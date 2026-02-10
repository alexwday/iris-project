#!/usr/bin/env python3
"""
Stage-by-Stage Test for Document Refresh Pipeline.

Tests each stage incrementally with sample PDFs.

Usage:
    python -m doc_refresh.testing.test_stages
    python -m doc_refresh.testing.test_stages --stage 1
    python -m doc_refresh.testing.test_stages --stage all
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doc_refresh.utils.logging_format import configure_root_logger

# Configure logging
configure_root_logger(logging.INFO)
logger = logging.getLogger(__name__)


# Test configuration
TEST_DIR = Path(__file__).parent / "test_docs"
DB_SOURCE = "test_docs"


def test_stage_1():
    """Test Stage 1: Scan."""
    print("\n" + "=" * 60)
    print("TESTING STAGE 1: SCAN")
    print("=" * 60)

    from doc_refresh.connections.file_source import LocalFileSource
    from doc_refresh.stages import stage_1_scan

    # Use local file source pointing to test_docs
    file_source = LocalFileSource(base_path=str(TEST_DIR.parent))

    # Run scan with test_docs as the database name
    result = stage_1_scan.run_stage(
        file_source=file_source,
        database_names=[DB_SOURCE],
        force=True,  # Force to process all files
    )

    print(f"\nScan Results:")
    print(f"  Files to process: {len(result.files_to_process)}")
    print(f"  Files to remove: {len(result.files_to_remove)}")
    print(f"  Files unchanged: {result.files_unchanged}")
    print(f"  Errors: {len(result.scan_errors)}")

    for f in result.files_to_process:
        print(f"\n  File: {f.file_name}")
        print(f"    Path: {f.relative_path}")
        print(f"    Size: {f.file_size} bytes")
        print(f"    Hash: {f.file_hash[:16]}...")
        print(f"    Action: {f.action}")

    return result


def test_stage_2(scan_result=None):
    """Test Stage 2: Extract."""
    print("\n" + "=" * 60)
    print("TESTING STAGE 2: EXTRACT")
    print("=" * 60)

    from doc_refresh.connections.file_source import LocalFileSource
    from doc_refresh.stages import stage_1_scan, stage_2_extract

    # If no scan result provided, run stage 1 first
    if scan_result is None:
        file_source = LocalFileSource(base_path=str(TEST_DIR.parent))
        scan_result = stage_1_scan.run_stage(
            file_source=file_source,
            database_names=[DB_SOURCE],
            force=True,
        )

    # Run extraction
    file_source = LocalFileSource(base_path=str(TEST_DIR.parent))
    result = stage_2_extract.run_stage(
        files_to_process=scan_result.files_to_process,
        file_source=file_source,
    )

    print(f"\nExtraction Results:")
    print(f"  Documents extracted: {len(result.extracted_documents)}")
    print(f"  Documents failed: {len(result.failed_documents)}")
    print(f"  Total pages: {result.total_pages}")

    for doc in result.extracted_documents:
        print(f"\n  Document: {doc.file_info.file_name}")
        print(f"    Pages: {doc.page_count}")
        print(f"    First page preview: {doc.pages[0][:200]}..." if doc.pages else "    No pages")

    return result


def test_stage_3(extraction_result=None):
    """Test Stage 3: Process."""
    print("\n" + "=" * 60)
    print("TESTING STAGE 3: PROCESS")
    print("=" * 60)

    from doc_refresh.connections.file_source import LocalFileSource
    from doc_refresh.stages import stage_1_scan, stage_2_extract, stage_3_process

    # If no extraction result provided, run stages 1 and 2 first
    if extraction_result is None:
        file_source = LocalFileSource(base_path=str(TEST_DIR.parent))
        scan_result = stage_1_scan.run_stage(
            file_source=file_source,
            database_names=[DB_SOURCE],
            force=True,
        )
        extraction_result = stage_2_extract.run_stage(
            files_to_process=scan_result.files_to_process,
            file_source=file_source,
        )

    # Run processing
    result = stage_3_process.run_stage(
        extracted_documents=extraction_result.extracted_documents,
    )

    print(f"\nProcessing Results:")
    print(f"  Documents processed: {len(result.processed_documents)}")
    print(f"  Documents failed: {len(result.failed_documents)}")
    print(f"  Total sections: {result.total_sections}")
    print(f"  Total chunks: {result.total_chunks}")

    for doc in result.processed_documents:
        print(f"\n  Document: {doc.file_info.file_name}")
        print(f"    Structure type: {doc.structure_type.value}")
        print(f"    Confidence: {doc.structure_confidence}")
        print(f"    Sections: {len(doc.sections)}")
        print(f"    Chunks: {len(doc.chunks)}")

        if doc.sections:
            print(f"    First section: {doc.sections[0].title}")
            print(f"      Summary: {doc.sections[0].summary[:100]}...")

        if doc.chunks:
            has_embedding = doc.chunks[0].embedding is not None
            print(f"    First chunk has embedding: {has_embedding}")

    return result


def test_stage_4(processing_result=None):
    """Test Stage 4: Validate."""
    print("\n" + "=" * 60)
    print("TESTING STAGE 4: VALIDATE")
    print("=" * 60)

    from doc_refresh.connections.file_source import LocalFileSource
    from doc_refresh.stages import stage_1_scan, stage_2_extract, stage_3_process, stage_4_validate

    # If no processing result provided, run stages 1-3 first
    if processing_result is None:
        file_source = LocalFileSource(base_path=str(TEST_DIR.parent))
        scan_result = stage_1_scan.run_stage(
            file_source=file_source,
            database_names=[DB_SOURCE],
            force=True,
        )
        extraction_result = stage_2_extract.run_stage(
            files_to_process=scan_result.files_to_process,
            file_source=file_source,
        )
        processing_result = stage_3_process.run_stage(
            extracted_documents=extraction_result.extracted_documents,
        )

    # Run validation
    result = stage_4_validate.run_stage(
        processed_documents=processing_result.processed_documents,
        strict=False,  # Allow warnings for testing
    )

    print(f"\nValidation Results:")
    print(f"  Documents validated: {len(result.validated_documents)}")
    print(f"  Documents failed: {len(result.failed_documents)}")
    print(f"  Total warnings: {result.total_warnings}")

    for doc in result.validated_documents:
        print(f"\n  Validated: {doc.document.file_info.file_name}")
        if doc.warnings:
            for w in doc.warnings:
                print(f"    Warning: [{w.error_type}] {w.message}")

    for doc in result.failed_documents:
        print(f"\n  Failed: {doc.file_info.file_name}")

    return result


def test_stage_5(validation_result=None, scan_result=None, dry_run=True):
    """Test Stage 5: Database."""
    print("\n" + "=" * 60)
    print("TESTING STAGE 5: DATABASE")
    print("=" * 60)

    from doc_refresh.connections.file_source import LocalFileSource
    from doc_refresh.stages import (
        stage_1_scan,
        stage_2_extract,
        stage_3_process,
        stage_4_validate,
        stage_5_database,
    )

    # If no results provided, run all previous stages
    if validation_result is None or scan_result is None:
        file_source = LocalFileSource(base_path=str(TEST_DIR.parent))
        scan_result = stage_1_scan.run_stage(
            file_source=file_source,
            database_names=[DB_SOURCE],
            force=True,
        )
        extraction_result = stage_2_extract.run_stage(
            files_to_process=scan_result.files_to_process,
            file_source=file_source,
        )
        processing_result = stage_3_process.run_stage(
            extracted_documents=extraction_result.extracted_documents,
        )
        validation_result = stage_4_validate.run_stage(
            processed_documents=processing_result.processed_documents,
            strict=False,
        )

    # Run database sync
    result = stage_5_database.run_stage(
        files_to_remove=scan_result.files_to_remove,
        validated_documents=validation_result.validated_documents,
        dry_run=dry_run,
    )

    print(f"\nDatabase Results (dry_run={dry_run}):")
    print(f"  Documents removed: {result.documents_removed}")
    print(f"  Documents inserted: {result.documents_inserted}")
    print(f"  Sections inserted: {result.sections_inserted}")
    print(f"  Chunks inserted: {result.chunks_inserted}")
    print(f"  Errors: {len(result.errors)}")

    return result


def test_stage_6(
    scan_result=None,
    extraction_result=None,
    processing_result=None,
    validation_result=None,
    database_result=None,
):
    """Test Stage 6: Report."""
    print("\n" + "=" * 60)
    print("TESTING STAGE 6: REPORT")
    print("=" * 60)

    from doc_refresh.stages import stage_6_report

    # Run report generation
    result = stage_6_report.run_stage(
        scan_result=scan_result,
        extraction_result=extraction_result,
        processing_result=processing_result,
        validation_result=validation_result,
        database_result=database_result,
    )

    if result.report_path:
        print(f"\nReport saved to: {result.report_path}")

    return result


def test_all_stages(dry_run=True):
    """Run all stages in sequence."""
    print("\n" + "=" * 60)
    print("TESTING ALL STAGES")
    print("=" * 60)

    from doc_refresh.connections.file_source import LocalFileSource
    from doc_refresh.stages import (
        stage_1_scan,
        stage_2_extract,
        stage_3_process,
        stage_4_validate,
        stage_5_database,
        stage_6_report,
    )

    file_source = LocalFileSource(base_path=str(TEST_DIR.parent))

    # Stage 1
    print("\n--- Stage 1: Scan ---")
    scan_result = stage_1_scan.run_stage(
        file_source=file_source,
        database_names=[DB_SOURCE],
        force=True,
    )
    print(f"Files to process: {len(scan_result.files_to_process)}")

    # Stage 2
    print("\n--- Stage 2: Extract ---")
    extraction_result = stage_2_extract.run_stage(
        files_to_process=scan_result.files_to_process,
        file_source=file_source,
    )
    print(f"Documents extracted: {len(extraction_result.extracted_documents)}")
    print(f"Total pages: {extraction_result.total_pages}")

    # Stage 3
    print("\n--- Stage 3: Process ---")
    processing_result = stage_3_process.run_stage(
        extracted_documents=extraction_result.extracted_documents,
    )
    print(f"Documents processed: {len(processing_result.processed_documents)}")
    print(f"Total sections: {processing_result.total_sections}")
    print(f"Total chunks: {processing_result.total_chunks}")

    # Stage 4
    print("\n--- Stage 4: Validate ---")
    validation_result = stage_4_validate.run_stage(
        processed_documents=processing_result.processed_documents,
        strict=False,
    )
    print(f"Documents validated: {len(validation_result.validated_documents)}")
    print(f"Documents failed: {len(validation_result.failed_documents)}")

    # Stage 5
    print("\n--- Stage 5: Database ---")
    database_result = stage_5_database.run_stage(
        files_to_remove=scan_result.files_to_remove,
        validated_documents=validation_result.validated_documents,
        dry_run=dry_run,
    )
    print(f"Documents inserted: {database_result.documents_inserted}")

    # Stage 6
    print("\n--- Stage 6: Report ---")
    report_result = stage_6_report.run_stage(
        scan_result=scan_result,
        extraction_result=extraction_result,
        processing_result=processing_result,
        validation_result=validation_result,
        database_result=database_result,
    )

    return report_result


def main():
    parser = argparse.ArgumentParser(description="Test doc_refresh stages")
    parser.add_argument(
        "--stage",
        type=str,
        default="1",
        choices=["1", "2", "3", "4", "5", "6", "all"],
        help="Stage to test (default: 1)",
    )
    parser.add_argument(
        "--real-db",
        action="store_true",
        help="Actually modify database (default: dry-run)",
    )
    args = parser.parse_args()

    print(f"Test directory: {TEST_DIR}")
    print(f"Database source: {DB_SOURCE}")

    if args.stage == "1":
        test_stage_1()
    elif args.stage == "2":
        test_stage_2()
    elif args.stage == "3":
        test_stage_3()
    elif args.stage == "4":
        test_stage_4()
    elif args.stage == "5":
        test_stage_5(dry_run=not args.real_db)
    elif args.stage == "6":
        test_stage_6()
    elif args.stage == "all":
        test_all_stages(dry_run=not args.real_db)


if __name__ == "__main__":
    main()
