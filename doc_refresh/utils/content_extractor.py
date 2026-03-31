"""
Content Extraction Module for Document Refresh Pipeline.

Provides content extraction for PDF and DOCX files:
- PDF: pymupdf4llm (markdown-formatted extraction with page chunks)
- DOCX: LibreOffice headless conversion to PDF, then pymupdf4llm extraction

Image artifacts (markdown images, HTML img tags, base64 data URIs) are
stripped during the clean_text() pass so downstream LLM prompts receive
only textual content.

Functions:
    extract_pages: Extract text pages from PDF or DOCX file
    clean_text: Normalize and clean extracted text
    convert_docx_to_pdf: Convert DOCX to PDF via LibreOffice headless
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import pymupdf4llm

    _PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    _PYMUPDF4LLM_AVAILABLE = False


def extract_pages(file_path: str) -> List[str]:
    """
    Extract text pages from a PDF or DOCX file.

    For PDF files:
        Uses pymupdf4llm.to_markdown() with page_chunks=True.

    For DOCX files:
        Converts to PDF via LibreOffice headless, then extracts pages
        from the resulting PDF using pymupdf4llm.

    Args:
        file_path: Path to the PDF or DOCX file.

    Returns:
        List of strings, one per page.

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
        pdf_path = convert_docx_to_pdf(file_path, str(path.parent))
        return _extract_pdf_pages(pdf_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def _extract_pdf_pages(file_path: str) -> List[str]:
    """Extract pages from a PDF using pymupdf4llm."""
    if not _PYMUPDF4LLM_AVAILABLE:
        raise RuntimeError(
            "pymupdf4llm is not available. "
            "Install with: pip install pymupdf4llm"
        )
    return _extract_pdf_with_pymupdf4llm(file_path)


def _extract_pdf_with_pymupdf4llm(file_path: str) -> List[str]:
    """Extract PDF pages using pymupdf4llm for markdown output."""
    try:
        pages_data = pymupdf4llm.to_markdown(
            file_path,
            page_chunks=True,
            write_images=False,
            show_progress=False,
        )
    except AttributeError as exc:
        if "tables" in str(exc):
            logger.warning(
                "Table detection failed for %s (%s), retrying without table extraction",
                file_path,
                exc,
            )
            pages_data = pymupdf4llm.to_markdown(
                file_path,
                page_chunks=True,
                write_images=False,
                show_progress=False,
                table_strategy="",
            )
        else:
            raise

    if not pages_data:
        return []

    pages = []
    for page_data in pages_data:
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


def convert_docx_to_pdf(docx_path: str, output_dir: str) -> str:
    """
    Convert a DOCX file to PDF using LibreOffice headless.

    Args:
        docx_path: Path to the DOCX file.
        output_dir: Directory to write the output PDF.

    Returns:
        Path to the generated PDF file.

    Raises:
        RuntimeError: If LibreOffice conversion fails.
    """
    docx = Path(docx_path)
    expected_pdf = Path(output_dir) / f"{docx.stem}.pdf"

    libreoffice_cmd = _resolve_libreoffice_command()

    user_install_dir = tempfile.mkdtemp(prefix="lo_profile_")
    try:
        result = subprocess.run(
            [
                libreoffice_cmd,
                "--headless",
                f"-env:UserInstallation=file://{user_install_dir}",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed (exit {result.returncode}): "
                f"{result.stderr.strip()}"
            )

        if not expected_pdf.exists():
            raise RuntimeError(
                f"LibreOffice conversion produced no output file: {expected_pdf}"
            )

        logger.info("Converted DOCX to PDF: %s -> %s", docx_path, expected_pdf)
        return str(expected_pdf)

    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice executable not found. Set LIBREOFFICE_BIN, ensure "
            "'libreoffice' or 'soffice' is on PATH, or install LibreOffice."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"LibreOffice conversion timed out after 300s: {docx_path}"
        )
    finally:
        shutil.rmtree(user_install_dir, ignore_errors=True)


def _resolve_libreoffice_command() -> str:
    """Resolve a usable LibreOffice CLI executable path.

    Priority:
    1. LIBREOFFICE_BIN env var (absolute path or command name)
    2. PATH lookup: libreoffice
    3. PATH lookup: soffice
    4. macOS app bundle path
    """
    env_override = os.getenv("LIBREOFFICE_BIN", "").strip()
    if env_override:
        if os.path.isabs(env_override):
            if os.path.exists(env_override):
                return env_override
        else:
            resolved = shutil.which(env_override)
            if resolved:
                return resolved

    for candidate in ("libreoffice", "soffice"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    mac_soffice = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.exists(mac_soffice):
        return mac_soffice

    # Let subprocess raise FileNotFoundError with the conventional command.
    return "libreoffice"


def clean_text(text: str) -> str:
    """
    Normalize and clean extracted text.

    Performs:
    - Unicode normalization (NFKC)
    - Image artifact removal (markdown images, HTML img tags, base64 data URIs)
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

    # Fix combining diacriticals separated from base char by a space
    text = re.sub(r'(\w) ([\u0300-\u036f])', r'\1\2', text)
    text = unicodedata.normalize("NFKC", text)

    # Strip markdown images: ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)

    # Strip HTML img tags: <img ...> or <img ... />
    text = re.sub(r"<img[^>]*>", "", text, flags=re.IGNORECASE)

    # Strip base64 data URIs: data:image/...;base64,...
    text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "", text)

    # Strip orphaned long base64 blobs (500+ chars of base64 alphabet)
    text = re.sub(r"[A-Za-z0-9+/=]{500,}", "", text)

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

    # Strip standalone page numbers at start/end of page (1-4 digits only)
    text = re.sub(r'^\s*\d{1,4}\s*\n', '', text)
    text = re.sub(r'\n\s*\d{1,4}\s*$', '', text)

    # Strip trailing proceedings-style footers
    text = re.sub(
        r'\n_[^_]{10,}_,?\s*pages\s+\d+[–\-]\d+.*$',
        '', text, flags=re.DOTALL
    )

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
    if _PYMUPDF4LLM_AVAILABLE:
        extensions.append(".pdf")
        extensions.append(".docx")
    extensions.append(".xlsx")
    return extensions


def check_dependencies() -> dict:
    """
    Check which extraction dependencies are available.

    Returns:
        Dict with availability status for each library.
    """
    return {
        "pymupdf4llm": _PYMUPDF4LLM_AVAILABLE,
        "pdf_support": _PYMUPDF4LLM_AVAILABLE,
        "docx_support": _PYMUPDF4LLM_AVAILABLE,
        "xlsx_support": True,
    }
