# services/src/chat_model/model.py
"""
Model Initialization and Setup Module (Async Core with Sync Wrapper)

This module serves as the main entry point for the IRIS application.
It uses an asynchronous core for parallel processing but provides a
synchronous interface for compatibility with standard Python iteration.

Functions:
    model: Synchronous wrapper that runs the async core and yields results.
    _model_async_generator: Main async core function handling the workflow.

Dependencies:
    - logging
    - SSL certificate setup
    - OAuth authentication
    - Conversation processing
    - Agent orchestration (async components)
"""

import inspect
import concurrent.futures
import json
import logging
import time
import uuid  # Import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Generator, Callable, Tuple

# ... (Keep existing imports) ...
from ..global_prompts.database_statement import get_available_databases

# Import the connector, but not the removed usage functions
from ..llm_connectors.rbc_openai import (
    call_llm,
)  # Assuming this is the correct import now

# Import sync version of route_query
from ..agents.database_subagents.database_router import route_query_sync

# Import config for global access
from ..initial_setup.env_config import config

# Import database connection utilities for APG catalog search
from ..initial_setup.db_config import connect_to_db
import psycopg2.extras
from pgvector.psycopg2 import register_vector


def _generate_query_embedding(
    query: str, token: Optional[str] = None
) -> Tuple[Optional[List[float]], Optional[Dict[str, Any]]]:
    """
    Generates embedding for the query string using call_llm.

    Args:
        query (str): The input query string to embed
        token (Optional[str]): OAuth token for API authentication

    Returns:
        Tuple[Optional[List[float]], Optional[Dict[str, Any]]]:
            - Embedding vector
            - Usage details dictionary
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating embedding for query: '{query[:100]}...'")
    usage_details = None

    try:
        model_config = config.get_model_config("embedding")
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        completion_cost = model_config.get("completion_token_cost", 0.0)

        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": prompt_cost,
            "completion_token_cost": completion_cost,
            "model": model_name,
            "input": [query],  # API expects a list
            "dimensions": 2000,  # OpenAI embedding dimensions
            "database_name": "apg_catalog",
            "is_embedding": True,
        }

        # Direct synchronous call - returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Embedding Usage details: {usage_details}")
        else:
            response = result
            logger.debug("call_llm did not return usage_details")

        if (
            response
            and hasattr(response, "data")
            and response.data
            and hasattr(response.data[0], "embedding")
            and response.data[0].embedding
        ):
            logger.info("Embedding generated successfully.")
            return response.data[0].embedding, usage_details
        else:
            logger.error(
                "No embedding data received from API.",
                extra={"api_response": response},
            )
            return None, usage_details

    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}", exc_info=True)
        return None, usage_details


def search_apg_catalog_by_embedding(
    research_statement: str,
    token: Optional[str] = None,
    top_k: int = 5,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Search the apg_catalog table using embeddings to find relevant documents.

    Args:
        research_statement (str): The research statement to search for
        token (Optional[str]): OAuth token for API authentication
        top_k (int): Number of top results to retrieve (default 5)

    Returns:
        Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
            - List of matching documents with document_source and document_description
            - Usage details dictionary for the embedding call, or None if error
    """
    logger = logging.getLogger(__name__)
    logger.info(
        f"Searching apg_catalog for research statement: '{research_statement[:100]}...'"
    )
    usage_details = None

    conn = None
    cursor = None

    try:
        # Generate embedding for the research statement
        query_embedding, usage_details = _generate_query_embedding(
            research_statement, token
        )

        if query_embedding is None:
            logger.error("Could not generate embedding for research statement")
            return [], usage_details

        # Connect to database
        conn = connect_to_db()
        if conn is None:
            logger.error("Failed to connect to database for apg_catalog search")
            return [], usage_details

        register_vector(conn)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Perform vector search against apg_catalog table
        if available_databases:
            # Build the IN clause for filtering by document_source
            db_sources = list(available_databases.keys())
            placeholders = ", ".join(["%s"] * len(db_sources))
            sql = f"""
                SELECT
                    document_source,
                    document_description,
                    document_type,
                    document_name,
                    1 - (document_usage_embedding <=> %s::vector) AS similarity_score
                FROM apg_catalog
                WHERE document_usage_embedding IS NOT NULL
                    AND document_source IN ({placeholders})
                ORDER BY similarity_score DESC
                LIMIT %s;
            """
            params = [query_embedding] + db_sources + [top_k]
        else:
            # No filtering - original query
            sql = """
                SELECT
                    document_source,
                    document_description,
                    document_type,
                    document_name,
                    1 - (document_usage_embedding <=> %s::vector) AS similarity_score
                FROM apg_catalog
                WHERE document_usage_embedding IS NOT NULL
                ORDER BY similarity_score DESC
                LIMIT %s;
            """
            params = [query_embedding, top_k]

        cursor.execute(sql, params)
        results_raw = cursor.fetchall()

        # Convert to list of dictionaries
        results = []
        for i, row in enumerate(results_raw):
            record = dict(row)
            record["rank"] = i + 1
            results.append(record)

        logger.info(f"Found {len(results)} matching documents in apg_catalog")

        # Log the top 5 document names for debugging
        if results:
            logger.info("Top 5 APG Catalog document names:")
            for i, doc in enumerate(results[:5], 1):
                logger.info(
                    f"  {i}. {doc.get('document_name', 'N/A')} (score: {doc.get('similarity_score', 0.0):.3f})"
                )

        return results, usage_details

    except Exception as e:
        logger.error(f"Error searching apg_catalog: {e}", exc_info=True)
        return [], usage_details
    finally:
        # Ensure database connections are properly closed
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor: {e}")
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")


# --- Formatting Function (Remains Synchronous) ---
# This function might need adjustment later if debug_data structure changes significantly
def format_usage_summary(
    agent_token_usage: Dict[str, Any], start_time: Optional[str] = None
) -> str:
    """
    Format token usage and timing information into a nicely formatted string.
    Note: Database usage is now included within agent_token_usage due to central logging.

    Args:
        agent_token_usage (dict): Accumulated token usage dictionary with keys like
                                  'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost'.
        start_time (str, optional): ISO format timestamp of when processing started.

    Returns:
        str: Formatted usage summary as markdown.
    """
    duration = None
    if start_time:
        try:
            end_dt = datetime.now()
            start_dt = datetime.fromisoformat(start_time)
            duration = (end_dt - start_dt).total_seconds()
        except ValueError:
            logging.getLogger().warning(
                f"Could not parse start_time for duration calculation: {start_time}"
            )
            duration = None

    usage_summary = "\n\n---\n"
    usage_summary += "## Agent Usage Statistics\n\n"
    usage_summary += (
        f"- Overall Input tokens: {agent_token_usage.get('prompt_tokens', 0)}\n"
    )
    usage_summary += (
        f"- Overall Output tokens: {agent_token_usage.get('completion_tokens', 0)}\n"
    )
    usage_summary += (
        f"- Overall Total tokens: {agent_token_usage.get('total_tokens', 0)}\n"
    )
    usage_summary += f"- Overall Cost: ${agent_token_usage.get('cost', 0.0):.6f}\n"
    if duration is not None:
        usage_summary += f"- Total Time: {duration:.2f} seconds\n"

    return usage_summary


# --- Helper functions for reference processing ---
def _process_final_references(
    buffer: str, reference_index: Dict[str, Dict[str, Any]]
) -> Generator[str, None, None]:
    """
    Process all remaining buffer content and replace [REF:X] markers with href links.
    This is a generator function for final processing.
    """
    import re

    logger = logging.getLogger(__name__)

    # Process all remaining content - support both individual and legacy formats
    def replace_refs(match):
        """Replace REF:x references with formatted citations."""
        ref_text = match.group(1)

        # Parse reference IDs based on format
        ref_ids: List[str] = []
        if "," in ref_text or "-" in ref_text:
            # Legacy format: comma-separated or range
            for part in ref_text.split(","):
                part = part.strip()
                if "-" in part:
                    # Handle ranges like "1-12"
                    try:
                        start, end = part.split("-", 1)
                        start_num = int(start.strip())
                        end_num = int(end.strip())
                        ref_ids.extend(str(i) for i in range(start_num, end_num + 1))
                    except ValueError:
                        # If parsing fails, treat as regular ID
                        ref_ids.append(part)
                else:
                    ref_ids.append(part)
        else:
            # Individual format: single reference ID
            ref_ids = [ref_text]

        # Generate href links - group by page to avoid duplicates
        page_links = {}  # Map (doc_name, page) -> href
        found_refs = []  # Track which refs were actually found

        for ref_id in ref_ids:
            if ref_id in reference_index:
                found_refs.append(ref_id)
                ref_data = reference_index[ref_id]
                file_link = ref_data.get("file_link", "")
                file_name = ref_data.get("file_name", "")
                page = ref_data.get("page", 1)
                highlight_text = ref_data.get("highlight_text", "")
                doc_name = ref_data.get("doc_name", "Unknown Document")

                # Extract additional fields for semantic search
                page_reference = ref_data.get(
                    "page_reference", str(page)
                )  # Display reference
                chapter_number = ref_data.get("chapter_number", "")  # Chapter number
                source_filename = ref_data.get(
                    "source_filename", doc_name
                )  # Original document name
                
                # Debug logging to verify page numbers
                logger.debug(
                    f"REF:{ref_id} - page={page}, page_reference={page_reference}, "
                    f"chapter={chapter_number}, source={source_filename}"
                )

                # Create S3 URL using S3_BASE_PATH + file_name
                s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                # Create href link with 3-parameter format: filename, page, highlight_text
                page_key = (doc_name, page)
                if page_key not in page_links:
                    # Build link text with new format: source_filename, Ch. chapter_number, Pg. page_reference
                    # Always show page_reference when available (it's the display text)
                    if chapter_number:
                        if page_reference and page_reference != "0":
                            # Show full format with page reference
                            link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page_reference}"
                        else:
                            # No page_reference, fallback to page number
                            link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page}"
                    else:
                        # Fallback for catalog search or when chapter not available
                        if page_reference and page_reference != "0":
                            link_text = f"📄 {source_filename}, Pg. {page_reference}"
                        else:
                            # No page_reference, fallback to page number
                            link_text = f"📄 {source_filename}, Pg. {page}"
                    
                    # Use 'page' (which contains page_number) for PDF navigation
                    # page_reference is only for display text
                    href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'
                    page_links[page_key] = href
            else:
                logger.warning(f"Reference {ref_id} not found in index")

        links = list(page_links.values())

        # Return the reference line with links
        if links:
            result = f"\n\n{' '.join(links)}\n\n"
            logger.info(
                f"Final processing: Replaced {match.group(0)} with {len(links)} link(s) for refs: {found_refs}"
            )
            return result
        else:
            return match.group(0)  # Keep original if no match

    # Process both individual [REF:x] and legacy formats [REF:x,y,z] or [REF:x-y]
    # First process individual references
    processed = re.sub(r"\[REF:(\d+)\]", replace_refs, buffer)
    # Then process any remaining legacy patterns
    processed = re.sub(r"\[REF:([\d,\s\-]+)\]", replace_refs, processed)
    yield processed


def _process_reference_buffer(
    buffer: str, reference_index: Dict[str, Dict[str, Any]], buffer_size: int = 80
) -> tuple[str, str]:
    """
    Smart buffering: accumulate chunks and process complete reference patterns immediately.
    This ensures href links are sent in the stream before the UI displays [REF:X] tags.
    Returns tuple of (processed_content_to_output, remaining_buffer).
    """
    import re

    logger = logging.getLogger(__name__)

    # Debug logging
    logger.debug(
        f"Buffer processing: buffer length={len(buffer)}, content preview: '{buffer[-50:]}'"
    )
    if "[REF:" in buffer:
        ref_matches = re.findall(r"\[REF:\d+\]", buffer)
        logger.debug(f"Found individual references in buffer: {ref_matches}")

    # Look for all reference patterns
    # Individual reference pattern for processing
    individual_pattern = r"\[REF:(\d+)\]"
    # Legacy patterns: comma-separated [REF:1,2,3] and ranges [REF:1-12]
    legacy_pattern = r"\[REF:([\d,\s\-]+)\]"

    # Find all individual references
    individual_refs = list(re.finditer(individual_pattern, buffer))
    logger.debug(
        f"Found {len(individual_refs)} individual references: {[m.group(0) for m in individual_refs]}"
    )

    # Find legacy format references that aren't single numbers
    legacy_refs = []
    for legacy_match in re.finditer(legacy_pattern, buffer):
        legacy_text = legacy_match.group(1)
        # Only include if it's actually comma-separated or range format (not just a single number)
        if "," in legacy_text or "-" in legacy_text:
            # Check if this legacy ref overlaps with any individual reference
            overlaps = False
            for ind_ref in individual_refs:
                if (
                    legacy_match.start() < ind_ref.end()
                    and legacy_match.end() > ind_ref.start()
                ):
                    overlaps = True
                    break
            if not overlaps:
                legacy_refs.append(legacy_match)

    logger.debug(
        f"Found {len(legacy_refs)} legacy references: {[m.group(0) for m in legacy_refs]}"
    )

    all_matches = individual_refs + legacy_refs

    # Check if we have complete patterns or need to keep buffering
    if not all_matches:
        logger.debug(f"No complete references found in buffer")
        if len(buffer) < buffer_size:
            # Check for incomplete references at the end of buffer
            if buffer.endswith("[") or re.search(r"\[REF:?\d*$", buffer):
                # Incomplete reference at end, keep buffering
                logger.debug(
                    f"Incomplete reference at end, keeping buffer: '{buffer[-20:]}'"
                )
                return "", buffer
            # No incomplete references and buffer not full - output what we have
            logger.debug(
                f"No references and buffer not full, outputting buffer content"
            )
            return buffer, ""
        else:
            # Buffer is full but no references - handle potential partial references
            potential_ref_start = buffer.rfind("[")
            if potential_ref_start != -1 and potential_ref_start > len(buffer) - 15:
                # Keep potential reference start in buffer
                logger.debug(
                    f"Buffer full, keeping potential ref at end: '{buffer[potential_ref_start:]}'"
                )
                processed_content = buffer[:potential_ref_start]
                remaining_buffer = buffer[potential_ref_start:]
                return processed_content, remaining_buffer
            else:
                # No potential reference at end - output most of buffer but keep a small amount
                keep_chars = min(10, len(buffer) // 3)
                processed_content = buffer[:-keep_chars] if keep_chars > 0 else buffer
                remaining_buffer = buffer[-keep_chars:] if keep_chars > 0 else ""
                logger.debug(f"Buffer full, no refs, keeping {keep_chars} chars")
                return processed_content, remaining_buffer

    # Before processing, check if there's content after the last complete reference that needs to be preserved
    # Find the rightmost complete reference position in the original buffer
    rightmost_ref_end = 0
    for match in all_matches:
        rightmost_ref_end = max(rightmost_ref_end, match.end())

    # Check what comes after the last complete reference
    trailing_content = (
        buffer[rightmost_ref_end:] if rightmost_ref_end < len(buffer) else ""
    )

    logger.debug(
        f"Processing {len(all_matches)} references in buffer, trailing content: '{trailing_content}'"
    )

    # Process matches from end to start to maintain string positions
    all_matches.sort(key=lambda x: x.start(), reverse=True)
    processed_content = buffer

    for match in all_matches:
        match_text = match.group(0)

        if match in individual_refs:
            # This is an individual reference: [REF:1]
            ref_id = match.group(1)

            # Generate href link
            if ref_id in reference_index:
                ref_data = reference_index[ref_id]
                file_link = ref_data.get("file_link", "")
                file_name = ref_data.get("file_name", "")
                page = ref_data.get("page", 1)
                highlight_text = ref_data.get("highlight_text", "")
                doc_name = ref_data.get("doc_name", "Unknown Document")

                # Extract additional fields for semantic search
                page_reference = ref_data.get(
                    "page_reference", str(page)
                )  # Display reference
                chapter_number = ref_data.get("chapter_number", "")  # Chapter number
                source_filename = ref_data.get(
                    "source_filename", doc_name
                )  # Original document name

                # Create S3 URL using S3_BASE_PATH + file_name
                s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                # Create href link with 3-parameter format: filename, page, highlight_text
                # Build link text with new format: source_filename, Ch. chapter_number, Pg. page_reference
                # Handle missing page_reference gracefully
                if chapter_number:
                    if (
                        page_reference
                        and page_reference != str(page)
                        and page_reference != "0"
                    ):
                        link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page_reference}"
                    else:
                        # No valid page_reference, just show source and chapter
                        link_text = f"📄 {source_filename}, Ch. {chapter_number}"
                else:
                    # Fallback for catalog search or when chapter not available
                    if (
                        page_reference
                        and page_reference != str(page)
                        and page_reference != "0"
                    ):
                        link_text = f"📄 {source_filename}, Pg. {page_reference}"
                    else:
                        # No valid page_reference, just show source
                        link_text = f"📄 {source_filename}"
                href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'

                replacement = f" {href} "
                processed_content = (
                    processed_content[: match.start()]
                    + replacement
                    + processed_content[match.end() :]
                )
                logger.debug(
                    f"Replaced individual {match_text} with link for ref: {ref_id}"
                )
            else:
                logger.warning(f"Reference {ref_id} not found in index")

        else:
            # This is a legacy format reference: [REF:1,2,3] or [REF:1-12]
            ref_text = match.group(1)
            ref_ids: List[str] = []

            for part in ref_text.split(","):
                part = part.strip()
                if "-" in part:
                    # Handle ranges like "1-12"
                    try:
                        start, end = part.split("-", 1)
                        start_num = int(start.strip())
                        end_num = int(end.strip())
                        ref_ids.extend(str(i) for i in range(start_num, end_num + 1))
                    except ValueError:
                        # If parsing fails, treat as regular ID
                        ref_ids.append(part)
                else:
                    ref_ids.append(part)

            # Generate href links
            page_links = {}
            found_refs = []

            for ref_id in ref_ids:
                if ref_id in reference_index:
                    found_refs.append(ref_id)
                    ref_data = reference_index[ref_id]
                    file_link = ref_data.get("file_link", "")
                    file_name = ref_data.get("file_name", "")
                    page = ref_data.get("page", 1)
                    highlight_text = ref_data.get("highlight_text", "")
                    doc_name = ref_data.get("doc_name", "Unknown Document")

                    # Extract additional fields for semantic search
                    page_reference = ref_data.get(
                        "page_reference", str(page)
                    )  # Display reference
                    chapter_number = ref_data.get(
                        "chapter_number", ""
                    )  # Chapter number
                    source_filename = ref_data.get(
                        "source_filename", doc_name
                    )  # Original document name

                    # Create S3 URL using S3_BASE_PATH + file_name
                    s3_url = f"{config.S3_BASE_PATH}/{file_name}"

                    # Create href link with 3-parameter format: filename, page, highlight_text
                    page_key = (doc_name, page)
                    if page_key not in page_links:
                        # Build link text with new format: source_filename, Ch. chapter_number, Pg. page_reference
                        # Handle missing page_reference gracefully
                        if chapter_number:
                            if (
                                page_reference
                                and page_reference != str(page)
                                and page_reference != "0"
                            ):
                                link_text = f"📄 {source_filename}, Ch. {chapter_number}, Pg. {page_reference}"
                            else:
                                # No valid page_reference, just show source and chapter
                                link_text = (
                                    f"📄 {source_filename}, Ch. {chapter_number}"
                                )
                        else:
                            # Fallback for catalog search or when chapter not available
                            if (
                                page_reference
                                and page_reference != str(page)
                                and page_reference != "0"
                            ):
                                link_text = (
                                    f"📄 {source_filename}, Pg. {page_reference}"
                                )
                            else:
                                # No valid page_reference, just show source
                                link_text = f"📄 {source_filename}"
                        href = f'<a href=\'javascript:window.maven.openPdf("{s3_url}", {page}, "{highlight_text}")\'>{link_text}</a>'
                        page_links[page_key] = href
                else:
                    logger.warning(f"Reference {ref_id} not found in index")

            links = list(page_links.values())

            if links:
                replacement = f" {' '.join(links)} "
                processed_content = (
                    processed_content[: match.start()]
                    + replacement
                    + processed_content[match.end() :]
                )
                logger.debug(
                    f"Replaced legacy {match.group(0)} with {len(links)} link(s) for refs: {found_refs}"
                )

    # Check if trailing content looks like the start of an incomplete reference
    if trailing_content and (
        trailing_content.startswith("[") or re.search(r"\[REF:?\d*$", trailing_content)
    ):
        # There's an incomplete reference after our processed references
        # Find where this trailing content starts in the processed buffer and preserve it
        # Since we processed from right to left, the trailing incomplete reference should still be at the end
        logger.debug(f"Preserving incomplete reference in buffer: '{trailing_content}'")

        # Find where the trailing content starts in the processed content
        # Look for the pattern at the end of the processed content
        if processed_content.endswith(trailing_content):
            # The trailing content is still there unchanged at the end
            final_processed = processed_content[: -len(trailing_content)]
            remaining_buffer = trailing_content
        else:
            # The trailing content might have been affected by replacements
            # Use a more conservative approach - look for incomplete patterns at the end
            incomplete_match = re.search(r"\[REF:?\d*$", processed_content)
            if incomplete_match:
                final_processed = processed_content[: incomplete_match.start()]
                remaining_buffer = processed_content[incomplete_match.start() :]
            else:
                # Fallback - if we can't find the pattern, just preserve what we detected originally
                final_processed = (
                    processed_content[: -len(trailing_content)]
                    if len(trailing_content) <= len(processed_content)
                    else processed_content
                )
                remaining_buffer = trailing_content

        return final_processed, remaining_buffer

    # No incomplete references after processing, return all processed content
    logger.debug(f"Returning processed content, length: {len(processed_content)}")
    return processed_content, ""


# --- Worker Function for Threaded Query Execution ---
def _execute_query_worker(
    db_name: str,
    query_text: str,
    scope: str,
    token: str,
    db_display_name: str,
    query_index: int,
    total_queries: int,
) -> Dict[str, Any]:
    """
    Worker function executed by each thread to run a single database query.

    Args:
        db_name (str): Internal name of the database
        query_text (str): The search query to execute
        scope (str): Query scope ('metadata' or 'research')
        token (str): OAuth token for API authentication
        db_display_name (str): Human-readable database name for display
        query_index (int): Index of this query in the batch
        total_queries (int): Total number of queries being executed

    Returns:
        Dict[str, Any]: Query execution results and metadata
    """
    logger = logging.getLogger(__name__)
    result = None
    task_exception = None

    from ..initial_setup.process_monitor_setup import get_process_monitor

    process_monitor = get_process_monitor()
    query_stage_name = f"db_query_{db_name}_{query_index}"

    process_monitor.start_stage(query_stage_name)
    process_monitor.add_stage_details(
        query_stage_name,
        db_name=db_name,
        db_display_name=db_display_name,
        query_text=query_text,
        scope=scope,
        query_index=query_index,
        total_queries=total_queries,
    )

    try:
        logger.info(
            f"Thread executing query {query_index + 1}/{total_queries} for database: {db_name}"
        )
        # Assume route_query_sync handles its own LLM calls and logging internally
        # It now returns a tuple: (result, doc_ids, file_links)
        # Pass the process_monitor instance and the specific stage name to the router
        result_tuple = route_query_sync(
            db_name,
            query_text,
            scope,
            token,
            process_monitor=process_monitor,
            query_stage_name=query_stage_name,
            research_statement=query_text,  # Pass research statement for similarity filtering
        )  # ADDED query_stage_name

        # Handle different tuple lengths for backward compatibility
        if len(result_tuple) == 6:
            (
                result,
                doc_ids,
                file_links,
                page_section_refs,
                section_content_map,
                reference_index,
            ) = result_tuple
        elif len(result_tuple) == 5:
            result, doc_ids, file_links, page_section_refs, section_content_map = (
                result_tuple
            )
            reference_index = None
        elif len(result_tuple) == 4:
            result, doc_ids, file_links, page_section_refs = result_tuple
            section_content_map = None
            reference_index = None
        elif len(result_tuple) == 3:
            result, doc_ids, file_links = result_tuple
            page_section_refs = None
            section_content_map = None
            reference_index = None
        elif len(result_tuple) == 2:
            # Old format: (result, doc_ids)
            result, doc_ids = result_tuple
            file_links = None
            page_section_refs = None
            section_content_map = None
            reference_index = None
        else:
            # Unexpected tuple length - handle gracefully
            logger.error(
                f"Unexpected tuple length {len(result_tuple)} from route_query_sync for {db_name}"
            )
            if len(result_tuple) > 0:
                result = result_tuple[0]
            else:
                # Empty tuple case
                if scope == "metadata":
                    result = []
                else:
                    result = {
                        "detailed_research": f"Error: Invalid response format from {db_name}",
                        "status_summary": f"❌ Error: Query failed for '{db_name}'.",
                    }
            doc_ids = None
            file_links = None
            page_section_refs = None
            section_content_map = None
            reference_index = None
        logger.info(f"Thread completed query for database: {db_name}")
        # End the stage for this specific query worker instance successfully
        process_monitor.end_stage(query_stage_name)  # RESTORED end_stage call here

        # Add result details
        if scope == "metadata" and isinstance(result, list):
            process_monitor.add_stage_details(
                query_stage_name,
                result_count=len(result),
                document_names=[
                    item.get("document_name", "Unnamed") for item in result[:10]
                ],
                has_more_documents=len(result) > 10,
            )
        elif scope == "research" and isinstance(result, dict):
            process_monitor.add_stage_details(
                query_stage_name,
                status_summary=result.get("status_summary", "No status provided"),
                has_detailed_research=bool(result.get("detailed_research")),
            )
        # Add document IDs to details if they were returned
        if doc_ids is not None:  # Check if doc_ids is not None (could be empty list)
            process_monitor.add_stage_details(query_stage_name, document_ids=doc_ids)

    except Exception as e:
        task_exception = e
        logger.error(
            f"Thread error executing query for {db_name}: {str(e)}", exc_info=True
        )
        # Ensure stage is ended with error status in case of exception
        process_monitor.end_stage(
            query_stage_name, "error"
        )  # Ensure this is called on error
        process_monitor.add_stage_details(query_stage_name, error=str(e))

    # Return dictionary without token_usage
    return {
        "db_name": db_name,
        "query_text": query_text,
        "scope": scope,
        "db_display_name": db_display_name,
        "query_index": query_index,
        "total_queries": total_queries,
        "result": result,
        "exception": task_exception,
        "file_links": file_links if "file_links" in locals() else None,
        "page_section_refs": (
            page_section_refs if "page_section_refs" in locals() else None
        ),
        "section_content_map": (
            section_content_map if "section_content_map" in locals() else None
        ),
        "reference_index": reference_index if "reference_index" in locals() else None,
    }


# --- Main Synchronous Core Function ---
def _model_generator(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[Callable] = None,
    debug_mode: bool = False,  # Keep debug_mode for legacy debug dict
    db_names: Optional[List[str]] = None,  # List of database names to query
) -> Generator[str, None, None]:
    """
    Core synchronous generator handling the agent workflow.
    """
    from ..initial_setup.process_monitor_setup import (
        enable_monitoring,
        get_process_monitor,
    )

    # Add more logging around the process monitoring setup
    logger = logging.getLogger(__name__)
    logger.info("Setting up process monitoring")

    enable_monitoring(True)
    process_monitor = get_process_monitor()

    # Check if process_monitor is enabled
    logger.info(
        f"Process monitor enabled after enable_monitoring call: {process_monitor.enabled}"
    )

    run_uuid_val = uuid.uuid4()
    logger.info(f"Generated run UUID: {run_uuid_val}")

    process_monitor.set_run_uuid(run_uuid_val)
    logger.info(f"Set run UUID. Current run UUID: {process_monitor.run_uuid}")

    process_monitor.start_monitoring()
    logger.info(f"Started monitoring. Start time: {process_monitor.start_time}")

    # Initialize legacy debug tracking (structure might be inaccurate now)
    debug_data = None
    if debug_mode:
        # This legacy structure is likely inaccurate now and should be reviewed/removed later
        debug_data = {
            "decisions": [],
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0,
                "cost": 0.0,
                "stages": {},
            },
            "start_timestamp": datetime.now().isoformat(),
            "error": None,
            "completed": False,
        }

    from ..agents.agent_clarifier.clarifier import clarify_research_needs
    from ..agents.agent_direct_response.response_from_conversation import (
        response_from_conversation,
    )
    from ..agents.agent_planner.planner import create_database_selection_plan
    from ..agents.agent_router.router import get_routing_decision
    from ..agents.agent_summarizer.summarizer import generate_streaming_summary
    from ..initial_setup.conversation_setup import process_conversation
    from ..initial_setup.logging_config import configure_logging
    from ..initial_setup.oauth_setup import setup_oauth
    from ..initial_setup.ssl_setup import setup_ssl
    from ..initial_setup.db_config import connect_to_db

    # Get settings from config
    SHOW_USAGE_SUMMARY = config.SHOW_USAGE_SUMMARY

    logger = configure_logging()
    db_conn = None
    db_cursor = None

    try:
        logger.info("Initializing model setup (sync core)...")

        process_monitor.start_stage("ssl_setup")
        cert_path = setup_ssl()
        process_monitor.end_stage("ssl_setup")
        process_monitor.add_stage_details("ssl_setup", cert_path=cert_path)

        process_monitor.start_stage("oauth_setup")
        token = setup_oauth()
        process_monitor.end_stage("oauth_setup")
        process_monitor.add_stage_details(
            "oauth_setup", token_length=len(token) if token else 0
        )

        if not conversation:
            logger.warning("No conversation provided.")
            yield "Model initialized, but no conversation provided to process."
            return

        process_monitor.start_stage("conversation_processing")
        try:
            processed_conversation = process_conversation(conversation)
            logger.info(
                f"Conversation processed: {len(processed_conversation['messages'])} messages"
            )
        except ValueError as e:
            logger.warning(f"Invalid conversation format: {str(e)}")
            yield f"Model initialized, but conversation format is invalid: {str(e)}"
            return
        except Exception as e:
            logger.error(f"Error processing conversation: {str(e)}")
            yield f"Error processing conversation: {str(e)}"
            return

        if not processed_conversation["messages"]:
            logger.warning("Processed conversation is empty.")
            yield "Model initialized, but processed conversation is empty."
            return

        process_monitor.end_stage("conversation_processing")
        process_monitor.add_stage_details(
            "conversation_processing",
            message_count=len(processed_conversation["messages"]),
        )

        # Filter available databases based on user selection BEFORE any agent calls
        from ..global_prompts.database_statement import get_available_databases

        available_databases = get_available_databases()
        logger.info(f"Initial available databases: {list(available_databases.keys())}")
        if db_names is not None:
            logger.info(f"db_names filter provided: {db_names}")
            available_databases = {
                k: v for k, v in available_databases.items() if k in db_names
            }
            logger.info(
                f"Filtered available_databases: {list(available_databases.keys())}"
            )
        else:
            logger.info(
                "No db_names filter provided; agents will see all available databases."
            )

        process_monitor.start_stage("router")
        logger.info("Getting routing decision...")
        # TODO: Update get_routing_decision to return (decision, usage_details)
        routing_decision, router_usage_details = get_routing_decision(
            processed_conversation, token, available_databases
        )
        process_monitor.end_stage("router")
        if router_usage_details:
            process_monitor.add_llm_call_details_to_stage(
                "router", router_usage_details
            )
        process_monitor.add_stage_details(
            "router",
            function_name=routing_decision.get("function_name"),
            decision=routing_decision,
        )

        # --- Legacy Debug Block Removed ---

        if routing_decision["function_name"] == "response_from_conversation":
            logger.info("Using direct response path based on routing decision")
            process_monitor.start_stage("direct_response")
            # TODO: Update response_from_conversation to yield usage details at the end
            direct_response_usage_details = None
            stream_iterator = response_from_conversation(
                processed_conversation, token, available_databases
            )
            for chunk in stream_iterator:
                if isinstance(chunk, dict) and "usage_details" in chunk:
                    direct_response_usage_details = chunk["usage_details"]
                else:
                    yield chunk
            process_monitor.end_stage("direct_response")
            if direct_response_usage_details:
                process_monitor.add_llm_call_details_to_stage(
                    "direct_response", direct_response_usage_details
                )
            else:
                logger.warning("No usage details received from direct_response stream.")

            # --- Legacy Debug Block Removed ---

            # End monitoring after successful direct response completion
            logger.info("Direct response completed successfully, ending monitoring")
            process_monitor.end_monitoring()

        elif routing_decision["function_name"] == "research_from_database":
            logger.info("Using research path based on routing decision")
            process_monitor.start_stage("clarifier")
            logger.info("Clarifying research needs...")
            # TODO: Update clarify_research_needs to return (decision, usage_details)
            clarifier_decision, clarifier_usage_details = clarify_research_needs(
                processed_conversation, token, available_databases
            )
            process_monitor.end_stage("clarifier")
            if clarifier_usage_details:
                process_monitor.add_llm_call_details_to_stage(
                    "clarifier", clarifier_usage_details
                )
            process_monitor.add_stage_details(
                "clarifier",
                action=clarifier_decision.get("action"),
                scope=clarifier_decision.get("scope"),
                is_continuation=clarifier_decision.get("is_continuation", False),
                decision=clarifier_decision,
            )

            # --- Legacy Debug Block Removed ---

            if clarifier_decision["action"] == "request_essential_context":
                logger.info("Essential context needed, returning context questions")
                questions = clarifier_decision["output"].strip()
                yield "Before proceeding with research, please clarify:\n\n" + questions

                # End monitoring after successful context request completion
                logger.info("Context request completed successfully, ending monitoring")
                process_monitor.end_monitoring()
            else:
                research_statement = clarifier_decision.get("output", "")
                scope = clarifier_decision.get("scope")
                is_continuation = clarifier_decision.get("is_continuation", False)
                if not scope:
                    logger.error("Scope missing from clarifier decision.")
                    yield "Error: Internal configuration error - missing research scope."
                    # End monitoring after error
                    logger.info("Ending monitoring due to scope error")
                    process_monitor.end_monitoring()
                    return

                logger.info(f"Research scope determined: {scope}")
                # available_databases already filtered earlier in the flow

                # Search apg_catalog for relevant documents based on research statement
                logger.info("Searching apg_catalog for document usage context...")
                apg_catalog_results, apg_catalog_usage = (
                    search_apg_catalog_by_embedding(
                        research_statement,
                        token,
                        top_k=5,
                        available_databases=available_databases,
                    )
                )
                if apg_catalog_usage:
                    process_monitor.add_llm_call_details_to_stage(
                        "clarifier", apg_catalog_usage
                    )

                if apg_catalog_results:
                    logger.info(
                        f"Found {len(apg_catalog_results)} relevant documents in apg_catalog"
                    )
                    # Log the top documents for debugging
                    for i, doc in enumerate(apg_catalog_results[:3]):
                        logger.debug(
                            f"APG Doc {i+1}: {doc.get('document_source', 'N/A')} - {doc.get('document_description', 'N/A')[:100]}..."
                        )
                else:
                    logger.info("No relevant documents found in apg_catalog")

                process_monitor.start_stage("planner")
                logger.info("Creating database selection plan...")
                # TODO: Update create_database_selection_plan to return (plan, usage_details)
                db_selection_plan, planner_usage_details = (
                    create_database_selection_plan(
                        research_statement,
                        token,
                        available_databases,
                        is_continuation,
                        apg_catalog_results,
                    )
                )
                selected_databases = db_selection_plan.get("databases", [])
                logger.info(
                    f"Database selection plan created with {len(selected_databases)} databases: {selected_databases}"
                )
                process_monitor.end_stage("planner")
                if planner_usage_details:
                    process_monitor.add_llm_call_details_to_stage(
                        "planner", planner_usage_details
                    )
                process_monitor.add_stage_details(
                    "planner",
                    database_count=len(selected_databases),
                    selected_databases=selected_databases,
                    decision=db_selection_plan,
                )

                # --- Legacy Debug Block Removed ---

                # Display plan...
                logger.info(
                    f"Final selected_databases to be queried: {selected_databases}"
                )
                if scope == "metadata":
                    yield "# 🔍 File Search Plan\n\n"
                    yield f"## Search Criteria\n{research_statement}\n\n"
                else:
                    yield "# 📋 Research Plan\n\n"
                    yield f"## Research Statement\n{research_statement}\n\n"
                selected_db_display_names = [
                    available_databases.get(db_name, {}).get("name", db_name)
                    for db_name in selected_databases
                ]
                if selected_db_display_names:
                    if len(selected_db_display_names) == 1:
                        names_str = selected_db_display_names[0]
                    elif len(selected_db_display_names) == 2:
                        names_str = f"{selected_db_display_names[0]} and {selected_db_display_names[1]}"
                    else:
                        names_str = (
                            ", ".join(selected_db_display_names[:-1])
                            + f", and {selected_db_display_names[-1]}"
                        )
                    yield f"Searching the following databases: {names_str}.\n\n---\n"
                else:
                    yield "No databases selected for search.\n\n---\n"
                logger.info("Displayed database selection plan.")

                if not selected_databases:
                    logger.warning(
                        "Database selection plan is empty, skipping database search."
                    )
                else:
                    logger.info(
                        f"Starting {len(selected_databases)} database queries concurrently..."
                    )
                    aggregated_detailed_research = {}
                    metadata_results_by_db: Dict[str, List[Dict[str, Any]]] = {}
                    total_metadata_items = 0
                    all_file_links = []  # Collect all file links from all databases
                    all_page_section_refs = (
                        {}
                    )  # Collect all page/section refs by database
                    all_section_content_maps = (
                        {}
                    )  # Collect all section content maps by database
                    all_reference_indices = (
                        {}
                    )  # Collect all reference indices by database
                    futures = []

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for i, db_name in enumerate(selected_databases):
                            query_text = research_statement
                            db_display_name = available_databases.get(db_name, {}).get(
                                "name", db_name
                            )
                            if i > 0:
                                time.sleep(1)
                            future = executor.submit(
                                _execute_query_worker,
                                db_name,
                                query_text,
                                scope,
                                token,
                                db_display_name,
                                i,
                                len(selected_databases),
                            )
                            futures.append(future)
                        logger.info(f"Submitted {len(futures)} queries to thread pool.")

                        for future in concurrent.futures.as_completed(futures):
                            try:
                                result_data = future.result()
                            except Exception as exc:
                                logger.error(
                                    f"Error retrieving result from future: {exc}",
                                    exc_info=True,
                                )
                                continue
                            db_name = result_data["db_name"]
                            db_display_name = result_data["db_display_name"]
                            task_exception = result_data["exception"]
                            result = result_data["result"]
                            scope = result_data["scope"]
                            file_links = result_data.get("file_links", None)
                            page_section_refs = result_data.get(
                                "page_section_refs", None
                            )
                            section_content_map = result_data.get(
                                "section_content_map", None
                            )
                            reference_index = result_data.get("reference_index", None)

                            # --- Legacy Debug Block Removed ---

                            # Aggregate results and yield status...
                            status_summary = "❓ Unknown status (Processing error)."
                            if task_exception:
                                status_summary = f"❌ Error: {str(task_exception)}"
                                if scope == "research":
                                    aggregated_detailed_research[db_name] = (
                                        f"Error: {str(task_exception)}"
                                    )
                                elif scope == "metadata":
                                    metadata_results_by_db.setdefault(
                                        db_name, []
                                    ).append({"error": str(task_exception)})
                            elif result is not None:
                                if scope == "research":
                                    if (
                                        isinstance(result, dict)
                                        and "detailed_research" in result
                                        and "status_summary" in result
                                    ):
                                        status_summary = result["status_summary"]
                                        aggregated_detailed_research[db_name] = result[
                                            "detailed_research"
                                        ]
                                    else:
                                        status_summary = (
                                            "❌ Error: Unexpected result format."
                                        )
                                        aggregated_detailed_research[db_name] = (
                                            f"Error: {str(result)[:200]}..."
                                        )
                                elif scope == "metadata":
                                    if isinstance(result, list):
                                        metadata_results_by_db.setdefault(
                                            db_name, []
                                        ).extend(result)
                                        total_metadata_items += len(result)
                                        status_summary = (
                                            f"✅ Found {len(result)} items."
                                        )
                                    else:
                                        status_summary = (
                                            "❌ Error: Unexpected result format."
                                        )
                                        metadata_results_by_db.setdefault(
                                            db_name, []
                                        ).append({"error": "Unexpected format"})

                            # Collect file links if available
                            if file_links:
                                all_file_links.extend(file_links)

                            # Collect page/section data if available
                            if page_section_refs:
                                all_page_section_refs[db_name] = page_section_refs
                            if section_content_map:
                                all_section_content_maps[db_name] = section_content_map

                            # Collect reference indices if available
                            if reference_index:
                                all_reference_indices[db_name] = reference_index

                            status_block = f"**Database:** {db_display_name}\n{status_summary}\n---\n"
                            yield status_block

                    logger.info("All concurrent database queries completed processing.")
                    # --- Legacy Debug Block Removed ---
                    if scope == "metadata":
                        for db_name in selected_databases:
                            metadata_results_by_db.setdefault(db_name, [])

                if scope == "research":
                    if aggregated_detailed_research:
                        yield "\n\n---\n"
                        yield "\n\n## 📊 Research Summary\n"
                        process_monitor.start_stage("summary")
                        process_monitor.add_stage_details(
                            "summary",
                            scope=scope,
                            num_results=len(aggregated_detailed_research),
                            sources=list(aggregated_detailed_research.keys()),
                        )

                        # Process both old format (reference indices) and new format (structured research)
                        master_reference_index = {}
                        structured_research_with_refs = {}
                        ref_counter = 1

                        # First, process new structured research format and assign REF numbers
                        for db_name, ref_index in all_reference_indices.items():
                            if isinstance(ref_index, dict) and any(
                                isinstance(doc_data, dict)
                                and any(
                                    isinstance(page_data, dict)
                                    and "research_content" in page_data
                                    for page_data in doc_data.values()
                                    if isinstance(page_data, dict)
                                )
                                for doc_data in ref_index.values()
                                if isinstance(doc_data, dict)
                            ):
                                # New structured format: {doc_name: {page_x: {research_content, file_link, page_number}}}
                                db_research_with_refs: Dict[str, str] = {}

                                # Sort by document name, then by page number for consistent REF ordering
                                for doc_name in sorted(ref_index.keys()):
                                    doc_data = ref_index[doc_name]
                                    db_research_with_refs[doc_name] = {}

                                    # Sort pages by page number
                                    sorted_pages = sorted(
                                        doc_data.items(),
                                        key=lambda x: (
                                            x[1].get("page_number", 0)
                                            if isinstance(x[1], dict)
                                            else 0
                                        ),
                                    )

                                    for page_key, page_data in sorted_pages:
                                        if (
                                            isinstance(page_data, dict)
                                            and "research_content" in page_data
                                        ):
                                            page_number = page_data.get(
                                                "page_number", 0
                                            )
                                            research_content = page_data.get(
                                                "research_content", ""
                                            )
                                            file_link = page_data.get("file_link", "")
                                            file_name = page_data.get("file_name", "")

                                            # Assign REF number
                                            ref_id = str(ref_counter)
                                            ref_tag = f"REF:{ref_id}"

                                            # Add REF tag to research content
                                            research_with_ref = (
                                                f"{research_content} [{ref_tag}]"
                                            )

                                            # Store in structured format
                                            db_research_with_refs[doc_name][
                                                page_key
                                            ] = {
                                                "research_content": research_with_ref,
                                                "file_link": file_link,
                                                "file_name": file_name,
                                                "page_number": page_number,
                                                "ref_id": ref_id,
                                            }

                                            # Build master reference index for href generation
                                            master_reference_index[ref_id] = {
                                                "doc_name": doc_name,
                                                "file_link": file_link,
                                                "file_name": file_name,
                                                "page": page_number,
                                                "highlight_text": "",  # Empty as requested
                                                "source_db": db_name,
                                            }

                                            ref_counter += 1

                                # Store the completed db_research_with_refs for this database
                                structured_research_with_refs[db_name] = (
                                    db_research_with_refs
                                )

                            else:
                                # Old format: simple reference index with ID mappings
                                for old_ref_id, ref_data in ref_index.items():
                                    new_ref_id = str(ref_counter)
                                    master_reference_index[new_ref_id] = {
                                        **ref_data,
                                        "source_db": db_name,
                                    }
                                    # Update the research text with new reference IDs
                                    if db_name in aggregated_detailed_research:
                                        aggregated_detailed_research[
                                            db_name
                                        ] = aggregated_detailed_research[
                                            db_name
                                        ].replace(
                                            f"[REF:{old_ref_id}]", f"[REF:{new_ref_id}]"
                                        )
                                    ref_counter += 1

                        # Convert structured research to combined research text for summarizer
                        if (
                            structured_research_with_refs
                        ):  # Only process if we have structured research
                            for (
                                db_name,
                                db_research,
                            ) in structured_research_with_refs.items():
                                combined_research = (
                                    f"# {db_name.upper()} Research Results\n\n"
                                )

                                for doc_name, doc_data in db_research.items():
                                    # Use display name if available, otherwise use doc_name
                                    display_name = doc_data.get(
                                        "_display_name", doc_name
                                    )
                                    combined_research += f"## {display_name}\n\n"

                                    for page_key, page_data in doc_data.items():
                                        # Skip the _display_name metadata field
                                        if page_key == "_display_name":
                                            continue
                                        page_number = page_data.get("page_number", 0)
                                        research_content = page_data.get(
                                            "research_content", ""
                                        )

                                        combined_research += (
                                            f"### Page {page_number}\n\n"
                                        )
                                        combined_research += f"{research_content}\n\n"

                                    combined_research += "---\n\n"

                                # Update aggregated research with the combined version
                                aggregated_detailed_research[db_name] = (
                                    combined_research.strip()
                                )

                        # --- Legacy Debug Block Removed ---
                        try:
                            logger.info("Calling generate_streaming_summary")
                            # TODO: Update generate_streaming_summary to yield usage details
                            summary_usage_details = None
                            summary_stream = generate_streaming_summary(
                                aggregated_detailed_research,
                                scope,
                                token,
                                available_databases,
                                research_statement=research_statement,
                                reference_index=master_reference_index,
                            )

                            # Buffer for handling reference replacement
                            buffer = ""

                            for chunk in summary_stream:
                                if isinstance(chunk, dict) and "usage_details" in chunk:
                                    summary_usage_details = chunk["usage_details"]
                                    # Process any remaining buffer content
                                    if buffer:
                                        yield from _process_final_references(
                                            buffer, master_reference_index
                                        )
                                else:
                                    # Add chunk to buffer
                                    buffer += chunk
                                    # Process buffer for reference replacements
                                    processed, buffer = _process_reference_buffer(
                                        buffer, master_reference_index
                                    )
                                    if processed:
                                        yield processed
                            process_monitor.end_stage("summary")
                            if summary_usage_details:
                                process_monitor.add_llm_call_details_to_stage(
                                    "summary", summary_usage_details
                                )
                            else:
                                logger.warning(
                                    "No usage details received from summary stream."
                                )
                        except Exception as summary_exc:
                            logger.error(
                                f"Error during summarization: {summary_exc}",
                                exc_info=True,
                            )
                            yield f"\n\n**Error during final summarization:** {str(summary_exc)}"
                            process_monitor.end_stage("summary", "error")
                            process_monitor.add_stage_details(
                                "summary", error=str(summary_exc)
                            )
                        # --- Legacy Debug Block Removed ---

                        logger.info(f"Completed process for scope '{scope}'")
                elif scope == "metadata":
                    # Metadata display logic...
                    seen_documents: Dict[str, Dict[str, Any]] = {}
                    unique_item_count = 0
                    for db_name, items_list in metadata_results_by_db.items():
                        seen_documents.setdefault(db_name, set())
                        for item in items_list:
                            if isinstance(item, dict) and "error" in item:
                                unique_item_count += 1
                            else:
                                doc_name = item.get("document_name", "Unknown")
                                if doc_name not in seen_documents[db_name]:
                                    seen_documents[db_name].add(doc_name)
                                    unique_item_count += 1
                    yield f"\n\nCompleted metadata search across {len(selected_databases)} databases. Found {unique_item_count} unique relevant items:\n"
                    seen_documents: Dict[str, Dict[str, Any]] = {}
                    for db_name, items_list in metadata_results_by_db.items():
                        db_display_name = available_databases.get(db_name, {}).get(
                            "name", db_name
                        )
                        yield f"\n**{db_display_name}:**\n"
                        if items_list:
                            seen_documents.setdefault(db_name, set())
                            displayed_items = 0
                            for item in items_list:
                                if isinstance(item, dict) and "error" in item:
                                    yield f"- Error: {item['error']}\n"
                                    displayed_items += 1
                                else:
                                    doc_name = item.get("document_name", "Unknown")
                                if doc_name not in seen_documents[db_name]:
                                    seen_documents[db_name].add(doc_name)
                                    doc_desc = item.get(
                                        "document_description", "No description"
                                    )
                                    yield f"- **{doc_name}:** {doc_desc}\n"
                                    displayed_items += 1
                            if displayed_items == 0:
                                yield "- No unique items found.\n"
                        else:
                            yield "- No relevant items found.\n"
                    logger.info(
                        f"Completed process for scope '{scope}', returning {total_metadata_items} items internally."
                    )

                # --- Legacy Debug Block Removed ---

                # End monitoring after successful research completion
                logger.info("Research completed successfully, ending monitoring")
                process_monitor.end_monitoring()

        else:
            logger.error(
                f"Unknown routing function: {routing_decision['function_name']}"
            )
            yield "Error: Unable to process query due to internal routing error."
            # End monitoring after routing error
            logger.info("Ending monitoring due to routing error")
            process_monitor.end_monitoring()

    except Exception as e:
        error_msg = f"Critical error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if process_monitor.enabled and (
            not hasattr(process_monitor, "end_time") or not process_monitor.end_time
        ):
            process_monitor.end_monitoring()
        process_monitor.add_stage_details("_global", error=error_msg)
        # --- Legacy Debug Block Removed ---
        yield f"**Error:** {error_msg}"

    finally:
        if process_monitor.enabled and (
            not hasattr(process_monitor, "end_time") or not process_monitor.end_time
        ):
            logger.warning(
                "Process monitoring end_time was not set before finally block, setting now."
            )
            process_monitor.end_monitoring()

        # --- Database Logging Call ---
        if process_monitor.enabled:
            try:
                # Use the imported connect_to_db function
                logger.info(
                    f"Attempting to log process monitor data to database for run {process_monitor.run_uuid}"
                )
                logger.info(f"Total stages to log: {len(process_monitor.stages)}")
                # Show ENVIRONMENT value
                logger.info(f"Using environment: {config.ENVIRONMENT}")

                db_conn = connect_to_db()
                if db_conn:
                    logger.info("Database connection established")
                    # Check if table exists
                    with db_conn.cursor() as check_cursor:
                        check_cursor.execute(
                            """
                            SELECT EXISTS (
                               SELECT FROM information_schema.tables 
                               WHERE table_schema = 'public'
                               AND table_name = 'process_monitor_logs'
                            );
                        """
                        )
                        table_exists = check_cursor.fetchone()[0]
                        logger.info(
                            f"process_monitor_logs table exists: {table_exists}"
                        )

                    # Try to log to the database
                    with db_conn.cursor() as db_cursor:
                        process_monitor.log_to_database(db_cursor)
                        db_conn.commit()  # Commit transaction
                    logger.info("Process monitor data logged to database.")
                else:
                    logger.error(
                        f"Failed to get database connection for logging process monitor data. Environment: {config.ENVIRONMENT}"
                    )
            except Exception as log_exc:
                logger.error(
                    f"Failed to log process monitor data to database: {log_exc}",
                    exc_info=True,
                )
                # Rollback if connection object available
                if db_conn:
                    try:
                        db_conn.rollback()
                    except Exception as rb_exc:
                        logger.error(f"Error during DB rollback: {rb_exc}")
            finally:
                # Close connection if obtained
                if db_conn:
                    try:
                        db_conn.close()
                    except Exception as close_exc:
                        logger.error(f"Error closing DB connection: {close_exc}")

        # --- Legacy Debug: Final Yield ---
        if debug_mode and debug_data is not None and not debug_data.get("error"):
            # This legacy data is likely inaccurate now
            debug_data["completed"] = True
            if "end_timestamp" not in debug_data:
                # Simplified calculation based on potentially incomplete stage data
                final_agent_usage = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                }
                # This loop might fail if stages structure changed
                try:
                    for stage_usage in (
                        debug_data.get("tokens", {}).get("stages", {}).values()
                    ):
                        final_agent_usage["prompt_tokens"] += stage_usage.get(
                            "prompt", 0
                        )
                        final_agent_usage["completion_tokens"] += stage_usage.get(
                            "completion", 0
                        )
                        final_agent_usage["total_tokens"] += stage_usage.get("total", 0)
                        final_agent_usage["cost"] += stage_usage.get("cost", 0.0)
                    debug_data["tokens"]["prompt"] = final_agent_usage["prompt_tokens"]
                    debug_data["tokens"]["completion"] = final_agent_usage[
                        "completion_tokens"
                    ]
                    debug_data["tokens"]["total"] = final_agent_usage["total_tokens"]
                    debug_data["cost"] = final_agent_usage["cost"]
                except Exception:
                    logger.warning("Could not calculate legacy debug token totals.")
                debug_data["end_timestamp"] = datetime.now().isoformat()
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"
        # --- End Legacy Debug ---


# --- Synchronous Wrapper Function ---
def model(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[Callable] = None,
    debug_mode: bool = False,  # Keep debug_mode for legacy dict
    db_names: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """
    Synchronous wrapper for the model generator.
    """
    logger = logging.getLogger(__name__)
    logger.info("Entering synchronous model wrapper.")
    try:
        sync_gen = _model_generator(conversation, html_callback, debug_mode, db_names)
        for chunk in sync_gen:
            yield chunk
        logger.info("Synchronous generator completed.")
    except Exception as e:
        error_msg = f"Error during synchronous model execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield f"**Error:** {error_msg}"


# --- Async Wrapper for FastAPI ---
async def process_request_async(
    conversation: List[Dict[str, str]],
    stream: bool = False,
    db_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Async wrapper for FastAPI that processes a conversation request.

    Args:
        conversation: List of message dictionaries with 'role' and 'content'
        stream: Whether to enable streaming (not implemented in this wrapper)

    Returns:
        Dictionary with response data including:
        - response: The complete response text
        - agent_used: Which agent handled the request
        - processing_time_ms: Processing time in milliseconds
        - token_usage: Token usage statistics
        - run_uuid: Unique run identifier
    """
    import asyncio
    import time

    logger = logging.getLogger(__name__)
    logger.info(f"Processing async request with {len(conversation)} messages")

    start_time = time.time()

    def run_sync_model():
        """Run the synchronous model in a thread"""
        try:
            # Convert conversation to expected format
            conversation_dict = {"messages": conversation}

            # Collect all chunks from the generator
            response_chunks = []
            agent_used = None
            run_uuid = None
            token_usage = None

            # Run the existing synchronous model
            for chunk in model(conversation_dict, debug_mode=False, db_names=db_names):
                if isinstance(chunk, str):
                    response_chunks.append(chunk)
                elif isinstance(chunk, dict):
                    # This might be debug info or final summary
                    if "agent_used" in chunk:
                        agent_used = chunk.get("agent_used")
                    if "run_uuid" in chunk:
                        run_uuid = chunk.get("run_uuid")
                    if "token_usage" in chunk:
                        token_usage = chunk.get("token_usage")

            # Join all response chunks
            full_response = "".join(response_chunks)

            return {
                "response": full_response,
                "agent_used": agent_used,
                "run_uuid": str(run_uuid) if run_uuid else None,
                "token_usage": token_usage,
            }

        except Exception as e:
            logger.error(f"Error in sync model execution: {str(e)}", exc_info=True)
            return {
                "response": f"Error processing request: {str(e)}",
                "agent_used": None,
                "run_uuid": None,
                "token_usage": None,
            }

    # Run the synchronous code in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_sync_model)

    # Add processing time
    processing_time_ms = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time_ms

    logger.info(f"Async request completed in {processing_time_ms}ms")

    return result


# --- Helper Function (Remains Synchronous) ---
def format_remaining_queries(remaining_queries: List[Dict[str, Any]]) -> str:
    """Format remaining queries for display to the user."""
    if not remaining_queries:
        return ""
    available_databases = get_available_databases()
    message = "## ⏸️ Remaining Queries\n\n"
    message += "The following database queries were not processed:\n\n"
    for i, query in enumerate(remaining_queries, 1):
        db_name = query["database"]
        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
        message += f"**{i}.** {db_display_name}: {query['query']}\n\n"
    message += "\nPlease let me know if you would like to continue with these remaining database queries in a new search."
    return message
