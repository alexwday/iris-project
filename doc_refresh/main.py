"""
Document Refresh Pipeline - Main Entry Point.

A standalone tool for processing documents and syncing with PostgreSQL.
Scans input folders, extracts content from PDF/DOCX files, processes
into hierarchical structure, and syncs with database.

Usage:
    python -m doc_refresh.main [options]

Options:
    --dry-run       Don't modify database, just report what would happen
    --force         Process all files, ignore unchanged
    --log-level     Logging level (DEBUG, INFO, WARNING, ERROR)
    --help          Show this help message

Environment Variables:
    BASE_PATH           Root folder containing database subfolders
    DATABASE_NAMES      Comma-separated list of folder names to process
    FILE_SOURCE_MODE    "local" or "nas"
    OPENAI_API_KEY      OpenAI API key (local development)
    VECTOR_POSTGRES_*   Database connection parameters

See documentation for full configuration options.
"""

import argparse
import logging
import sys
import tempfile

from .connections.file_source import get_file_source
from .stages import (
    stage_1_scan,
    stage_6_report,
)
from .stages.stage_2_extract import ExtractionResult, ExtractedDocument, extract_file
from .stages.stage_3_process import (
    ProcessedDocument,
    ProcessingResult,
    StructureType,
    process_document,
    resolve_auth_token,
)
from .stages.stage_4_validate import (
    ValidatedDocument,
    ValidationResult,
    validate_document,
)
from .stages.stage_5_database import (
    DatabaseResult,
    remove_document,
    replace_single_document,
)
from .utils import backup
from .utils.audit_trail import create_audit_trail, generate_index_html
from .utils.env_config import config
from .utils.logging_format import configure_root_logger
from .utils.prompt_loader import load_all_prompts
from .utils.rbc_security import configure_rbc_security_certs

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Document Refresh Pipeline - Process documents and sync with PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process all configured databases
    python -m doc_refresh.main

    # Dry run (no database changes)
    python -m doc_refresh.main --dry-run

    # Force reprocess all files
    python -m doc_refresh.main --force

    # Debug logging
    python -m doc_refresh.main --log-level DEBUG

Environment:
    Set BASE_PATH and DATABASE_NAMES to configure input folders.
    Set OPENAI_API_KEY for local development.
    Set FILE_SOURCE_MODE=nas for NAS file access.
""",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=config.REFRESH_DRY_RUN,
        help="Don't modify database, just report what would happen",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        default=config.REFRESH_FORCE,
        help="Process all files, ignore unchanged",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=config.REFRESH_LOG_PATH,
        help="Path for JSON report output",
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the document refresh pipeline.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    # Parse arguments
    args = parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    configure_root_logger(log_level)

    logger.info("=" * 60)
    logger.info("Document Refresh Pipeline Starting")
    logger.info("=" * 60)

    # Setup SSL certificates if needed
    configure_rbc_security_certs()

    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed. Check environment variables.")
        return 1

    prompt_count = load_all_prompts(model="doc_refresh")
    if prompt_count == 0:
        logger.error(
            "No prompts loaded for model 'doc_refresh'. "
            "Check database connectivity and prompts table."
        )
        return 1
    logger.info("Loaded %d prompts for doc_refresh", prompt_count)

    logger.info("Configuration:")
    logger.info("  File Source Mode: %s", config.FILE_SOURCE_MODE)
    logger.info("  Base Path: %s", config.BASE_PATH)
    logger.info("  Database Names: %s", config.get_database_names())
    logger.info("  Dry Run: %s", args.dry_run)
    logger.info("  Force: %s", args.force)

    scan_result = None
    extraction_result = ExtractionResult()
    processing_result = ProcessingResult()
    validation_result = ValidationResult()
    database_result = DatabaseResult()

    try:
        file_source = get_file_source()

        # Stage 1: Scan (batch — need full file list for new/changed/deleted detection)
        logger.info("-" * 60)
        logger.info("Stage 1: Scanning folders")
        logger.info("-" * 60)
        scan_result = stage_1_scan.run_stage(
            file_source=file_source,
            force=args.force,
        )

        audit_documents = []
        if not scan_result.files_to_process and not scan_result.files_to_remove:
            logger.info("No files to process or remove. Pipeline complete.")
        else:
            # Handle deletions (batch, before per-file loop — no LLM cost)
            if scan_result.files_to_remove:
                logger.info(
                    "Removing %d deleted/changed files from database",
                    len(scan_result.files_to_remove),
                )
                if not args.dry_run:
                    for file_info in scan_result.files_to_remove:
                        doc_path = file_info.get("file_path", "")
                        try:
                            removed = remove_document(
                                file_info["db_source"], doc_path
                            )
                            if removed:
                                database_result.documents_removed += 1
                        except Exception as exc:
                            error_msg = f"Failed to remove {doc_path}: {exc}"
                            logger.error(error_msg)
                            database_result.errors.append(error_msg)
                else:
                    for file_info in scan_result.files_to_remove:
                        logger.info(
                            "DRY RUN: Would remove %s/%s",
                            file_info["db_source"],
                            file_info.get("file_path", ""),
                        )
                        database_result.documents_removed += 1

            # Backup before any inserts
            if scan_result.files_to_process:
                if config.BACKUP_ENABLED and not args.dry_run:
                    backup_success, backup_files = backup.run_backup(
                        config.BACKUP_PATH, file_source=file_source
                    )
                    if backup_success:
                        logger.info("Backup completed: %s", backup_files)
                    else:
                        logger.error(
                            "Backup failed; aborting pipeline to prevent data loss. "
                            "Disable BACKUP_ENABLED to skip backups."
                        )
                        return 1
                elif config.BACKUP_ENABLED and args.dry_run:
                    logger.info("DRY RUN: Skipping backup")

            # Per-file pipeline: extract → process → validate → insert
            files_to_process = scan_result.files_to_process
            if files_to_process:
                total = len(files_to_process)
                logger.info("-" * 60)
                logger.info("Processing %d files (per-file pipeline)", total)
                logger.info("-" * 60)

                with tempfile.TemporaryDirectory() as temp_dir:
                    for i, file_info in enumerate(files_to_process, 1):
                        logger.info(
                            "File %d/%d: %s", i, total, file_info.file_name
                        )

                        try:
                            extracted = extract_file(
                                file_info, file_source, temp_dir
                            )
                        except Exception as exc:
                            logger.error(
                                "Error extracting %s: %s",
                                file_info.file_name,
                                exc,
                            )
                            extraction_result.failed_documents.append(
                                ExtractedDocument(
                                    file_info=file_info,
                                    extraction_error=str(exc),
                                )
                            )
                            continue

                        if not extracted.is_valid:
                            extraction_result.failed_documents.append(extracted)
                            logger.warning(
                                "Extraction failed for %s: %s",
                                file_info.file_name,
                                extracted.extraction_error,
                            )
                            continue

                        extraction_result.extracted_documents.append(extracted)
                        extraction_result.total_pages += extracted.page_count

                        audit_trail = create_audit_trail(
                            config.AUDIT_PATH,
                            file_info.db_source,
                            file_info.relative_path,
                        )

                        try:
                            auth_token = resolve_auth_token()
                            processed = process_document(
                                extracted, auth_token, audit_trail=audit_trail
                            )
                        except Exception as exc:
                            logger.error(
                                "Error processing %s: %s",
                                file_info.file_name,
                                exc,
                            )
                            processing_result.failed_documents.append(
                                ProcessedDocument(
                                    file_info=file_info,
                                    structure_type=StructureType.SEMANTIC,
                                    structure_confidence="low",
                                    page_count=extracted.page_count,
                                    processing_error=str(exc),
                                )
                            )
                            continue

                        if not processed.is_valid:
                            processing_result.failed_documents.append(processed)
                            logger.warning(
                                "Processing failed for %s: %s",
                                file_info.file_name,
                                processed.processing_error,
                            )
                            continue

                        processing_result.processed_documents.append(processed)
                        processing_result.total_sections += len(processed.sections)
                        processing_result.total_subsections += processed.subsection_count
                        processing_result.total_chunks += len(processed.chunks)

                        errors = validate_document(processed)
                        hard_errors = [
                            e for e in errors if e.severity == "error"
                        ]
                        warnings = [
                            e for e in errors if e.severity == "warning"
                        ]
                        validation_result.all_errors.extend(errors)
                        validation_result.total_warnings += len(warnings)

                        if hard_errors:
                            validation_result.failed_documents.append(processed)
                            for error in hard_errors:
                                logger.error(
                                    "Validation error for %s: [%s] %s",
                                    error.document_name,
                                    error.error_type,
                                    error.message,
                                )
                            continue

                        validated = ValidatedDocument(
                            document=processed, warnings=warnings
                        )
                        validation_result.validated_documents.append(validated)
                        if warnings:
                            for warning in warnings:
                                logger.warning(
                                    "Validation warning for %s: [%s] %s",
                                    warning.document_name,
                                    warning.error_type,
                                    warning.message,
                                )

                        if not args.dry_run:
                            try:
                                sections, chunks = replace_single_document(
                                    processed
                                )
                                database_result.documents_inserted += 1
                                database_result.sections_inserted += sections
                                database_result.chunks_inserted += chunks
                            except Exception as exc:
                                error_msg = (
                                    f"Failed to insert {file_info.file_name}: {exc}"
                                )
                                logger.error(error_msg)
                                database_result.errors.append(error_msg)
                                continue
                        else:
                            logger.info(
                                "DRY RUN: Would insert %s (%d sections, %d chunks)",
                                file_info.file_name,
                                len(processed.sections),
                                len(processed.chunks),
                            )
                            database_result.documents_inserted += 1
                            database_result.sections_inserted += len(
                                processed.sections
                            )
                            database_result.chunks_inserted += len(processed.chunks)

                        audit_trail.finalize()
                        audit_summary = audit_trail.get_summary()
                        if audit_summary:
                            audit_documents.append(audit_summary)

                        logger.info(
                            "Completed file %d/%d: %s",
                            i,
                            total,
                            file_info.file_name,
                        )

        if audit_documents:
            generate_index_html(config.AUDIT_PATH, audit_documents)

        # Stage 6: Report
        logger.info("-" * 60)
        logger.info("Stage 6: Generating report")
        logger.info("-" * 60)

        report_result = stage_6_report.run_stage(
            scan_result=scan_result,
            extraction_result=extraction_result,
            processing_result=processing_result,
            validation_result=validation_result,
            database_result=database_result,
            output_path=args.output,
            file_source=file_source,
        )

        has_errors = False
        if scan_result and scan_result.scan_errors:
            has_errors = True
        if extraction_result and extraction_result.failed_documents:
            has_errors = True
        if processing_result and processing_result.failed_documents:
            has_errors = True
        if validation_result and validation_result.failed_documents:
            has_errors = True
        if database_result and database_result.errors:
            has_errors = True

        if has_errors:
            logger.warning("Pipeline completed with errors")
            return 1

        logger.info("Pipeline completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        return 130

    except Exception as exc:
        logger.exception("Pipeline failed with unexpected error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
