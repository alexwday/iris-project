"""
Content Extraction Module for Document Refresh Pipeline.

Pluggable content extraction using:
- PDF: pymupdf4llm (with PyMuPDF fallback)
- DOCX: mammoth (converts to HTML then extracts text)

This module is designed to be swappable - in the future, different
extraction backends (OCR, cloud APIs, etc.) can be implemented
with the same interface.

Functions:
    extract_pages: Extract text pages from PDF or DOCX file
    clean_text: Normalize and clean extracted text
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try to import pymupdf4llm (preferred for PDF)
try:
    import pymupdf4llm

    _PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    _PYMUPDF4LLM_AVAILABLE = False

# Fallback to basic PyMuPDF
try:
    import pymupdf

    _PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz as pymupdf

        _PYMUPDF_AVAILABLE = True
    except ImportError:
        _PYMUPDF_AVAILABLE = False

# Try to import mammoth for DOCX
try:
    import mammoth

    _MAMMOTH_AVAILABLE = True
except ImportError:
    _MAMMOTH_AVAILABLE = False


def extract_pages(file_path: str) -> List[str]:
    """
    Extract text pages from a PDF or DOCX file.

    For PDF files:
        Uses pymupdf4llm.to_markdown() with page_chunks=True for best results.
        Falls back to basic PyMuPDF text extraction if pymupdf4llm unavailable.

    For DOCX files:
        Uses mammoth to convert to HTML, then extracts text content.
        DOCX files don't have natural page breaks, so content is returned
        as a single "page" unless section breaks are detected.

    Args:
        file_path: Path to the PDF or DOCX file.

    Returns:
        List of strings, one per page (or section for DOCX).

    Raises:
        ValueError: If file type is not supported.
        FileNotFoundError: If file does not exist.
        RuntimeError: If extraction fails.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".pdf":
        return _extract_pdf_pages(file_path)
    elif extension == ".docx":
        return _extract_docx_pages(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def _extract_pdf_pages(file_path: str) -> List[str]:
    """
    Extract pages from a PDF file.

    Uses pymupdf4llm for markdown-formatted extraction if available,
    otherwise falls back to basic PyMuPDF text extraction.
    """
    if _PYMUPDF4LLM_AVAILABLE:
        return _extract_pdf_with_pymupdf4llm(file_path)
    elif _PYMUPDF_AVAILABLE:
        return _extract_pdf_with_pymupdf(file_path)
    else:
        raise RuntimeError(
            "No PDF extraction library available. "
            "Install pymupdf4llm: pip install pymupdf4llm"
        )


def _extract_pdf_with_pymupdf4llm(file_path: str) -> List[str]:
    """Extract PDF pages using pymupdf4llm for markdown output."""
    try:
        # Extract as markdown with page chunks
        pages_data = pymupdf4llm.to_markdown(
            file_path,
            page_chunks=True,
            write_images=False,
            show_progress=False,
        )

        pages = []
        for page_data in pages_data:
            # Each page_data is a dict with 'text' key
            if isinstance(page_data, dict):
                text = page_data.get("text", "")
            else:
                text = str(page_data)
            cleaned = clean_text(text)
            pages.append(cleaned)

        logger.info(
            "Extracted %d pages from PDF using pymupdf4llm: %s",
            len(pages),
            file_path,
        )
        return pages

    except Exception as exc:
        logger.error("pymupdf4llm extraction failed for %s: %s", file_path, exc)
        # Try fallback
        if _PYMUPDF_AVAILABLE:
            logger.info("Falling back to basic PyMuPDF extraction")
            return _extract_pdf_with_pymupdf(file_path)
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc


def _extract_pdf_with_pymupdf(file_path: str) -> List[str]:
    """Extract PDF pages using basic PyMuPDF text extraction."""
    try:
        doc = pymupdf.open(file_path)
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            cleaned = clean_text(text)
            pages.append(cleaned)

        doc.close()

        logger.info(
            "Extracted %d pages from PDF using PyMuPDF: %s",
            len(pages),
            file_path,
        )
        return pages

    except Exception as exc:
        raise RuntimeError(f"PyMuPDF extraction failed: {exc}") from exc


def _extract_docx_pages(file_path: str) -> List[str]:
    """
    Extract content from a DOCX file.

    DOCX files don't have natural page breaks like PDFs.
    This function converts to HTML using mammoth, then extracts text.
    Content is split on section breaks if present, otherwise returned
    as a single "page".
    """
    if not _MAMMOTH_AVAILABLE:
        raise RuntimeError(
            "mammoth library not available. Install with: pip install mammoth"
        )

    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html_content = result.value

            # Log any conversion warnings
            if result.messages:
                for msg in result.messages:
                    logger.debug("mammoth warning: %s", msg)

        # Extract text from HTML
        text = _html_to_text(html_content)
        cleaned = clean_text(text)

        # Split on section breaks (indicated by multiple newlines or hr tags)
        # For now, return as single page - can be enhanced later
        pages = [cleaned] if cleaned.strip() else []

        logger.info(
            "Extracted content from DOCX (%d chars): %s",
            len(cleaned),
            file_path,
        )
        return pages

    except Exception as exc:
        raise RuntimeError(f"DOCX extraction failed: {exc}") from exc


def _html_to_text(html: str) -> str:
    """
    Convert HTML to plain text.

    Handles common HTML elements and extracts readable text content.
    """
    import html as html_module

    # Replace common block elements with newlines
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</td>", "\t", text, flags=re.IGNORECASE)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text, flags=re.IGNORECASE)

    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html_module.unescape(text)

    return text


def clean_text(text: str) -> str:
    """
    Normalize and clean extracted text.

    Performs:
    - Unicode normalization (NFKC)
    - Control character removal (except newlines/tabs)
    - Whitespace normalization
    - Line ending normalization

    Args:
        text: Raw extracted text.

    Returns:
        Cleaned text string.
    """
    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Remove control characters except newlines and tabs
    text = "".join(
        char for char in text if not unicodedata.category(char).startswith("C") or char in "\n\t"
    )

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse multiple blank lines into two newlines max
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Strip overall leading/trailing whitespace
    text = text.strip()

    return text


def get_supported_extensions() -> List[str]:
    """
    Get list of supported file extensions.

    Returns:
        List of supported extensions (e.g., ['.pdf', '.docx']).
    """
    extensions = []
    if _PYMUPDF4LLM_AVAILABLE or _PYMUPDF_AVAILABLE:
        extensions.append(".pdf")
    if _MAMMOTH_AVAILABLE:
        extensions.append(".docx")
    return extensions


def check_dependencies() -> dict:
    """
    Check which extraction dependencies are available.

    Returns:
        Dict with availability status for each library.
    """
    return {
        "pymupdf4llm": _PYMUPDF4LLM_AVAILABLE,
        "pymupdf": _PYMUPDF_AVAILABLE,
        "mammoth": _MAMMOTH_AVAILABLE,
        "pdf_support": _PYMUPDF4LLM_AVAILABLE or _PYMUPDF_AVAILABLE,
        "docx_support": _MAMMOTH_AVAILABLE,
    }
