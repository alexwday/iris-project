# services/src/agents/database_subagents/semantic_search_v2/subagent.py
"""
Semantic Search V2 Subagent

Handles queries to the new iris_semantic_search table with enhanced retrieval logic:
- Top-k semantic search with embedding similarity
- Section expansion for sections ≤6 pages
- Gap filling for missing sections
- REF tag integration with dual page reference system
- Support for both single and multi-document queries

Functions:
    query_database_sync: Main entry point for database queries
"""

import json
import logging
import os
import time
import traceback
import yaml
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from collections import defaultdict

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

from ....initial_setup.env_config import config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm

# Type definitions
MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
FileLink = Dict[str, str]
PageSectionRefs = Dict[int, List[int]]
SectionContentMap = Dict[str, str]
ReferenceIndex = Dict[str, Dict[str, Any]]
SubagentResult = Tuple[
    DatabaseResponse,
    Optional[List[str]],
    Optional[List[FileLink]],
    Optional[PageSectionRefs],
    Optional[SectionContentMap],
    Optional[ReferenceIndex],
]
LlmUsageDetails = Optional[Dict[str, Any]]

logger = logging.getLogger(__name__)

# Configuration Constants
TARGET_TABLE = "iris_semantic_search"
EMBEDDING_MODEL_CAPABILITY = "embedding"
RELEVANCE_MODEL_CAPABILITY = "small"
RESPONSE_MODEL_CAPABILITY = "small"  # Use small model for synthesis to save costs
EMBEDDING_DIMENSIONS = 2000
INITIAL_K = 20
SECTION_EXPANSION_MAX_PAGES = 6
GAP_FILL_MAX_SECTIONS = 2
MAX_RESPONSE_TOKENS = 32768
RESPONSE_TEMPERATURE = 0.7


def load_content_synthesis_config():
    """Load content synthesis configuration from YAML file."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "content_synthesis_prompt.yaml")
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)
        
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception("No system_prompt found in YAML configuration")
        
        return yaml_config
    
    except Exception as e:
        logger.error(f"Failed to load content synthesis YAML config: {str(e)}")
        raise


def get_content_synthesis_prompt(query: str, formatted_context: str) -> str:
    """Generate prompt for content synthesis."""
    yaml_config = load_content_synthesis_config()
    system_prompt = yaml_config.get("system_prompt", "")
    
    system_prompt = system_prompt.replace("{{query}}", query)
    system_prompt = system_prompt.replace("{{formatted_context}}", formatted_context)
    
    return system_prompt


def get_synthesis_tool_schema() -> Dict[str, Any]:
    """Get the synthesis tool schema from YAML configuration."""
    yaml_config = load_content_synthesis_config()
    tools = yaml_config.get("tools", [])
    
    if not tools:
        raise Exception("No tools found in YAML configuration")
    
    return tools[0]


def _generate_query_embedding(
    query: str, token: Optional[str] = None
) -> Tuple[Optional[List[float]], LlmUsageDetails]:
    """Generate embedding for the query string."""
    logger.info(f"Generating embedding for query: '{query}'...")
    usage_details: LlmUsageDetails = None
    
    try:
        model_config = config.get_model_config(EMBEDDING_MODEL_CAPABILITY)
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        completion_cost = model_config.get("completion_token_cost", 0.0)
        
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": prompt_cost,
            "completion_token_cost": completion_cost,
            "model": model_name,
            "input": [query],
            "dimensions": EMBEDDING_DIMENSIONS,
            "database_name": "semantic_search_v2",
            "is_embedding": True,
        }
        
        result = call_llm(**call_params)
        
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Embedding usage details: {usage_details}")
        else:
            response = result
        
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
            logger.error("No embedding data received from API.")
            return None, usage_details
    
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}", exc_info=True)
        return None, usage_details


def _perform_vector_search(
    cursor, 
    query_embedding: List[float], 
    k: int, 
    doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Perform vector search on iris_semantic_search table."""
    doc_filter = f" filtering for document_id='{doc_id}'" if doc_id else ""
    logger.info(f"Performing vector search (k={k}){doc_filter}")
    
    if query_embedding is None:
        logger.error("Cannot perform vector search without embedding.")
        return []
    
    try:
        sql = f"""
            SELECT
                id,
                document_id,
                filename,
                filepath,
                source_filename,
                chapter_number,
                chapter_name,
                chapter_summary,
                chapter_page_count,
                section_number,
                section_summary,
                section_start_page,
                section_end_page,
                section_page_count,
                section_start_reference,
                section_end_reference,
                chunk_number,
                chunk_content,
                chunk_start_page,
                chunk_end_page,
                chunk_start_reference,
                chunk_end_reference,
                1 - (embedding <=> %s::vector) AS vector_score
            FROM {TARGET_TABLE}
            WHERE 1=1
            {" AND document_id = %s" if doc_id else ""}
            ORDER BY vector_score DESC
            LIMIT %s;
        """
        
        params = [query_embedding]
        if doc_id:
            params.append(doc_id)
        params.append(k)
        
        cursor.execute(sql, params)
        results_raw = cursor.fetchall()
        logger.info(f"Found {len(results_raw)} results via vector search.")
        
        results = []
        for i, row in enumerate(results_raw):
            record = dict(row)
            record["rank"] = i + 1
            results.append(record)
        
        return results
    
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return []


def _filter_by_relevance(
    query: str,
    chunks: List[Dict[str, Any]],
    token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], LlmUsageDetails]:
    """Use LLM to filter chunks by relevance based on summaries."""
    logger.info(f"Filtering {len(chunks)} chunks by relevance")
    usage_details: LlmUsageDetails = None
    
    if not chunks:
        return [], usage_details
    
    # Debug: Log sample chunk data
    if chunks:
        sample_chunk = chunks[0]
        logger.debug(f"Sample chunk keys: {list(sample_chunk.keys())}")
        logger.debug(f"Sample chapter_summary: {sample_chunk.get('chapter_summary', 'MISSING')[:200] if sample_chunk.get('chapter_summary') else 'EMPTY'}")
        logger.debug(f"Sample section_summary: {sample_chunk.get('section_summary', 'MISSING')[:200] if sample_chunk.get('section_summary') else 'EMPTY'}")
    
    # Prepare summaries for LLM evaluation with simple 1-based numbering
    summaries_list = []
    chunk_by_number = {}  # Map number to actual chunk
    empty_summary_count = 0
    
    for i, chunk in enumerate(chunks, 1):  # Start from 1 for clearer numbering
        chunk_id = chunk.get("id")
        chapter_summary = chunk.get("chapter_summary", "")
        section_summary = chunk.get("section_summary", "")
        
        # Debug: Check for empty summaries
        if not chapter_summary and not section_summary:
            empty_summary_count += 1
            logger.debug(f"Chunk {chunk_id} has empty summaries")
            continue  # Skip chunks with no summaries
        
        chunk_by_number[i] = chunk
        summaries_list.append(f"{i}. Chapter: {chapter_summary}\n   Section: {section_summary}")
    
    logger.info(f"Prepared {len(summaries_list)} summaries for evaluation, {empty_summary_count} chunks had empty summaries")
    
    if not summaries_list:
        logger.warning("No valid summaries found for relevance check.")
        return chunks, usage_details
    
    # Create the prompt with numbered summaries
    prompt_summaries = "\n\n".join(summaries_list)
    
    # Log what we're sending for debugging
    logger.info(f"Query for relevance check: '{query}'")
    logger.debug(f"First 3 summaries being evaluated:\n{prompt_summaries[:1000]}")
    
    # Log full prompt at INFO level for debugging aggressive filtering
    if len(summaries_list) <= 20:
        logger.info(f"All {len(summaries_list)} summaries being sent for evaluation:")
        for summary in summaries_list[:5]:  # Show first 5 at INFO level
            logger.info(f"  {summary[:200]}...")  # First 200 chars of each
        if len(summaries_list) > 5:
            logger.info(f"  ... and {len(summaries_list) - 5} more summaries")
    
    system_message = """You are evaluating text summaries for relevance to a user query.
Your goal is to KEEP as many summaries as possible that might help answer the query.
Only remove summaries that are COMPLETELY OFF-TOPIC with ZERO relevance.

Guidelines:
- KEEP summaries that mention ANY concept, term, or topic from the query
- KEEP summaries that provide context or background information
- KEEP summaries that might be tangentially related
- ONLY REMOVE summaries about completely unrelated topics

Be VERY conservative - when in doubt, KEEP the summary.
Respond with a JSON ARRAY of numbers to REMOVE (only the completely irrelevant ones)."""
    
    user_message = f"""Query: "{query}"

Summaries to evaluate:
{prompt_summaries}

Return a JSON ARRAY of summary numbers that are COMPLETELY IRRELEVANT and should be removed.
- If a summary has ANY possible relevance, do NOT include it in the removal list
- Return an empty array [] if all summaries might be relevant
- Example: [3, 15] means ONLY summaries 3 and 15 are completely off-topic

IMPORTANT: Be conservative - only remove if you're absolutely certain it's irrelevant."""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    
    try:
        model_config = config.get_model_config(RELEVANCE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": messages,
            "temperature": 0.3,  # Slightly higher for more inclusive relevance scoring
            # Removed response_format to allow array responses
            "database_name": "semantic_search_v2",
            "stream": False,
        }
        
        result = call_llm(**call_params)
        
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
        else:
            response = result
        
        if response and hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
            logger.debug(f"LLM relevance response: {content[:500] if content else 'EMPTY'}")
            
            # Parse the array of numbers to remove
            numbers_to_remove = json.loads(content)
            logger.debug(f"Numbers to remove (irrelevant): {numbers_to_remove}")
            
            # Handle both array and dict formats for backward compatibility
            if isinstance(numbers_to_remove, dict):
                logger.warning("LLM returned dict format instead of array - attempting to extract irrelevant items")
                # Try to extract keys where value is 0 (irrelevant)
                remove_list = []
                for key, value in numbers_to_remove.items():
                    if value == 0:  # 0 means irrelevant in the old format
                        try:
                            # Convert key to int if it's a number
                            num = int(key)
                            remove_list.append(num)
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse key '{key}' as number")
                numbers_to_remove = remove_list
                logger.info(f"Extracted {len(remove_list)} items to remove from dict format")
            elif not isinstance(numbers_to_remove, list):
                logger.error(f"Expected array but got: {type(numbers_to_remove)}")
                logger.warning("Returning all chunks without filtering")
                return chunks, usage_details
            
            # Convert to set for efficient lookup
            remove_set = set(numbers_to_remove)
            logger.info(f"LLM marked {len(remove_set)} summaries as completely irrelevant for removal: {sorted(remove_set)[:10]}{'...' if len(remove_set) > 10 else ''}")
            
            # Keep chunks that are NOT in the remove list
            filtered_chunks = []
            removed_summaries = []
            for number, chunk in chunk_by_number.items():
                if number not in remove_set:
                    filtered_chunks.append(chunk)
                    logger.debug(f"Keeping chunk {number} (ID: {chunk.get('id')}) as relevant")
                else:
                    logger.debug(f"Removing chunk {number} (ID: {chunk.get('id')}) as irrelevant")
                    # Log what's being removed at INFO level if aggressive filtering
                    if len(remove_set) > len(chunk_by_number) * 0.7:  # If removing >70%
                        chapter_summary = chunk.get("chapter_summary", "")[:100]
                        section_summary = chunk.get("section_summary", "")[:100]
                        removed_summaries.append(f"  #{number}: Ch: {chapter_summary}... | Sec: {section_summary}...")
            
            logger.info(f"Kept {len(filtered_chunks)} relevant chunks out of {len(chunk_by_number)}")
            
            # If aggressive filtering, show what was removed
            if len(removed_summaries) > 0 and len(removed_summaries) > len(chunk_by_number) * 0.5:
                logger.warning(f"Aggressive filtering detected! Removed {len(removed_summaries)} chunks:")
                for summary in removed_summaries[:3]:  # Show first 3 removed
                    logger.warning(summary)
                if len(removed_summaries) > 3:
                    logger.warning(f"  ... and {len(removed_summaries) - 3} more")
            
            # If all chunks were filtered out, log a warning
            if len(filtered_chunks) == 0 and len(chunk_by_number) > 0:
                logger.warning(f"All {len(chunk_by_number)} chunks were filtered out as irrelevant!")
                logger.warning(f"Query was: {query}")
                logger.warning("This may indicate overly strict filtering or a mismatch with the content")
                # Consider returning top chunks as fallback
                # filtered_chunks = list(chunk_by_number.values())[:5]
                # logger.warning(f"Returning top 5 chunks as fallback")
            
            return filtered_chunks, usage_details
        
    except Exception as e:
        logger.error(f"Relevance filtering failed: {e}", exc_info=True)
    
    return chunks, usage_details


def _expand_to_full_sections(
    cursor,
    chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Expand chunks to full sections if section_page_count <= 6."""
    logger.info(f"Expanding {len(chunks)} chunks to full sections where applicable")
    
    expanded_results = []
    processed_sections = set()
    
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        chapter_num = chunk.get("chapter_number")
        section_num = chunk.get("section_number")
        section_page_count = chunk.get("section_page_count", 0)
        
        section_key = (doc_id, chapter_num, section_num)
        
        # Skip if already processed this section
        if section_key in processed_sections:
            continue
        
        processed_sections.add(section_key)
        
        # If section is small enough, expand to full section
        if section_page_count <= SECTION_EXPANSION_MAX_PAGES:
            try:
                sql = f"""
                    SELECT * FROM {TARGET_TABLE}
                    WHERE document_id = %s 
                    AND chapter_number = %s 
                    AND section_number = %s
                    ORDER BY chunk_number;
                """
                cursor.execute(sql, (doc_id, chapter_num, section_num))
                section_chunks = cursor.fetchall()
                
                if section_chunks:
                    logger.debug(f"Expanded section {section_key} to {len(section_chunks)} chunks")
                    for section_chunk in section_chunks:
                        expanded_results.append(dict(section_chunk))
                else:
                    # If expansion fails, keep original chunk
                    expanded_results.append(chunk)
            
            except Exception as e:
                logger.error(f"Failed to expand section {section_key}: {e}")
                expanded_results.append(chunk)
        else:
            # Section too large, keep only the original chunk
            expanded_results.append(chunk)
    
    logger.info(f"Expanded to {len(expanded_results)} total chunks")
    return expanded_results


def _fill_section_gaps(
    cursor,
    chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Fill gaps of 1-2 sections between existing sections."""
    logger.info("Filling section gaps")
    
    # Group chunks by document and chapter
    doc_chapter_sections = defaultdict(set)
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        chapter_num = chunk.get("chapter_number")
        section_num = chunk.get("section_number")
        
        if doc_id and chapter_num is not None and section_num is not None:
            doc_chapter_sections[(doc_id, chapter_num)].add(section_num)
    
    # Find and fill gaps
    sections_to_add = []
    for (doc_id, chapter_num), section_nums in doc_chapter_sections.items():
        sorted_sections = sorted(section_nums)
        
        for i in range(len(sorted_sections) - 1):
            gap = sorted_sections[i + 1] - sorted_sections[i] - 1
            
            if 0 < gap <= GAP_FILL_MAX_SECTIONS:
                # Fill the gap
                for missing_section in range(sorted_sections[i] + 1, sorted_sections[i + 1]):
                    sections_to_add.append((doc_id, chapter_num, missing_section))
                    logger.debug(f"Gap filling: Adding section {missing_section} in chapter {chapter_num}")
    
    # Fetch gap-filled sections
    gap_filled_chunks = []
    for doc_id, chapter_num, section_num in sections_to_add:
        try:
            sql = f"""
                SELECT * FROM {TARGET_TABLE}
                WHERE document_id = %s 
                AND chapter_number = %s 
                AND section_number = %s
                ORDER BY chunk_number;
            """
            cursor.execute(sql, (doc_id, chapter_num, section_num))
            section_chunks = cursor.fetchall()
            
            for chunk in section_chunks:
                gap_filled_chunks.append(dict(chunk))
        
        except Exception as e:
            logger.error(f"Failed to fetch gap section {section_num}: {e}")
    
    # Combine original and gap-filled chunks
    all_chunks = chunks + gap_filled_chunks
    logger.info(f"Added {len(gap_filled_chunks)} chunks from gap filling")
    
    return all_chunks


def _format_context_with_blocks(
    chunks: List[Dict[str, Any]]
) -> str:
    """Format chunks into hierarchical chapter/section/chunk blocks."""
    logger.info(f"Formatting {len(chunks)} chunks into context blocks")
    
    # Group by document, then chapter
    doc_structure = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        chapter_num = chunk.get("chapter_number")
        section_num = chunk.get("section_number")
        
        if doc_id and chapter_num is not None and section_num is not None:
            doc_structure[doc_id][chapter_num][section_num].append(chunk)
    
    # Build formatted context
    context_parts = []
    
    for doc_id in sorted(doc_structure.keys()):
        # Note: doc_id is still used internally for grouping, but not shown to LLM
        context_parts.append(f"\n{'='*80}")
        
        for chapter_num in sorted(doc_structure[doc_id].keys()):
            # Get chapter info from first chunk
            first_chunk = next(iter(next(iter(doc_structure[doc_id][chapter_num].values()))))
            chapter_name = first_chunk.get("chapter_name", f"Chapter {chapter_num}")
            chapter_summary = first_chunk.get("chapter_summary", "")
            
            context_parts.append(f"\n{'-'*60}")
            context_parts.append(f"CHAPTER {chapter_num}: {chapter_name}")
            if chapter_summary:
                context_parts.append(f"Summary: {chapter_summary}")
            context_parts.append(f"{'-'*60}\n")
            
            for section_num in sorted(doc_structure[doc_id][chapter_num].keys()):
                section_chunks = sorted(
                    doc_structure[doc_id][chapter_num][section_num],
                    key=lambda x: x.get("chunk_number", 0)
                )
                
                # Determine if this is a full section or single chunks
                first_chunk = section_chunks[0]
                section_page_count = first_chunk.get("section_page_count", 0)
                
                if section_page_count <= SECTION_EXPANSION_MAX_PAGES and len(section_chunks) > 1:
                    # Full section block
                    context_parts.append(f"\n### SECTION {section_num} (Full Section)")
                    context_parts.append(f"Filename: {first_chunk.get('filename', 'N/A')}")
                    context_parts.append(f"Pages: {first_chunk.get('section_start_page', 'N/A')} - {first_chunk.get('section_end_page', 'N/A')}")
                    context_parts.append(f"References: {first_chunk.get('section_start_reference', 'N/A')} - {first_chunk.get('section_end_reference', 'N/A')}")
                    
                    if first_chunk.get("section_summary"):
                        context_parts.append(f"Summary: {first_chunk.get('section_summary')}")
                    
                    context_parts.append("\nContent:")
                    for chunk in section_chunks:
                        content = chunk.get("chunk_content", "")
                        if content:
                            context_parts.append(content)
                else:
                    # Individual chunk blocks
                    for chunk in section_chunks:
                        context_parts.append(f"\n### SECTION {section_num}, CHUNK {chunk.get('chunk_number', 'N/A')}")
                        context_parts.append(f"Filename: {chunk.get('filename', 'N/A')}")
                        context_parts.append(f"Pages: {chunk.get('chunk_start_page', 'N/A')} - {chunk.get('chunk_end_page', 'N/A')}")
                        context_parts.append(f"References: {chunk.get('chunk_start_reference', 'N/A')} - {chunk.get('chunk_end_reference', 'N/A')}")
                        
                        content = chunk.get("chunk_content", "")
                        if content:
                            context_parts.append("\nContent:")
                            context_parts.append(content)
    
    formatted_context = "\n".join(context_parts)
    logger.info(f"Formatted context length: {len(formatted_context)} characters")
    
    return formatted_context


# Note: _build_reference_index function removed - no longer needed
# The LLM now extracts page-based research directly in _generate_synthesis_response
# This matches the catalog search approach where the LLM determines what to reference


def _generate_synthesis_response(
    query: str,
    formatted_context: str,
    chunks: List[Dict[str, Any]],
    token: Optional[str] = None
) -> Tuple[Dict[str, Any], LlmUsageDetails]:
    """
    Generate synthesis response with page-based extraction EXACTLY like catalog search.
    Returns structured output: {doc_name: {page_x: {research_content, file_link, file_name, page_number}}}
    This matches catalog search output format for consistent REF generation.
    """
    logger.info("Generating synthesis response with page-based extraction (catalog search format)")
    usage_details: LlmUsageDetails = None
    
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_context)
    
    try:
        model_config = config.get_model_config(RESPONSE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": [
                {"role": "system", "content": synthesis_prompt},
                {"role": "user", "content": "Please extract page-based research findings using the tool."}
            ],
            "max_tokens": MAX_RESPONSE_TOKENS,
            "temperature": RESPONSE_TEMPERATURE,
            "tools": [get_synthesis_tool_schema()],
            "tool_choice": {
                "type": "function",
                "function": {"name": get_synthesis_tool_schema()["function"]["name"]}
            },
            "database_name": "semantic_search_v2",
            "stream": False,
        }
        
        result = call_llm(**call_params)
        
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
        else:
            response = result
        
        if response and hasattr(response, "choices") and response.choices:
            tool_call = response.choices[0].message.tool_calls[0]
            arguments = json.loads(tool_call.function.arguments)
            
            status_summary = arguments.get("status_summary", "❌ No status")
            page_research = arguments.get("page_research", [])
            
            # Build structured output matching catalog search format EXACTLY
            # Format: {doc_name: {page_x: {research_content, file_link, file_name, page_number}}}
            structured_output = {}
            
            # Create a map of chunks for metadata lookup using filename + page
            chunk_map = {}
            for chunk in chunks:
                filename = chunk.get("filename")
                page_num = chunk.get("chunk_start_page")
                if filename and page_num:
                    key = f"{filename}_{page_num}"
                    chunk_map[key] = chunk
            
            # Process each page research item from LLM
            for page_item in page_research:
                filename = page_item.get("filename")  # LLM extracts this from context
                page_number = page_item.get("page_number")
                page_reference = page_item.get("page_reference")  # For display
                research_content = page_item.get("research_content", "")
                chapter_name = page_item.get("chapter_name", "")
                
                if not all([filename, page_number, research_content]):
                    logger.warning(f"Skipping incomplete page item: filename={filename}, page={page_number}")
                    continue
                
                # Find corresponding chunk for additional metadata
                chunk_key = f"{filename}_{page_number}"
                chunk = chunk_map.get(chunk_key, {})
                
                # Get filepath and source_filename from chunk if available
                filepath = chunk.get("filepath", "")
                source_filename = chunk.get("source_filename", "")
                
                # If no source_filename, try to derive from filename
                if not source_filename:
                    # Use filename without chapter prefix as fallback
                    source_filename = filename
                
                # Use source_filename as the document name for display (like catalog search uses document_name)
                # This gives us the original PDF name for the document grouping
                doc_name = source_filename
                
                # Initialize document entry if needed
                if doc_name not in structured_output:
                    structured_output[doc_name] = {}
                
                # Create page key
                page_key = f"page_{page_number}"
                
                # Build full S3 link from filepath or use filename as fallback
                if filepath:
                    file_link = filepath  # Use full filepath from database
                else:
                    # Fallback to constructing from config (should get S3 base from config)
                    s3_base = config.get("s3_base_url", "https://s3.amazonaws.com/your-bucket/")
                    file_link = f"{s3_base}{filename}"
                
                # Store in EXACT format that catalog search uses
                structured_output[doc_name][page_key] = {
                    "research_content": research_content,
                    "file_link": file_link,  # Full S3 link to chapter PDF
                    "file_name": filename,  # Chapter PDF filename
                    "page_number": page_number,  # Actual page in chapter PDF
                    # Additional fields for semantic search (will be ignored by model.py but useful for debugging)
                    "page_reference": page_reference or f"{page_number}",  # Fallback if missing
                    "chapter_name": chapter_name,
                }
            
            logger.info(f"Built structured output from {len(page_research)} page findings for {len(structured_output)} documents")
            
            # Return structured output and usage (status is embedded in the structured output processing)
            return structured_output, usage_details
    
    except Exception as e:
        logger.error(f"Synthesis generation failed: {e}", exc_info=True)
        return {}, usage_details


def query_database_sync(
    query: str,
    scope: str,
    document_config: Dict[str, Any],
    token: Optional[str] = None,
    process_monitor=None,
    query_stage_name: Optional[str] = None,
    research_statement: Optional[str] = None,
) -> SubagentResult:
    """
    Main entry point for semantic search v2 queries.
    
    Supports both single and multi-document queries based on document_config.
    """
    start_time = time.time()
    documents = document_config.get("documents", {})
    query_type = document_config.get("query_type", "single_document")
    
    database_name = "semantic_search_v2"
    logger.info(f"Querying {database_name}: '{query}' with scope: {scope}, type: {query_type}")
    
    stage_name = query_stage_name or f"db_query_{database_name}_unknown"
    
    result: DatabaseResponse = {} if scope == "research" else []
    initial_chunk_ids: Optional[List[str]] = None
    final_chunk_ids: Optional[List[str]] = None
    all_usage_details: List[LlmUsageDetails] = []
    reference_index: Optional[ReferenceIndex] = None
    
    conn = None
    cursor = None
    
    try:
        # Connect to database
        conn = connect_to_db()
        if not conn:
            raise ConnectionError("Failed to connect to database")
        
        register_vector(conn)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        logger.info("Database connection established")
        
        # Generate query embedding
        query_embedding, embed_usage = _generate_query_embedding(query, token)
        if embed_usage:
            all_usage_details.append(embed_usage)
        
        if query_embedding is None:
            error_response = {
                "detailed_research": "Could not generate embedding for query.",
                "status_summary": "❌ Embedding Generation Failed"
            }
            return (error_response, None, None, None, None, None)
        
        # Handle different scopes
        if scope == "metadata":
            # For metadata, return section summaries
            all_results = []
            
            if query_type == "multi_document":
                # Search each document separately
                for doc_id, k_value in documents.items():
                    results = _perform_vector_search(cursor, query_embedding, k_value, doc_id)
                    all_results.extend(results)
            else:
                # Single document search
                doc_id = list(documents.keys())[0] if documents else None
                k_value = list(documents.values())[0] if documents else INITIAL_K
                results = _perform_vector_search(cursor, query_embedding, k_value, doc_id)
                all_results = results
            
            # Build metadata response
            metadata_response = []
            seen_sections = set()
            
            for chunk in all_results:
                section_key = (
                    chunk.get("document_id"),
                    chunk.get("chapter_number"),
                    chunk.get("section_number")
                )
                
                if section_key not in seen_sections:
                    seen_sections.add(section_key)
                    metadata_response.append({
                        "id": chunk.get("id"),
                        "document_name": f"{chunk.get('chapter_name')} - Section {chunk.get('section_number')}",
                        "document_description": chunk.get("section_summary", ""),
                        "source": database_name,
                        "source_document_id": chunk.get("document_id"),
                    })
            
            return (metadata_response, None, None, None, None, None)
        
        elif scope == "research":
            # Research scope with full pipeline
            all_chunks = []
            initial_chunk_ids = []
            
            if query_type == "multi_document":
                # Process each document separately
                for doc_id, k_value in documents.items():
                    logger.info(f"Processing document {doc_id} with k={k_value}")
                    
                    # Initial search
                    chunks = _perform_vector_search(cursor, query_embedding, k_value, doc_id)
                    initial_chunk_ids.extend([str(c.get("id")) for c in chunks if c.get("id")])
                    
                    # Filter by relevance
                    relevant_chunks, filter_usage = _filter_by_relevance(query, chunks, token)
                    if filter_usage:
                        all_usage_details.append(filter_usage)
                    
                    all_chunks.extend(relevant_chunks)
            else:
                # Single document processing
                doc_id = list(documents.keys())[0] if documents else None
                k_value = list(documents.values())[0] if documents else INITIAL_K
                
                chunks = _perform_vector_search(cursor, query_embedding, k_value, doc_id)
                initial_chunk_ids = [str(c.get("id")) for c in chunks if c.get("id")]
                
                relevant_chunks, filter_usage = _filter_by_relevance(query, chunks, token)
                if filter_usage:
                    all_usage_details.append(filter_usage)
                
                all_chunks = relevant_chunks
            
            if not all_chunks:
                return ({
                    "detailed_research": "No relevant information found.",
                    "status_summary": "📄 No relevant information found"
                }, initial_chunk_ids, None, all_usage_details, None)
            
            # Expand to full sections
            expanded_chunks = _expand_to_full_sections(cursor, all_chunks)
            
            # Fill gaps
            final_chunks = _fill_section_gaps(cursor, expanded_chunks)
            final_chunk_ids = [str(c.get("id")) for c in final_chunks if c.get("id")]
            
            # Format context for LLM
            formatted_context = _format_context_with_blocks(final_chunks)
            
            # Generate synthesis with page-based extraction (returns structured output like catalog search)
            structured_output, synthesis_usage = _generate_synthesis_response(
                query, formatted_context, final_chunks, token=token
            )
            if synthesis_usage:
                all_usage_details.append(synthesis_usage)
            
            # Add process monitor details
            if process_monitor:
                if initial_chunk_ids:
                    process_monitor.add_stage_details(
                        stage_name, 
                        initial_document_ids=initial_chunk_ids,
                        result_count=len(initial_chunk_ids)
                    )
                if final_chunk_ids:
                    process_monitor.add_stage_details(
                        stage_name,
                        final_document_ids=final_chunk_ids
                    )
            
            # For backward compatibility, create a simple response dict
            # The actual research is in the structured_output which goes in reference_index position
            response_dict = {
                "detailed_research": f"Found research from {len(structured_output)} documents",
                "status_summary": "✅ Research extracted"
            }
            
            return (
                response_dict,  # Simple response for compatibility
                initial_chunk_ids,
                None,  # file_links (not needed as they're in structured_output)
                None,  # page_section_refs
                None,  # section_content_map
                structured_output  # This is the reference_index with page-based research (SAME FORMAT AS CATALOG SEARCH)
            )
        
        else:
            logger.error(f"Invalid scope: {scope}")
            return ({
                "detailed_research": f"Invalid scope: {scope}",
                "status_summary": "❌ Invalid Scope"
            }, None, None, None, None, None)
    
    except Exception as e:
        logger.error(f"Error in query_database_sync: {e}", exc_info=True)
        
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=str(e))
        
        return ({
            "detailed_research": f"Error: {str(e)}",
            "status_summary": "❌ Query Error"
        }, None, None, None, None, None)
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Query completed in {elapsed_time:.2f} seconds")