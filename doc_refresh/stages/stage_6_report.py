"""
Stage 6: Report - Generate Summary Report and Log Output.

This stage generates a comprehensive report of the document refresh run:
- Console summary
- Optional log file output
- Optional JSON report file

Functions:
    run_stage: Execute the reporting stage
    generate_report: Generate the full report dict
    print_summary: Print formatted summary to console
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..connections.file_source import FileSource
from ..stages.stage_1_scan import ScanResult
from ..stages.stage_2_extract import ExtractionResult
from ..stages.stage_3_process import ProcessingResult
from ..stages.stage_4_validate import ValidationResult
from ..stages.stage_5_database import DatabaseResult
from ..utils.env_config import config

logger = logging.getLogger(__name__)


@dataclass
class ReportResult:
    """Result of the reporting stage."""

    report_dict: Dict[str, Any] = field(default_factory=dict)
    report_path: Optional[str] = None
    success: bool = True


def run_stage(
    scan_result: Optional[ScanResult] = None,
    extraction_result: Optional[ExtractionResult] = None,
    processing_result: Optional[ProcessingResult] = None,
    validation_result: Optional[ValidationResult] = None,
    database_result: Optional[DatabaseResult] = None,
    output_path: Optional[str] = None,
    file_source: Optional[FileSource] = None,
) -> ReportResult:
    """
    Execute the reporting stage.

    Generates a comprehensive report from all stage results.

    Args:
        scan_result: Result from Stage 1.
        extraction_result: Result from Stage 2.
        processing_result: Result from Stage 3.
        validation_result: Result from Stage 4.
        database_result: Result from Stage 5.
        output_path: Optional path to write JSON report.
        file_source: Optional FileSource for writing report to NAS.

    Returns:
        ReportResult with report dict and optional file path.
    """
    result = ReportResult()

    try:
        result.report_dict = generate_report(
            scan_result,
            extraction_result,
            processing_result,
            validation_result,
            database_result,
        )

        print_summary(result.report_dict)

        if output_path:
            result.report_path = write_json_report(
                result.report_dict, output_path, file_source=file_source
            )
        elif config.REFRESH_LOG_PATH:
            result.report_path = write_json_report(
                result.report_dict, config.REFRESH_LOG_PATH, file_source=file_source
            )

        result.success = True

    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        result.success = False

    return result


def generate_report(
    scan_result: Optional[ScanResult],
    extraction_result: Optional[ExtractionResult],
    processing_result: Optional[ProcessingResult],
    validation_result: Optional[ValidationResult],
    database_result: Optional[DatabaseResult],
) -> Dict[str, Any]:
    """
    Generate comprehensive report from all stage results.

    Args:
        All stage results (can be None).

    Returns:
        Complete report dictionary.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_uuid": None,
        "configuration": {
            "file_source_mode": config.FILE_SOURCE_MODE,
            "base_path": config.BASE_PATH,
            "database_names": config.get_database_names(),
            "dry_run": config.REFRESH_DRY_RUN,
            "force": config.REFRESH_FORCE,
        },
        "stages": {},
        "errors": [],
    }

    # Stage 1: Scan
    if scan_result:
        report["stages"]["scan"] = {
            "files_to_process": len(scan_result.files_to_process),
            "files_to_remove": len(scan_result.files_to_remove),
            "files_unchanged": scan_result.files_unchanged,
            "databases_scanned": scan_result.databases_scanned,
            "errors": len(scan_result.scan_errors),
        }
        report["errors"].extend(scan_result.scan_errors)

    # Stage 2: Extract
    if extraction_result:
        report["stages"]["extract"] = {
            "documents_extracted": len(extraction_result.extracted_documents),
            "documents_failed": len(extraction_result.failed_documents),
            "total_pages": extraction_result.total_pages,
        }
        for doc in extraction_result.failed_documents:
            if doc.extraction_error:
                report["errors"].append(
                    f"Extraction failed for {doc.file_info.file_name}: {doc.extraction_error}"
                )

    # Stage 3: Process
    if processing_result:
        report["stages"]["process"] = {
            "documents_processed": len(processing_result.processed_documents),
            "documents_failed": len(processing_result.failed_documents),
            "total_sections": processing_result.total_sections,
            "total_chunks": processing_result.total_chunks,
        }
        for doc in processing_result.failed_documents:
            if doc.processing_error:
                report["errors"].append(
                    f"Processing failed for {doc.file_info.file_name}: {doc.processing_error}"
                )

    # Stage 4: Validate
    if validation_result:
        report["stages"]["validate"] = {
            "documents_validated": len(validation_result.validated_documents),
            "documents_failed": len(validation_result.failed_documents),
            "total_warnings": validation_result.total_warnings,
            "total_errors": len(
                [e for e in validation_result.all_errors if e.severity == "error"]
            ),
        }
        for error in validation_result.all_errors:
            if error.severity == "error":
                report["errors"].append(
                    f"Validation error for {error.document_name}: {error.message}"
                )

    # Stage 5: Database
    if database_result:
        report["stages"]["database"] = {
            "documents_removed": database_result.documents_removed,
            "documents_inserted": database_result.documents_inserted,
            "sections_inserted": database_result.sections_inserted,
            "chunks_inserted": database_result.chunks_inserted,
            "errors": len(database_result.errors),
        }
        report["errors"].extend(database_result.errors)

    return report


def print_summary(report: Dict[str, Any]) -> None:
    """
    Print formatted summary to console.

    Args:
        report: Report dictionary from generate_report.
    """
    print("\n" + "=" * 60)
    print("DOCUMENT REFRESH PIPELINE SUMMARY")
    print("=" * 60)

    # Configuration
    config_section = report.get("configuration", {})
    print(f"\nConfiguration:")
    print(f"  File Source: {config_section.get('file_source_mode', 'unknown')}")
    print(f"  Base Path: {config_section.get('base_path', 'not set')}")
    print(f"  Databases: {', '.join(config_section.get('database_names', []))}")
    if config_section.get("dry_run"):
        print("  Mode: DRY RUN (no database changes)")
    if config_section.get("force"):
        print("  Mode: FORCE (reprocessing all files)")

    # Stages
    stages = report.get("stages", {})
    print("\n" + "-" * 60)
    print("Stage Results:")

    if "scan" in stages:
        s = stages["scan"]
        print(f"\n  Scan:")
        print(f"    Files to process: {s.get('files_to_process', 0)}")
        print(f"    Files to remove: {s.get('files_to_remove', 0)}")
        print(f"    Files unchanged: {s.get('files_unchanged', 0)}")
        print(f"    Databases: {', '.join(s.get('databases_scanned', []))}")

    if "extract" in stages:
        s = stages["extract"]
        print(f"\n  Extract:")
        print(f"    Documents extracted: {s.get('documents_extracted', 0)}")
        print(f"    Documents failed: {s.get('documents_failed', 0)}")
        print(f"    Total pages: {s.get('total_pages', 0)}")

    if "process" in stages:
        s = stages["process"]
        print(f"\n  Process:")
        print(f"    Documents processed: {s.get('documents_processed', 0)}")
        print(f"    Documents failed: {s.get('documents_failed', 0)}")
        print(f"    Sections created: {s.get('total_sections', 0)}")
        print(f"    Chunks created: {s.get('total_chunks', 0)}")

    if "validate" in stages:
        s = stages["validate"]
        print(f"\n  Validate:")
        print(f"    Documents validated: {s.get('documents_validated', 0)}")
        print(f"    Documents failed: {s.get('documents_failed', 0)}")
        print(f"    Warnings: {s.get('total_warnings', 0)}")

    if "database" in stages:
        s = stages["database"]
        print(f"\n  Database:")
        print(f"    Documents removed: {s.get('documents_removed', 0)}")
        print(f"    Documents inserted: {s.get('documents_inserted', 0)}")
        print(f"    Sections inserted: {s.get('sections_inserted', 0)}")
        print(f"    Chunks inserted: {s.get('chunks_inserted', 0)}")

    # Errors
    errors = report.get("errors", [])
    if errors:
        print("\n" + "-" * 60)
        print(f"Errors ({len(errors)}):")
        for error in errors[:10]:  # Show first 10
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    print("\n" + "=" * 60)


def write_json_report(
    report: Dict[str, Any],
    output_path: str,
    file_source: Optional[FileSource] = None,
) -> str:
    """
    Write report to JSON file.

    Args:
        report: Report dictionary.
        output_path: Path to write file.
        file_source: Optional FileSource for writing to NAS.

    Returns:
        Actual path where file was written.
    """
    path = output_path

    if file_source is not None:
        if not path.lower().endswith(".json"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"{path.rstrip('/')}/doc_refresh_report_{timestamp}.json"

        data = json.dumps(report, indent=2, default=str).encode("utf-8")
        file_source.write_data(data, path)
        logger.info("Report written to: %s", path)
        return path

    path_obj = Path(path)

    if path_obj.is_dir():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path_obj = path_obj / f"doc_refresh_report_{timestamp}.json"

    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Report written to: %s", path_obj)
    return str(path_obj)
