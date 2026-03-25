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
    --backup-even-if-no-changes
                    Force a fresh backup snapshot even when no files changed
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
import collections
import logging
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .connections.file_source import FileSource, get_file_source
from .stages import (
    stage_1_scan,
    stage_6_report,
)
from .stages.stage_1_scan import FileInfo
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
    ValidationError,
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


@dataclass
class DocumentPipelineResult:
    """Outcome of running extract-process-validate-insert for one document."""

    file_info: Optional[FileInfo] = None
    extracted: Optional[ExtractedDocument] = None
    extraction_failed: bool = False
    processed: Optional[ProcessedDocument] = None
    processing_failed: bool = False
    validated: Optional[ValidatedDocument] = None
    validation_failed: bool = False
    validation_errors: List = field(default_factory=list)
    validation_warnings: List = field(default_factory=list)
    db_sections_inserted: int = 0
    db_chunks_inserted: int = 0
    db_inserted: bool = False
    db_error: Optional[str] = None
    audit_summary: Optional[dict] = None
    stage_reached: str = "none"


def _process_single_file(
    file_info: FileInfo,
    file_source: FileSource,
    auth_token: str,
    dry_run: bool,
) -> DocumentPipelineResult:
    """Run extract-process-validate-insert for a single document.

    Each invocation creates its own temp directory, which is cleaned up
    when the document finishes — preventing file-descriptor accumulation.
    """
    result = DocumentPipelineResult(file_info=file_info)

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            extracted = extract_file(file_info, file_source, temp_dir)
        except Exception as exc:
            logger.error("Error extracting %s: %s", file_info.file_name, exc)
            result.extracted = ExtractedDocument(
                file_info=file_info, extraction_error=str(exc)
            )
            result.extraction_failed = True
            result.stage_reached = "extraction"
            return result

        if not extracted.is_valid:
            logger.warning(
                "Extraction failed for %s: %s",
                file_info.file_name,
                extracted.extraction_error,
            )
            result.extracted = extracted
            result.extraction_failed = True
            result.stage_reached = "extraction"
            return result

        result.extracted = extracted
        result.stage_reached = "extraction"

        audit_trail = create_audit_trail(
            config.AUDIT_PATH, file_info.db_source, file_info.relative_path
        )

        try:
            processed = process_document(
                extracted, auth_token, audit_trail=audit_trail
            )
        except Exception as exc:
            logger.error("Error processing %s: %s", file_info.file_name, exc)
            result.processed = ProcessedDocument(
                file_info=file_info,
                structure_type=StructureType.SEMANTIC,
                structure_confidence="low",
                page_count=extracted.page_count,
                processing_error=str(exc),
            )
            result.processing_failed = True
            result.stage_reached = "processing"
            return result

        if not processed.is_valid:
            logger.warning(
                "Processing failed for %s: %s",
                file_info.file_name,
                processed.processing_error,
            )
            result.processed = processed
            result.processing_failed = True
            result.stage_reached = "processing"
            return result

        result.processed = processed
        result.stage_reached = "processing"

        errors = validate_document(processed)
        hard_errors = [e for e in errors if e.severity == "error"]
        warnings = [e for e in errors if e.severity == "warning"]
        result.validation_errors = errors
        result.validation_warnings = warnings

        if hard_errors:
            for error in hard_errors:
                logger.error(
                    "Validation error for %s: [%s] %s",
                    error.document_name,
                    error.error_type,
                    error.message,
                )
            result.validation_failed = True
            result.stage_reached = "validation"
            return result

        result.validated = ValidatedDocument(document=processed, warnings=warnings)
        result.stage_reached = "validation"

        if warnings:
            for warning in warnings:
                logger.warning(
                    "Validation warning for %s: [%s] %s",
                    warning.document_name,
                    warning.error_type,
                    warning.message,
                )

        if not dry_run:
            try:
                sections, chunks = replace_single_document(processed)
                result.db_inserted = True
                result.db_sections_inserted = sections
                result.db_chunks_inserted = chunks
            except Exception as exc:
                error_msg = f"Failed to insert {file_info.file_name}: {exc}"
                logger.error(error_msg)
                result.db_error = error_msg
                result.stage_reached = "database"
                return result
        else:
            logger.info(
                "DRY RUN: Would insert %s (%d sections, %d chunks)",
                file_info.file_name,
                len(processed.sections),
                len(processed.chunks),
            )
            result.db_inserted = True
            result.db_sections_inserted = len(processed.sections)
            result.db_chunks_inserted = len(processed.chunks)

        result.stage_reached = "complete"

        audit_trail.finalize()
        audit_summary = audit_trail.get_summary()
        if audit_summary:
            result.audit_summary = audit_summary

    return result


def _aggregate_document_result(
    doc_result: DocumentPipelineResult,
    extraction_result: ExtractionResult,
    processing_result: ProcessingResult,
    validation_result: ValidationResult,
    database_result: DatabaseResult,
    audit_documents: list,
) -> None:
    """Merge a single document's pipeline outcome into stage-level accumulators."""
    if doc_result.extraction_failed:
        extraction_result.failed_documents.append(doc_result.extracted)
        return

    if doc_result.extracted and doc_result.extracted.is_valid:
        extraction_result.extracted_documents.append(doc_result.extracted)
        extraction_result.total_pages += doc_result.extracted.page_count

    if doc_result.processing_failed:
        processing_result.failed_documents.append(doc_result.processed)
        return

    if doc_result.processed and doc_result.processed.is_valid:
        processing_result.processed_documents.append(doc_result.processed)
        processing_result.total_sections += len(doc_result.processed.sections)
        processing_result.total_subsections += doc_result.processed.subsection_count
        processing_result.total_chunks += len(doc_result.processed.chunks)

    validation_result.all_errors.extend(doc_result.validation_errors)
    validation_result.total_warnings += len(doc_result.validation_warnings)

    if doc_result.validation_failed:
        validation_result.failed_documents.append(doc_result.processed)
        return

    if doc_result.validated:
        validation_result.validated_documents.append(doc_result.validated)

    if doc_result.db_error:
        database_result.errors.append(doc_result.db_error)
        return

    if doc_result.db_inserted:
        database_result.documents_inserted += 1
        database_result.sections_inserted += doc_result.db_sections_inserted
        database_result.chunks_inserted += doc_result.db_chunks_inserted

    if doc_result.audit_summary:
        audit_documents.append(doc_result.audit_summary)


REFERENCE_SHEET_KEYWORDS = frozenset({
    "summary", "index", "definitions", "toc", "overview",
    "glossary", "legend", "reference", "contents",
})


def _process_xlsx_extract_and_process(
    file_info: FileInfo,
    file_source: FileSource,
    auth_token: str,
) -> DocumentPipelineResult:
    """Run extract and process (stages 2-3) for one xlsx sheet document.

    Stops after Stage 3 so that cross-referencing can enrich the
    document_description before validation and database insert.
    """
    result = DocumentPipelineResult(file_info=file_info)

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            extracted = extract_file(file_info, file_source, temp_dir)
        except Exception as exc:
            logger.error("Error extracting %s: %s", file_info.file_name, exc)
            result.extracted = ExtractedDocument(
                file_info=file_info, extraction_error=str(exc)
            )
            result.extraction_failed = True
            result.stage_reached = "extraction"
            return result

        if not extracted.is_valid:
            logger.warning(
                "Extraction failed for %s: %s",
                file_info.file_name,
                extracted.extraction_error,
            )
            result.extracted = extracted
            result.extraction_failed = True
            result.stage_reached = "extraction"
            return result

        result.extracted = extracted
        result.stage_reached = "extraction"

        audit_trail = create_audit_trail(
            config.AUDIT_PATH, file_info.db_source, file_info.relative_path
        )

        try:
            processed = process_document(
                extracted, auth_token, audit_trail=audit_trail
            )
        except Exception as exc:
            logger.error("Error processing %s: %s", file_info.file_name, exc)
            result.processed = ProcessedDocument(
                file_info=file_info,
                structure_type=StructureType.SEMANTIC,
                structure_confidence="low",
                page_count=extracted.page_count,
                processing_error=str(exc),
            )
            result.processing_failed = True
            result.stage_reached = "processing"
            return result

        if not processed.is_valid:
            logger.warning(
                "Processing failed for %s: %s",
                file_info.file_name,
                processed.processing_error,
            )
            result.processed = processed
            result.processing_failed = True
            result.stage_reached = "processing"
            return result

        result.processed = processed
        result.stage_reached = "processing"

        audit_trail.finalize()
        audit_summary = audit_trail.get_summary()
        if audit_summary:
            result.audit_summary = audit_summary

    return result


def _enrich_workbook_descriptions(
    workbook_results: List[DocumentPipelineResult],
    workbook_name: str,
) -> None:
    """Append related-sheet cross-references to each sheet's document_description."""
    processed_sheets = [
        r for r in workbook_results
        if r.processed and r.processed.is_valid
    ]

    if len(processed_sheets) < 2:
        return

    logger.info(
        "Enriching %d sheet descriptions for workbook '%s'",
        len(processed_sheets),
        workbook_name,
    )

    for sheet_result in processed_sheets:
        doc = sheet_result.processed
        lines = [f'\nRelated Sheets in "{workbook_name}":']

        for other in processed_sheets:
            if other is sheet_result:
                continue
            other_name = other.file_info.sheet_name or "Unknown"
            other_desc = other.processed.document_description or other_name
            is_reference = any(
                kw in other_name.lower() for kw in REFERENCE_SHEET_KEYWORDS
            )
            if is_reference:
                lines.append(f"- **{other_name}** [reference sheet]: {other_desc}")
            else:
                lines.append(f"- **{other_name}**: {other_desc}")

        doc.document_description = (doc.document_description or "") + "\n".join(lines)


def _validate_and_insert_document(
    doc_result: DocumentPipelineResult,
    dry_run: bool,
) -> DocumentPipelineResult:
    """Run validate and insert (stages 4-5) on an already-processed document."""
    processed = doc_result.processed
    file_info = doc_result.file_info

    errors = validate_document(processed)
    hard_errors = [e for e in errors if e.severity == "error"]
    warnings = [e for e in errors if e.severity == "warning"]
    doc_result.validation_errors = errors
    doc_result.validation_warnings = warnings

    if hard_errors:
        for error in hard_errors:
            logger.error(
                "Validation error for %s: [%s] %s",
                error.document_name,
                error.error_type,
                error.message,
            )
        doc_result.validation_failed = True
        doc_result.stage_reached = "validation"
        return doc_result

    doc_result.validated = ValidatedDocument(document=processed, warnings=warnings)
    doc_result.stage_reached = "validation"

    if warnings:
        for warning in warnings:
            logger.warning(
                "Validation warning for %s: [%s] %s",
                warning.document_name,
                warning.error_type,
                warning.message,
            )

    if not dry_run:
        try:
            sections, chunks = replace_single_document(processed)
            doc_result.db_inserted = True
            doc_result.db_sections_inserted = sections
            doc_result.db_chunks_inserted = chunks
        except Exception as exc:
            error_msg = f"Failed to insert {file_info.file_name}: {exc}"
            logger.error(error_msg)
            doc_result.db_error = error_msg
            doc_result.stage_reached = "database"
            return doc_result
    else:
        logger.info(
            "DRY RUN: Would insert %s (%d sections, %d chunks)",
            file_info.file_name,
            len(processed.sections),
            len(processed.chunks),
        )
        doc_result.db_inserted = True
        doc_result.db_sections_inserted = len(processed.sections)
        doc_result.db_chunks_inserted = len(processed.chunks)

    doc_result.stage_reached = "complete"
    return doc_result


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
        "--backup-even-if-no-changes",
        action="store_true",
        default=False,
        help="Take a fresh backup even when scan finds no files to process or remove",
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
    logger.info("  Backup On No Changes: %s", args.backup_even_if_no_changes)

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

        files_to_process = scan_result.files_to_process
        files_to_remove = scan_result.files_to_remove
        has_mutations = bool(files_to_process or files_to_remove)
        backup_enabled_live = config.BACKUP_ENABLED and not args.dry_run
        backup_requested = backup_enabled_live and (
            has_mutations or args.backup_even_if_no_changes
        )
        backup_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        audit_documents = []
        if backup_requested:
            backup_phase = "before" if has_mutations else "snapshot"
            backup_success, backup_files = backup.run_backup(
                config.BACKUP_PATH,
                file_source=file_source,
                backup_stamp=backup_stamp,
                backup_phase=backup_phase,
            )
            if backup_success:
                logger.info(
                    "Pre-run backup (%s) completed: %s",
                    backup_phase,
                    backup_files,
                )
            else:
                logger.error(
                    "Pre-run backup failed; aborting pipeline to prevent data loss. "
                    "Disable BACKUP_ENABLED to skip backups."
                )
                return 1
        elif config.BACKUP_ENABLED and args.dry_run:
            logger.info("DRY RUN: Skipping backup")

        if not has_mutations:
            logger.info("No files to process or remove. Pipeline complete.")
        else:
            # Handle deletions (batch, before per-file loop — no LLM cost)
            if files_to_remove:
                logger.info(
                    "Removing %d deleted/changed files from database",
                    len(files_to_remove),
                )
                if not args.dry_run:
                    for file_info in files_to_remove:
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
                    for file_info in files_to_remove:
                        logger.info(
                            "DRY RUN: Would remove %s/%s",
                            file_info["db_source"],
                            file_info.get("file_path", ""),
                        )
                        database_result.documents_removed += 1

            # Per-file pipeline: extract → process → validate → insert
            if files_to_process:
                regular_files = [
                    fi for fi in files_to_process if fi.sheet_name is None
                ]
                xlsx_sheets = [
                    fi for fi in files_to_process if fi.sheet_name is not None
                ]

                total = len(files_to_process)
                max_workers = config.MAX_DOCUMENT_WORKERS
                logger.info("-" * 60)
                logger.info(
                    "Processing %d files (%d regular, %d xlsx sheets, %d workers)",
                    total,
                    len(regular_files),
                    len(xlsx_sheets),
                    max_workers,
                )
                logger.info("-" * 60)

                auth_token = resolve_auth_token()
                completed_count = 0

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            _process_single_file,
                            fi,
                            file_source,
                            auth_token,
                            args.dry_run,
                        ): fi
                        for fi in regular_files
                    }
                    for future in as_completed(futures):
                        fi = futures[future]
                        try:
                            doc_result = future.result()
                        except Exception as exc:
                            logger.error(
                                "Unexpected error processing %s: %s",
                                fi.file_name,
                                exc,
                            )
                            extraction_result.failed_documents.append(
                                ExtractedDocument(
                                    file_info=fi,
                                    extraction_error=str(exc),
                                )
                            )
                            completed_count += 1
                            continue

                        _aggregate_document_result(
                            doc_result,
                            extraction_result,
                            processing_result,
                            validation_result,
                            database_result,
                            audit_documents,
                        )
                        completed_count += 1
                        logger.info(
                            "Completed file %d/%d: %s",
                            completed_count,
                            total,
                            fi.file_name,
                        )

                if xlsx_sheets:
                    logger.info("-" * 60)
                    logger.info(
                        "Processing %d xlsx sheet documents (stages 2-3)",
                        len(xlsx_sheets),
                    )
                    logger.info("-" * 60)

                    xlsx_results: List[DocumentPipelineResult] = []
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(
                                _process_xlsx_extract_and_process,
                                fi,
                                file_source,
                                auth_token,
                            ): fi
                            for fi in xlsx_sheets
                        }
                        for future in as_completed(futures):
                            fi = futures[future]
                            try:
                                doc_result = future.result()
                            except Exception as exc:
                                logger.error(
                                    "Unexpected error processing xlsx sheet %s: %s",
                                    fi.file_name,
                                    exc,
                                )
                                extraction_result.failed_documents.append(
                                    ExtractedDocument(
                                        file_info=fi,
                                        extraction_error=str(exc),
                                    )
                                )
                                completed_count += 1
                                continue

                            xlsx_results.append(doc_result)
                            completed_count += 1
                            logger.info(
                                "Completed xlsx stages 2-3 %d/%d: %s",
                                completed_count,
                                total,
                                fi.file_name,
                            )

                    workbook_groups: Dict[str, List[DocumentPipelineResult]] = (
                        collections.defaultdict(list)
                    )
                    for r in xlsx_results:
                        workbook_groups[r.file_info.file_path].append(r)

                    for wb_path, wb_results in workbook_groups.items():
                        wb_name = Path(wb_path).stem
                        _enrich_workbook_descriptions(wb_results, wb_name)

                    logger.info(
                        "Running validation and insert for %d xlsx sheet documents",
                        len(xlsx_results),
                    )
                    for doc_result in xlsx_results:
                        if doc_result.extraction_failed or doc_result.processing_failed:
                            _aggregate_document_result(
                                doc_result,
                                extraction_result,
                                processing_result,
                                validation_result,
                                database_result,
                                audit_documents,
                            )
                            continue

                        doc_result = _validate_and_insert_document(
                            doc_result, args.dry_run
                        )
                        _aggregate_document_result(
                            doc_result,
                            extraction_result,
                            processing_result,
                            validation_result,
                            database_result,
                            audit_documents,
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

        if backup_enabled_live and has_mutations:
            backup_success, backup_files = backup.run_backup(
                config.BACKUP_PATH,
                file_source=file_source,
                backup_stamp=backup_stamp,
                backup_phase="after",
            )
            if backup_success:
                logger.info("Post-run backup (after) completed: %s", backup_files)
            else:
                logger.error(
                    "Post-run backup failed after database updates. "
                    "Capture a manual backup before the next run."
                )
                return 1

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
