"""
Backup utilities for the document refresh pipeline.

Exports PostgreSQL tables to CSV files for disaster recovery.
"""

import csv
import logging
import os
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import text

from ..connections.postgres import get_database_session

logger = logging.getLogger(__name__)


def _export_table(query: str, file_path: str) -> str:
    """
    Export a table query result to CSV.

    Args:
        query: SQL query to execute.
        file_path: Destination CSV path.

    Returns:
        Path to the created CSV file.
    """
    with get_database_session() as session:
        result = session.execute(text(query))
        columns = list(result.keys())
        rows = [dict(row._mapping) for row in result.fetchall()]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Exported %d rows to %s", len(rows), file_path)
    return file_path


def export_metadata_csv(backup_dir: str) -> str:
    """Export iris_document_metadata table to CSV."""
    file_path = os.path.join(backup_dir, "iris_document_metadata.csv")
    return _export_table(
        """
        SELECT *
        FROM iris_document_metadata
        ORDER BY id
        """,
        file_path,
    )


def export_chunks_csv(backup_dir: str) -> str:
    """Export iris_document_chunks table to CSV."""
    file_path = os.path.join(backup_dir, "iris_document_chunks.csv")
    return _export_table(
        """
        SELECT *
        FROM iris_document_chunks
        ORDER BY document_id, id
        """,
        file_path,
    )


def run_backup(backup_path: str) -> Tuple[bool, List[str]]:
    """
    Run full database backup to CSV files.

    Args:
        backup_path: Base directory to write backups.

    Returns:
        Tuple of (success flag, list of created files).
    """
    if not backup_path:
        logger.warning("Backup path not configured; skipping backup")
        return False, []

    timestamp = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
    backup_dir = os.path.join(backup_path, timestamp)

    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception as exc:
        logger.error("Could not create backup directory %s: %s", backup_dir, exc)
        return False, []

    created_files: List[str] = []

    try:
        created_files.append(export_metadata_csv(backup_dir))
        created_files.append(export_chunks_csv(backup_dir))
        logger.info("Backup completed: %s", created_files)
        return True, created_files
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return False, created_files
