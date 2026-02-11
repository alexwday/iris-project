"""
Backup and restore utilities for the document refresh pipeline.

Exports PostgreSQL tables to CSV files for disaster recovery, and restores
them from CSV backups. The backup CSVs contain full table dumps (SELECT *)
including UUIDs and vector embeddings, allowing exact state restoration.

Used by Stage 5 (database sync) when BACKUP_ENABLED=true, and by the
restore CLI for disaster recovery from NAS or local backup directories.
"""

import csv
import io
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

from ..connections.file_source import FileSource
from ..connections.postgres import get_database_session

logger = logging.getLogger(__name__)

METADATA_TABLE = "iris_document_metadata"
CHUNKS_TABLE = "iris_document_chunks"


def _export_table(
    query: str, file_path: str, file_source: Optional[FileSource] = None
) -> str:
    """
    Export a table query result to CSV.

    Args:
        query: SQL query to execute.
        file_path: Destination CSV path.
        file_source: Optional FileSource for writing to NAS.

    Returns:
        Path to the created CSV file.
    """
    with get_database_session() as session:
        result = session.execute(text(query))
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result.fetchall()]

    if file_source is not None:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        file_source.write_data(buf.getvalue().encode("utf-8"), file_path)
    else:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    logger.info("Exported %d rows to %s", len(rows), file_path)
    return file_path


def export_metadata_csv(
    backup_dir: str, file_source: Optional[FileSource] = None
) -> str:
    """Export iris_document_metadata table to CSV."""
    file_path = os.path.join(backup_dir, "iris_document_metadata.csv")
    return _export_table(
        """
        SELECT *
        FROM iris_document_metadata
        ORDER BY id
        """,
        file_path,
        file_source=file_source,
    )


def export_chunks_csv(
    backup_dir: str, file_source: Optional[FileSource] = None
) -> str:
    """Export iris_document_chunks table to CSV."""
    file_path = os.path.join(backup_dir, "iris_document_chunks.csv")
    return _export_table(
        """
        SELECT *
        FROM iris_document_chunks
        ORDER BY document_id, id
        """,
        file_path,
        file_source=file_source,
    )


def run_backup(
    backup_path: str, file_source: Optional[FileSource] = None
) -> Tuple[bool, List[str]]:
    """
    Run full database backup to CSV files.

    Args:
        backup_path: Base directory to write backups.
        file_source: Optional FileSource for writing to NAS.

    Returns:
        Tuple of (success flag, list of created files).
    """
    if not backup_path:
        logger.warning("Backup path not configured; skipping backup")
        return False, []

    timestamp = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
    backup_dir = os.path.join(backup_path, timestamp)

    try:
        if file_source is not None:
            file_source.ensure_directory(backup_dir)
        else:
            os.makedirs(backup_dir, exist_ok=True)
    except Exception as exc:
        logger.error("Could not create backup directory %s: %s", backup_dir, exc)
        return False, []

    created_files: List[str] = []

    try:
        created_files.append(
            export_metadata_csv(backup_dir, file_source=file_source)
        )
        created_files.append(
            export_chunks_csv(backup_dir, file_source=file_source)
        )
        logger.info("Backup completed: %s", created_files)
        return True, created_files
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return False, created_files


def _read_csv(file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read a CSV file and return headers and rows as dicts."""

    with open(file_path, "r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        columns = reader.fieldnames or []
        rows = list(reader)

    logger.info("Read %d rows from %s", len(rows), file_path)
    return columns, rows


def _normalize_value(value: str, column: str) -> Optional[str]:
    """Convert CSV string values to appropriate SQL-ready values.

    Args:
        value: Raw string value from CSV.
        column: Column name for type-aware handling.

    Returns:
        Normalized value or None for empty strings.
    """
    if value == "" or value is None:
        return None
    return value


def _restore_metadata(
    rows: List[Dict[str, str]], db_sources: Optional[List[str]] = None
) -> int:
    """Restore iris_document_metadata rows from CSV data.

    Args:
        rows: Parsed CSV rows with all metadata columns.
        db_sources: Optional filter to only restore specific db_sources.

    Returns:
        Number of rows inserted.
    """
    if db_sources:
        rows = [r for r in rows if r.get("db_source") in db_sources]

    if not rows:
        logger.warning("No metadata rows to restore")
        return 0

    inserted = 0
    with get_database_session() as session:
        for row in rows:
            embedding = _normalize_value(row.get("summary_embedding", ""), "summary_embedding")

            session.execute(
                text(f"""
                    INSERT INTO {METADATA_TABLE} (
                        id, db_source, document_name, document_type,
                        document_summary, summary_embedding,
                        page_count, primary_section_count, subsection_count,
                        file_name, file_path, file_size, file_type,
                        document_description, document_usage,
                        created_at, updated_at, file_hash
                    ) VALUES (
                        CAST(:id AS uuid), :db_source, :document_name, :document_type,
                        :document_summary, CAST(:summary_embedding AS halfvec),
                        :page_count, :primary_section_count, :subsection_count,
                        :file_name, :file_path, :file_size, :file_type,
                        :document_description, :document_usage,
                        :created_at, :updated_at, :file_hash
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": row["id"],
                    "db_source": row["db_source"],
                    "document_name": row["document_name"],
                    "document_type": _normalize_value(row.get("document_type", ""), "document_type"),
                    "document_summary": row["document_summary"],
                    "summary_embedding": embedding,
                    "page_count": _normalize_value(row.get("page_count", ""), "page_count"),
                    "primary_section_count": _normalize_value(row.get("primary_section_count", ""), "primary_section_count"),
                    "subsection_count": _normalize_value(row.get("subsection_count", ""), "subsection_count"),
                    "file_name": _normalize_value(row.get("file_name", ""), "file_name"),
                    "file_path": _normalize_value(row.get("file_path", ""), "file_path"),
                    "file_size": _normalize_value(row.get("file_size", ""), "file_size"),
                    "file_type": _normalize_value(row.get("file_type", ""), "file_type"),
                    "document_description": _normalize_value(row.get("document_description", ""), "document_description"),
                    "document_usage": _normalize_value(row.get("document_usage", ""), "document_usage"),
                    "created_at": row.get("created_at") or datetime.now().isoformat(),
                    "updated_at": row.get("updated_at") or datetime.now().isoformat(),
                    "file_hash": _normalize_value(row.get("file_hash", ""), "file_hash"),
                },
            )
            inserted += 1

    logger.info("Restored %d metadata rows", inserted)
    return inserted


def _restore_chunks(
    rows: List[Dict[str, str]], db_sources: Optional[List[str]] = None
) -> int:
    """Restore iris_document_chunks rows from CSV data.

    Args:
        rows: Parsed CSV rows with all chunk columns.
        db_sources: Optional filter to only restore specific db_sources.

    Returns:
        Number of rows inserted.
    """
    if db_sources:
        rows = [r for r in rows if r.get("db_source") in db_sources]

    if not rows:
        logger.warning("No chunk rows to restore")
        return 0

    inserted = 0
    with get_database_session() as session:
        for row in rows:
            embedding = _normalize_value(row.get("chunk_embedding", ""), "chunk_embedding")

            session.execute(
                text(f"""
                    INSERT INTO {CHUNKS_TABLE} (
                        id, document_id, db_source, chunk_number,
                        primary_section_number, primary_section_name,
                        subsection_number, subsection_name,
                        hierarchy_path,
                        chunk_content, chunk_embedding,
                        page_number,
                        file_name, source_filename,
                        created_at,
                        primary_section_page_count, subsection_page_count
                    ) VALUES (
                        CAST(:id AS uuid), CAST(:document_id AS uuid),
                        :db_source, :chunk_number,
                        :primary_section_number, :primary_section_name,
                        :subsection_number, :subsection_name,
                        :hierarchy_path,
                        :chunk_content, CAST(:chunk_embedding AS halfvec),
                        :page_number,
                        :file_name, :source_filename,
                        :created_at,
                        :primary_section_page_count, :subsection_page_count
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "db_source": row["db_source"],
                    "chunk_number": row["chunk_number"],
                    "primary_section_number": _normalize_value(row.get("primary_section_number", ""), "primary_section_number"),
                    "primary_section_name": _normalize_value(row.get("primary_section_name", ""), "primary_section_name"),
                    "subsection_number": _normalize_value(row.get("subsection_number", ""), "subsection_number"),
                    "subsection_name": _normalize_value(row.get("subsection_name", ""), "subsection_name"),
                    "hierarchy_path": _normalize_value(row.get("hierarchy_path", ""), "hierarchy_path"),
                    "chunk_content": row["chunk_content"],
                    "chunk_embedding": embedding,
                    "page_number": _normalize_value(row.get("page_number", ""), "page_number"),
                    "file_name": _normalize_value(row.get("file_name", ""), "file_name"),
                    "source_filename": _normalize_value(row.get("source_filename", ""), "source_filename"),
                    "created_at": row.get("created_at") or datetime.now().isoformat(),
                    "primary_section_page_count": _normalize_value(row.get("primary_section_page_count", ""), "primary_section_page_count"),
                    "subsection_page_count": _normalize_value(row.get("subsection_page_count", ""), "subsection_page_count"),
                },
            )
            inserted += 1

    logger.info("Restored %d chunk rows", inserted)
    return inserted


def run_restore(
    backup_dir: str,
    db_sources: Optional[List[str]] = None,
    file_source: Optional[FileSource] = None,
) -> Tuple[bool, int, int]:
    """Restore document data from a CSV backup directory.

    Reads iris_document_metadata.csv and iris_document_chunks.csv from the
    backup directory and inserts them into PostgreSQL. Metadata is inserted
    first to satisfy foreign key constraints. Uses ON CONFLICT DO NOTHING
    to skip rows that already exist.

    Args:
        backup_dir: Path to backup directory containing the CSV files.
        db_sources: Optional list of db_source values to filter restore.
            If None, restores all data from the backup.
        file_source: Optional FileSource for reading from NAS. If provided,
            files are copied to a temp directory before reading.

    Returns:
        Tuple of (success, metadata_count, chunks_count).
    """
    metadata_csv = os.path.join(backup_dir, "iris_document_metadata.csv")
    chunks_csv = os.path.join(backup_dir, "iris_document_chunks.csv")

    if file_source is not None:
        import tempfile
        local_tmp = tempfile.mkdtemp(prefix="iris_restore_")
        logger.info("Copying backup CSVs from NAS to %s", local_tmp)
        metadata_csv = file_source.copy_to_local(metadata_csv, local_tmp)
        chunks_csv = file_source.copy_to_local(chunks_csv, local_tmp)

    if not os.path.exists(metadata_csv):
        logger.error("Metadata CSV not found: %s", metadata_csv)
        return False, 0, 0

    if not os.path.exists(chunks_csv):
        logger.error("Chunks CSV not found: %s", chunks_csv)
        return False, 0, 0

    try:
        _, metadata_rows = _read_csv(metadata_csv)
        _, chunks_rows = _read_csv(chunks_csv)

        source_filter = db_sources or list({r["db_source"] for r in metadata_rows})
        logger.info("Restoring db_sources: %s", source_filter)

        metadata_count = _restore_metadata(metadata_rows, db_sources)
        chunks_count = _restore_chunks(chunks_rows, db_sources)

        logger.info(
            "Restore complete: %d metadata rows, %d chunks",
            metadata_count,
            chunks_count,
        )
        return True, metadata_count, chunks_count

    except Exception as exc:
        logger.error("Restore failed: %s", exc, exc_info=True)
        return False, 0, 0
