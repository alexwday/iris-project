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
from typing import Optional

from .connections.file_source import get_file_source
from .connections.postgres import close_connections
from .stages import (
    stage_1_scan,
    stage_2_extract,
    stage_3_process,
    stage_4_validate,
    stage_5_database,
    stage_6_report,
)
from .utils.env_config import Config
from .utils.logging_format import configure_logging
from .utils.process_monitoring import enable_monitoring, get_process_monitor
from .utils.rbc_security import setup_ssl

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
        default=Config.REFRESH_DRY_RUN,
        help="Don't modify database, just report what would happen",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        default=Config.REFRESH_FORCE,
        help="Process all files, ignore unchanged",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=Config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=Config.REFRESH_LOG_PATH,
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
    configure_logging(log_level)

    logger.info("=" * 60)
    logger.info("Document Refresh Pipeline Starting")
    logger.info("=" * 60)

    # Setup SSL certificates if needed
    setup_ssl()

    # Enable process monitoring
    enable_monitoring(enabled=True)
    monitor = get_process_monitor()
    monitor.start_monitoring()

    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed. Check environment variables.")
        return 1

    logger.info("Configuration:")
    logger.info("  File Source Mode: %s", Config.FILE_SOURCE_MODE)
    logger.info("  Base Path: %s", Config.BASE_PATH)
    logger.info("  Database Names: %s", Config.get_database_names())
    logger.info("  Dry Run: %s", args.dry_run)
    logger.info("  Force: %s", args.force)

    # Initialize results
    scan_result = None
    extraction_result = None
    processing_result = None
    validation_result = None
    database_result = None

    try:
        # Get file source
        file_source = get_file_source()

        # Stage 1: Scan
        logger.info("-" * 60)
        logger.info("Stage 1: Scanning folders")
        logger.info("-" * 60)
        scan_result = stage_1_scan.run_stage(
            file_source=file_source,
            force=args.force,
        )

        if not scan_result.files_to_process and not scan_result.files_to_remove:
            logger.info("No files to process or remove. Pipeline complete.")
        else:
            # Stage 2: Extract
            if scan_result.files_to_process:
                logger.info("-" * 60)
                logger.info("Stage 2: Extracting content")
                logger.info("-" * 60)
                extraction_result = stage_2_extract.run_stage(
                    files_to_process=scan_result.files_to_process,
                    file_source=file_source,
                )

                # Stage 3: Process
                if extraction_result.extracted_documents:
                    logger.info("-" * 60)
                    logger.info("Stage 3: Processing documents")
                    logger.info("-" * 60)
                    processing_result = stage_3_process.run_stage(
                        extracted_documents=extraction_result.extracted_documents,
                    )

                    # Stage 4: Validate
                    if processing_result.processed_documents:
                        logger.info("-" * 60)
                        logger.info("Stage 4: Validating documents")
                        logger.info("-" * 60)
                        validation_result = stage_4_validate.run_stage(
                            processed_documents=processing_result.processed_documents,
                            strict=not args.dry_run,  # Less strict in dry-run
                        )

            # Stage 5: Database
            validated_docs = (
                validation_result.validated_documents if validation_result else []
            )
            if scan_result.files_to_remove or validated_docs:
                logger.info("-" * 60)
                logger.info("Stage 5: Syncing database")
                logger.info("-" * 60)
                database_result = stage_5_database.run_stage(
                    files_to_remove=scan_result.files_to_remove,
                    validated_documents=validated_docs,
                    dry_run=args.dry_run,
                )

        # Stage 6: Report
        logger.info("-" * 60)
        logger.info("Stage 6: Generating report")
        logger.info("-" * 60)
        monitor.end_monitoring()

        report_result = stage_6_report.run_stage(
            scan_result=scan_result,
            extraction_result=extraction_result,
            processing_result=processing_result,
            validation_result=validation_result,
            database_result=database_result,
            output_path=args.output,
        )

        # Determine exit code
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

    finally:
        # Cleanup
        try:
            close_connections()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
