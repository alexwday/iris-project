"""
Stage 5: Database - Sync Database with Processed Documents.

This stage performs database operations using the 2-table design:
- iris_document_metadata: Document-level metadata with summary
- iris_document_chunks: Chunk-level content with embeddings

Operations:
- Remove deleted/updated files from database
- Insert new/updated documents with chunks
- All operations in transactions for atomicity

Functions:
    run_stage: Execute the database sync stage
    remove_document: Remove a document and its chunks from database
    insert_document: Insert a document with all chunks
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..connections.postgres import execute_query, execute_one, get_cursor
from ..stages.stage_4_validate import ValidatedDocument
from ..utils.env_config import Config
from ..utils.process_monitoring import get_process_monitor

logger = logging.getLogger(__name__)


# Table names for the 2-table design
METADATA_TABLE = "iris_document_metadata"
CHUNKS_TABLE = "iris_document_chunks"


@dataclass
class DatabaseResult:
    """Result of the database sync stage."""

    documents_removed: int = 0
    documents_inserted: int = 0
    sections_inserted: int = 0
    chunks_inserted: int = 0
    errors: List[str] = field(default_factory=list)


def run_stage(
    files_to_remove: List[Dict],
    validated_documents: List[ValidatedDocument],
    dry_run: bool = False,
) -> DatabaseResult:
    """
    Execute the database sync stage.

    Removes deleted files and inserts new/updated documents.

    Args:
        files_to_remove: List of dicts with 'db_source', 'file_path' to remove.
        validated_documents: List of ValidatedDocument from Stage 4.
        dry_run: If True, don't actually modify database.

    Returns:
        DatabaseResult with operation counts and any errors.
    """
    monitor = get_process_monitor()
    monitor.start_stage("stage_5_database")

    result = DatabaseResult()

    if dry_run:
        logger.info("DRY RUN: Database operations will be simulated")

    # Step 1: Remove deleted/updated files
    if files_to_remove:
        logger.info("Removing %d documents from database", len(files_to_remove))
        for file_info in files_to_remove:
            # Use file_name as document_name for the 2-table design
            doc_name = file_info.get("file_name") or file_info.get("file_path", "").split("/")[-1]
            try:
                if not dry_run:
                    removed = remove_document(
                        file_info["db_source"], doc_name
                    )
                    if removed:
                        result.documents_removed += 1
                else:
                    logger.info(
                        "DRY RUN: Would remove %s/%s",
                        file_info["db_source"],
                        doc_name,
                    )
                    result.documents_removed += 1
            except Exception as exc:
                error_msg = f"Failed to remove {doc_name}: {exc}"
                logger.error(error_msg)
                result.errors.append(error_msg)

    # Step 2: Insert validated documents
    if validated_documents:
        logger.info("Inserting %d validated documents", len(validated_documents))
        for validated in validated_documents:
            doc = validated.document
            try:
                # Remove existing document first (for updates)
                if not dry_run:
                    remove_document(
                        doc.file_info.db_source, doc.file_info.file_name
                    )

                # Insert new document
                if not dry_run:
                    sections, chunks = insert_document(doc)
                    result.documents_inserted += 1
                    result.sections_inserted += sections
                    result.chunks_inserted += chunks
                else:
                    logger.info(
                        "DRY RUN: Would insert %s (%d sections, %d chunks)",
                        doc.file_info.file_name,
                        len(doc.sections),
                        len(doc.chunks),
                    )
                    result.documents_inserted += 1
                    result.sections_inserted += len(doc.sections)
                    result.chunks_inserted += len(doc.chunks)

            except Exception as exc:
                error_msg = f"Failed to insert {doc.file_info.file_name}: {exc}"
                logger.error(error_msg)
                result.errors.append(error_msg)

    # Log summary
    logger.info(
        "Database sync complete: %d removed, %d inserted (%d sections, %d chunks), %d errors",
        result.documents_removed,
        result.documents_inserted,
        result.sections_inserted,
        result.chunks_inserted,
        len(result.errors),
    )

    monitor.add_stage_details(
        "stage_5_database",
        documents_removed=result.documents_removed,
        documents_inserted=result.documents_inserted,
        sections_inserted=result.sections_inserted,
        chunks_inserted=result.chunks_inserted,
        errors=len(result.errors),
        dry_run=dry_run,
    )

    monitor.end_stage("stage_5_database", "completed")
    return result


def remove_document(db_source: str, document_name: str) -> bool:
    """
    Remove a document and all related chunks from database.

    Uses CASCADE to automatically remove chunks when document is deleted.

    Args:
        db_source: Database source identifier.
        document_name: Document name (file name).

    Returns:
        True if document was removed, False if not found.
    """
    # Find document ID
    result = execute_one(
        f"""
        SELECT id FROM {METADATA_TABLE}
        WHERE db_source = %s AND document_name = %s
        """,
        (db_source, document_name),
    )

    if not result:
        logger.debug("Document not found in DB: %s/%s", db_source, document_name)
        return False

    document_id = result[0]

    # Delete document (chunks cascade via FK)
    with get_cursor() as cursor:
        # Delete chunks first (explicit for logging)
        cursor.execute(
            f"DELETE FROM {CHUNKS_TABLE} WHERE document_id = %s",
            (document_id,),
        )
        chunks_deleted = cursor.rowcount

        # Delete document
        cursor.execute(
            f"DELETE FROM {METADATA_TABLE} WHERE id = %s",
            (document_id,),
        )

    logger.info(
        "Removed document %s: %d chunks",
        document_name,
        chunks_deleted,
    )

    return True


def insert_document(doc: Any) -> Tuple[int, int]:
    """
    Insert a document with all chunks into the 2-table design.

    Inserts into:
    - iris_document_metadata: Document-level info with summary and embedding
    - iris_document_chunks: Chunk-level content with embeddings

    Args:
        doc: ProcessedDocument to insert.

    Returns:
        Tuple of (sections_count, chunks_inserted).
    """
    with get_cursor() as cursor:
        # Format summary embedding as PostgreSQL array for HALFVEC
        summary_embedding_str = None
        if doc.summary_embedding:
            summary_embedding_str = "[" + ",".join(str(x) for x in doc.summary_embedding) + "]"

        # Insert document metadata with all new fields
        cursor.execute(
            f"""
            INSERT INTO {METADATA_TABLE} (
                db_source, document_name, document_type,
                document_summary, summary_embedding,
                page_count, primary_section_count, subsection_count,
                file_name, file_path, file_size, file_type,
                document_description
            ) VALUES (%s, %s, %s, %s, %s::halfvec, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                doc.file_info.db_source,
                doc.file_info.file_name,  # document_name
                doc.structure_type.value,  # document_type
                doc.document_summary,
                summary_embedding_str,
                doc.page_count,
                doc.primary_section_count,
                doc.subsection_count,
                doc.file_info.file_name,
                doc.file_info.relative_path,
                doc.file_info.file_size,
                doc.file_info.file_name.rsplit(".", 1)[-1] if "." in doc.file_info.file_name else None,
                doc.document_description,
            ),
        )
        document_id = cursor.fetchone()[0]

        # Insert chunks with all new fields
        chunks_inserted = 0
        for chunk in doc.chunks:
            # Format embedding as PostgreSQL array for HALFVEC
            embedding_str = None
            if chunk.embedding:
                embedding_str = "[" + ",".join(str(x) for x in chunk.embedding) + "]"

            cursor.execute(
                f"""
                INSERT INTO {CHUNKS_TABLE} (
                    document_id, db_source, chunk_number,
                    primary_section_number, primary_section_name,
                    subsection_number, subsection_name,
                    hierarchy_path,
                    chunk_content, chunk_embedding,
                    page_number,
                    primary_section_page_count, subsection_page_count,
                    file_name, source_filename
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::halfvec, %s, %s, %s, %s, %s)
                """,
                (
                    document_id,
                    doc.file_info.db_source,
                    chunk.chunk_number,
                    chunk.primary_section_number,
                    chunk.primary_section_name,
                    chunk.subsection_number,
                    chunk.subsection_name,
                    chunk.hierarchy_path,
                    chunk.raw_content,
                    embedding_str,
                    chunk.page_number,
                    chunk.primary_section_page_count,
                    chunk.subsection_page_count,
                    doc.file_info.file_name,
                    doc.file_info.file_name,
                ),
            )
            chunks_inserted += 1

    logger.info(
        "Inserted document %s: ID=%s, %d sections, %d subsections, %d chunks",
        doc.file_info.file_name,
        document_id,
        doc.primary_section_count,
        doc.subsection_count,
        chunks_inserted,
    )

    return doc.primary_section_count, chunks_inserted
