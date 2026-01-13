"""
Stage 2: Extract - Extract Content from Files.

This stage extracts text content from files identified in Stage 1.
Uses the content_extractor utility which supports:
- PDF files via pymupdf4llm
- DOCX files via mammoth

Functions:
    run_stage: Execute the extraction stage
    extract_file: Extract content from a single file
"""

import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from ..connections.file_source import FileSource, get_file_source
from ..stages.stage_1_scan import FileInfo
from ..utils.content_extractor import extract_pages, clean_text
from ..utils.env_config import config
from ..utils.process_monitoring import get_process_monitor

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDocument:
    """Extracted document with page content."""

    file_info: FileInfo
    pages: List[str] = field(default_factory=list)
    page_count: int = 0
    extraction_error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if extraction was successful."""
        return len(self.pages) > 0 and self.extraction_error is None


@dataclass
class ExtractionResult:
    """Result of the extraction stage."""

    extracted_documents: List[ExtractedDocument] = field(default_factory=list)
    failed_documents: List[ExtractedDocument] = field(default_factory=list)
    total_pages: int = 0


def run_stage(
    files_to_process: List[FileInfo],
    file_source: Optional[FileSource] = None,
) -> ExtractionResult:
    """
    Execute the extraction stage.

    Extracts text content from all files identified in Stage 1.

    Args:
        files_to_process: List of FileInfo objects from Stage 1.
        file_source: Optional FileSource instance (uses default if None).

    Returns:
        ExtractionResult with extracted documents and statistics.
    """
    monitor = get_process_monitor()
    monitor.start_stage("stage_2_extract")

    result = ExtractionResult()

    if not files_to_process:
        logger.info("No files to extract")
        monitor.end_stage("stage_2_extract", "completed")
        return result

    # Get file source
    if file_source is None:
        file_source = get_file_source()

    logger.info("Extracting content from %d files", len(files_to_process))

    # Create a temporary directory for file downloads (NAS mode)
    with tempfile.TemporaryDirectory() as temp_dir:
        for i, file_info in enumerate(files_to_process, 1):
            logger.info(
                "Processing file %d/%d: %s",
                i,
                len(files_to_process),
                file_info.file_name,
            )

            try:
                extracted = extract_file(file_info, file_source, temp_dir)

                if extracted.is_valid:
                    result.extracted_documents.append(extracted)
                    result.total_pages += extracted.page_count
                    logger.info(
                        "Extracted %d pages from %s",
                        extracted.page_count,
                        file_info.file_name,
                    )
                else:
                    result.failed_documents.append(extracted)
                    logger.warning(
                        "Failed to extract %s: %s",
                        file_info.file_name,
                        extracted.extraction_error,
                    )

            except Exception as exc:
                logger.error("Error extracting %s: %s", file_info.file_name, exc)
                result.failed_documents.append(
                    ExtractedDocument(
                        file_info=file_info,
                        extraction_error=str(exc),
                    )
                )

    # Log summary
    logger.info(
        "Extraction complete: %d successful (%d pages), %d failed",
        len(result.extracted_documents),
        result.total_pages,
        len(result.failed_documents),
    )

    monitor.add_stage_details(
        "stage_2_extract",
        documents_extracted=len(result.extracted_documents),
        documents_failed=len(result.failed_documents),
        total_pages=result.total_pages,
    )

    monitor.end_stage("stage_2_extract", "completed")
    return result


def extract_file(
    file_info: FileInfo,
    file_source: FileSource,
    temp_dir: str,
) -> ExtractedDocument:
    """
    Extract content from a single file.

    For NAS mode, downloads the file to temp directory first.
    For local mode, reads directly from the filesystem.

    Args:
        file_info: FileInfo object with file details.
        file_source: FileSource instance for file access.
        temp_dir: Temporary directory for file downloads.

    Returns:
        ExtractedDocument with extracted pages.
    """
    extracted = ExtractedDocument(file_info=file_info)

    try:
        # Determine the local path to process
        if config.FILE_SOURCE_MODE == "nas":
            # Download from NAS to temp directory
            local_path = file_source.copy_to_local(file_info.file_path, temp_dir)
            logger.debug("Downloaded to temp: %s", local_path)
        else:
            # Use the file path directly for local mode
            local_path = file_info.file_path

        # Verify file exists
        if not os.path.exists(local_path):
            extracted.extraction_error = f"File not found: {local_path}"
            return extracted

        # Extract pages using content_extractor
        pages = extract_pages(local_path)

        if not pages:
            extracted.extraction_error = "No content extracted from file"
            return extracted

        # Clean and store pages
        extracted.pages = [clean_text(page) for page in pages]
        extracted.page_count = len(extracted.pages)

        # Clean up temp file if NAS mode
        if config.FILE_SOURCE_MODE == "nas" and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass

        return extracted

    except Exception as exc:
        extracted.extraction_error = str(exc)
        return extracted
