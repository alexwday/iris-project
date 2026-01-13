"""
Reference Processor Utility Module.

Handles all reference-related processing for the IRIS system:
- Building consolidated reference indices from database query results
- Processing [REF:X] markers in streaming output
- Replacing reference markers with clickable href links

Functions:
    build_consolidated_reference_index: Consolidate reference indices from multiple databases
    process_streaming_reference_buffer: Smart buffering for reference replacement during streaming
    finalize_reference_replacements: Replace all remaining [REF:X] markers in final output
"""

import logging
import re
from typing import Any, Dict, Generator, List, Tuple

from .env_config import config

logger = logging.getLogger(__name__)

REF_PATTERN = re.compile(r"\[REF:([\d,\s\-]+)\]")
REF_INCOMPLETE_PATTERN = re.compile(r"\[REF:?[0-9,\s\-]*$")


def _is_structured_reference_format(ref_index: Dict[str, Any]) -> bool:
    """Check if reference index uses structured format with research_content.

    Structured format: {doc_name: {page_key: {research_content, file_link, ...}}}
    Legacy format: {ref_id: {doc_name, file_link, ...}}

    Args:
        ref_index: Reference index to check.

    Returns:
        bool: True if structured format, False if legacy format.
    """
    if not isinstance(ref_index, dict):
        return False

    for doc_data in ref_index.values():
        if not isinstance(doc_data, dict):
            continue
        for page_data in doc_data.values():
            if isinstance(page_data, dict) and "research_content" in page_data:
                return True
    return False


def _build_reference_link_text(
    source_filename: str,
    chapter_number: str,
    page_reference: str,
    page: int,
) -> str:
    """Build consistent link text for reference citations.

    Args:
        source_filename: Display name for the source file.
        chapter_number: Chapter number (empty string if not applicable).
        page_reference: Display page reference (may differ from actual page).
        page: Actual page number for PDF navigation.

    Returns:
        str: Formatted link text like "Filename, Ch. 5, Pg. 10" or "Filename, Pg. 10".
    """
    display_page = (
        page_reference if page_reference and page_reference != "0" else str(page)
    )

    if chapter_number:
        return f"{source_filename}, Ch. {chapter_number}, Pg. {display_page}"

    return f"{source_filename}, Pg. {display_page}"


def _build_reference_href(
    ref_data: Dict[str, Any],
    s3_base_path: str,
) -> str:
    """Build HTML href link for a reference.

    Args:
        ref_data: Reference data containing file_name, page, highlight_text, etc.
        s3_base_path: Base path for S3 URLs.

    Returns:
        str: HTML anchor tag with javascript:window.maven.openPdf() call.
    """
    file_name = ref_data.get("file_name") or ""
    try:
        page = int(ref_data.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    highlight_text = ref_data.get("highlight_text") or ""
    doc_name = ref_data.get("doc_name") or "Unknown Document"
    page_reference = str(ref_data.get("page_reference") or page)
    chapter_number = str(ref_data.get("chapter_number") or "")
    source_filename = ref_data.get("source_filename") or doc_name

    s3_url = f"{s3_base_path}/{file_name}"
    link_text = _build_reference_link_text(
        source_filename, chapter_number, page_reference, page
    )

    # Escape any quotes in highlight_text to prevent injection
    safe_highlight = highlight_text.replace('"', '\\"').replace("'", "\\'")

    js_call = f'javascript:window.maven.openPdf("{s3_url}", {page}, "{safe_highlight}")'
    return f"<a href='{js_call}'>{link_text}</a>"


def _parse_reference_ids(ref_text: str) -> List[str]:
    """Parse reference IDs from various formats.

    Handles:
    - Single ID: "5" -> ["5"]
    - Comma-separated: "1, 2, 3" -> ["1", "2", "3"]
    - Ranges: "1-5" -> ["1", "2", "3", "4", "5"]
    - Mixed: "1, 3-5, 7" -> ["1", "3", "4", "5", "7"]

    Args:
        ref_text: Raw reference text from [REF:...] pattern.

    Returns:
        list[str]: Individual reference ID strings.
    """
    ref_ids: List[str] = []

    for part in ref_text.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start_num = int(start_str.strip())
                end_num = int(end_str.strip())
                if start_num <= end_num:
                    ref_ids.extend(str(i) for i in range(start_num, end_num + 1))
                else:
                    # Handle reversed ranges gracefully
                    ref_ids.extend(str(i) for i in range(end_num, start_num + 1))
            except ValueError:
                # Not a valid range, treat as literal
                ref_ids.append(part)
        else:
            ref_ids.append(part)

    return ref_ids


def _generate_reference_links(
    ref_ids: List[str],
    reference_index: Dict[str, Dict[str, Any]],
    deduplicate_by_page: bool = True,
) -> Tuple[List[str], List[str]]:
    """Generate href links for a list of reference IDs.

    Args:
        ref_ids: List of reference ID strings to process.
        reference_index: Master reference index mapping ref IDs to data.
        deduplicate_by_page: If True, only one link per (doc, page) combo.

    Returns:
        tuple[list[str], list[str]]: Generated href strings and the found ref IDs.
    """
    page_links: Dict[Tuple[str, int], str] = {}
    found_refs: List[str] = []
    missing_refs: List[str] = []

    for ref_id in ref_ids:
        if ref_id not in reference_index:
            missing_refs.append(ref_id)
            continue

        found_refs.append(ref_id)
        ref_data = reference_index[ref_id]

        if deduplicate_by_page:
            doc_name = ref_data.get("doc_name", "Unknown Document")
            page = ref_data.get("page", 1)
            page_key = (doc_name, page)

            if page_key not in page_links:
                page_links[page_key] = _build_reference_href(
                    ref_data, config.S3_BASE_PATH
                )
        else:
            href = _build_reference_href(ref_data, config.S3_BASE_PATH)
            page_key = (ref_id, 0)
            page_links[page_key] = href

    if missing_refs:
        logger.warning("References not found in index: %s", missing_refs)

    return list(page_links.values()), found_refs


def build_consolidated_reference_index(
    all_reference_indices: Dict[str, Dict[str, Any]],
    aggregated_detailed_research: Dict[str, str],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Build a master reference index from all database reference indices.

    Consolidates reference indices from multiple databases, assigns sequential
    REF numbers, and updates the aggregated research text with the new REF tags.
    Handles both structured format (with page/section details) and legacy flat format.

    Args:
        all_reference_indices: Dict mapping database names to their reference indices.
            Can be structured format {doc_name: {page_x: {research_content, ...}}}
            or legacy format {ref_id: {doc_name, file_link, ...}}.
        aggregated_detailed_research: Dict mapping database names to research text.

    Returns:
        tuple[dict[str, dict[str, Any]], dict[str, str]]: Consolidated reference index
        with sequential IDs and updated research text with new REF tags.
    """
    master_reference_index: Dict[str, Dict[str, Any]] = {}
    structured_research_with_refs: Dict[str, Dict[str, Any]] = {}
    ref_counter = 1

    updated_research = dict(aggregated_detailed_research)

    for db_name, ref_index in all_reference_indices.items():
        if not ref_index:
            continue

        if _is_structured_reference_format(ref_index):
            db_research_with_refs: Dict[str, Any] = {}

            for doc_name in sorted(ref_index.keys()):
                doc_data = ref_index[doc_name]
                if not isinstance(doc_data, dict):
                    continue

                db_research_with_refs[doc_name] = {}

                # Sort by page number for consistent ordering
                # Check both "page" and "page_number" keys for compatibility
                def get_page_sort_key(item: Tuple[str, Any]) -> int:
                    page_data = item[1]
                    if isinstance(page_data, dict):
                        return page_data.get("page", page_data.get("page_number", 0))
                    return 0

                sorted_pages = sorted(doc_data.items(), key=get_page_sort_key)

                for page_key, page_data in sorted_pages:
                    if not isinstance(page_data, dict):
                        continue
                    if "research_content" not in page_data:
                        continue

                    # Extract page number (handle both key names)
                    page_number = page_data.get("page", page_data.get("page_number", 0))
                    research_content = page_data.get("research_content", "")
                    file_link = page_data.get("file_link", "")
                    file_name = page_data.get("file_name", "")
                    page_reference = page_data.get("page_reference", str(page_number))
                    chapter_number = page_data.get("chapter_number", "")
                    source_filename = page_data.get("source_filename", doc_name)

                    ref_id = str(ref_counter)
                    research_with_ref = f"{research_content} [REF:{ref_id}]"

                    db_research_with_refs[doc_name][page_key] = {
                        "research_content": research_with_ref,
                        "file_link": file_link,
                        "file_name": file_name,
                        "page_number": page_number,
                        "ref_id": ref_id,
                    }

                    master_reference_index[ref_id] = {
                        "doc_name": doc_name,
                        "file_link": file_link,
                        "file_name": file_name,
                        "page": page_number,
                        "page_reference": page_reference,
                        "chapter_number": chapter_number,
                        "source_filename": source_filename,
                        "highlight_text": "",
                        "source_db": db_name,
                    }

                    ref_counter += 1

            structured_research_with_refs[db_name] = db_research_with_refs

        else:
            # Legacy format: flat {ref_id: ref_data} mapping
            for old_ref_id, ref_data in ref_index.items():
                if not isinstance(ref_data, dict):
                    continue

                new_ref_id = str(ref_counter)
                master_reference_index[new_ref_id] = {
                    **ref_data,
                    "source_db": db_name,
                }

                # Update research text with new sequential IDs
                if db_name in updated_research:
                    updated_research[db_name] = updated_research[db_name].replace(
                        f"[REF:{old_ref_id}]", f"[REF:{new_ref_id}]"
                    )

                ref_counter += 1

    # Convert structured research to combined markdown for summarizer
    if structured_research_with_refs:
        for db_name, db_research in structured_research_with_refs.items():
            if not db_research:
                continue

            combined_research = f"# {db_name.upper()} Research Results\n\n"

            for doc_name, doc_data in db_research.items():
                if not doc_data:
                    continue

                combined_research += f"## {doc_name}\n\n"

                for page_key, page_data in doc_data.items():
                    if not isinstance(page_data, dict):
                        continue

                    page_number = page_data.get("page_number", 0)
                    research_content = page_data.get("research_content", "")

                    combined_research += f"### Page {page_number}\n\n"
                    combined_research += f"{research_content}\n\n"

                combined_research += "---\n\n"

            updated_research[db_name] = combined_research.strip()

    return master_reference_index, updated_research


def _replace_reference_markers_in_text(
    text: str,
    reference_index: Dict[str, Dict[str, Any]],
) -> str:
    """Replace all [REF:X] markers in text with href links.

    Handles individual refs [REF:1], comma-separated [REF:1,2,3], and ranges [REF:1-5].

    Args:
        text: Text containing [REF:X] markers.
        reference_index: Master reference index.

    Returns:
        str: Text with markers replaced by HTML links.
    """

    def replace_match(match: re.Match) -> str:
        ref_ids = _parse_reference_ids(match.group(1))
        links, found_refs = _generate_reference_links(ref_ids, reference_index)

        if not links:
            return match.group(0)

        logger.debug(
            "Replaced %s with %d link(s) for refs: %s",
            match.group(0),
            len(links),
            found_refs,
        )
        return f"\n\n{' '.join(links)}\n\n"

    return REF_PATTERN.sub(replace_match, text)


def finalize_reference_replacements(
    buffer: str, reference_index: Dict[str, Dict[str, Any]]
) -> Generator[str, None, None]:
    """Process all remaining buffer content and replace [REF:X] markers with href links.

    Called at the end of streaming to ensure all reference markers are converted
    to clickable links. Handles individual [REF:1], comma-separated [REF:1,2,3],
    and range [REF:1-12] formats.

    Args:
        buffer: The remaining buffer content to process.
        reference_index: Master reference index mapping REF IDs to reference data.

    Yields:
        str: Content with [REF:X] markers replaced by HTML href links.
    """
    if not buffer:
        return

    if not reference_index:
        yield buffer
        return

    processed = _replace_reference_markers_in_text(buffer, reference_index)
    yield processed


def process_streaming_reference_buffer(
    buffer: str, reference_index: Dict[str, Dict[str, Any]], buffer_size: int = 80
) -> Tuple[str, str]:
    """Smart buffering for streaming reference replacement.

    Accumulates streaming chunks and processes complete reference patterns immediately,
    ensuring href links are sent before the UI displays [REF:X] tags. Handles incomplete
    patterns at buffer boundaries by keeping them for the next chunk.

    Args:
        buffer: Current buffer content accumulated from stream.
        reference_index: Master reference index mapping REF IDs to reference data.
        buffer_size: Maximum buffer size before forcing output (default: 80).

    Returns:
        tuple[str, str]: Processed content ready to yield and incomplete content
            to carry forward.
    """
    if not buffer:
        return "", ""

    all_matches = list(REF_PATTERN.finditer(buffer))

    if not all_matches:
        incomplete_match = REF_INCOMPLETE_PATTERN.search(buffer)

        if incomplete_match:
            return (
                buffer[: incomplete_match.start()],
                buffer[incomplete_match.start() :],
            )

        if len(buffer) < buffer_size:
            if buffer.endswith("["):
                return buffer[:-1], "["
            return buffer, ""
        potential_ref_start = buffer.rfind("[")
        if potential_ref_start != -1 and potential_ref_start > len(buffer) - 15:
            return buffer[:potential_ref_start], buffer[potential_ref_start:]
        keep_chars = min(10, len(buffer) // 3)
        if keep_chars > 0:
            return buffer[:-keep_chars], buffer[-keep_chars:]
        return buffer, ""

    last_ref_end = max(m.end() for m in all_matches)

    trailing = buffer[last_ref_end:]
    incomplete_in_trailing = REF_INCOMPLETE_PATTERN.search(trailing)

    if incomplete_in_trailing:
        split_point = last_ref_end + incomplete_in_trailing.start()
        content_to_process = buffer[:split_point]
        remaining = buffer[split_point:]
    else:
        content_to_process = buffer
        remaining = ""

    processed = _replace_reference_markers_in_text(
        content_to_process, reference_index
    )

    return processed, remaining
