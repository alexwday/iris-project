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
import re
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
RESPONSE_MODEL_CAPABILITY = "large"  # Using large model for better instruction following and complete extraction
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

        logger.info(
            f"Using embedding model: {model_name} with {EMBEDDING_DIMENSIONS} dimensions"
        )

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
    cursor, query_embedding: List[float], k: int, doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Perform vector search on iris_semantic_search table."""
    doc_filter = f" filtering for document_id='{doc_id}'" if doc_id else ""
    logger.info(f"Performing vector search (k={k}){doc_filter}")

    if query_embedding is None:
        logger.error("Cannot perform vector search without embedding.")
        return []

    # Debug: Check query embedding validity
    logger.debug(
        f"Query embedding length: {len(query_embedding) if query_embedding else 0}"
    )
    logger.debug(
        f"Query embedding first 5 values: {query_embedding[:5] if query_embedding else 'None'}"
    )

    try:
        # First, let's check the database embeddings directly
        # Simple check first
        simple_check = """
            SELECT COUNT(*) as total_rows,
                   COUNT(embedding) as non_null_embeddings,
                   COUNT(CASE WHEN embedding IS NULL THEN 1 END) as null_embeddings
            FROM iris_semantic_search;
        """
        cursor.execute(simple_check)
        check_result = dict(cursor.fetchone())
        logger.info(
            f"Table check - Total rows: {check_result.get('total_rows')}, "
            f"Non-null embeddings: {check_result.get('non_null_embeddings')}, "
            f"Null embeddings: {check_result.get('null_embeddings')}"
        )

        # Detailed diagnostic
        diagnostic_sql = """
            SELECT 
                id,
                document_id,
                chunk_number,
                embedding IS NULL as embedding_is_null,
                pg_typeof(embedding) as embedding_type,
                CASE 
                    WHEN embedding IS NOT NULL THEN array_length(embedding::real[], 1)
                    ELSE NULL
                END as embedding_dimension,
                embedding <=> %s::vector as distance,
                1 - (embedding <=> %s::vector) as similarity_score
            FROM iris_semantic_search
            WHERE embedding IS NOT NULL
            LIMIT 5;
        """
        logger.info("Running diagnostic check on database embeddings...")
        cursor.execute(diagnostic_sql, [query_embedding, query_embedding])
        diagnostic_results = cursor.fetchall()

        for row in diagnostic_results:
            diag = dict(row)
            logger.info(
                f"Diagnostic - ID: {diag.get('id')}, "
                f"embedding_is_null: {diag.get('embedding_is_null')}, "
                f"type: {diag.get('embedding_type')}, "
                f"dimension: {diag.get('embedding_dimension')}, "
                f"distance: {diag.get('distance')}, "
                f"similarity: {diag.get('similarity_score')}"
            )
    except Exception as e:
        logger.error(f"Diagnostic query failed: {e}")

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
                CASE 
                    WHEN embedding IS NULL THEN NULL
                    WHEN embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf' THEN NULL
                    ELSE 1 - (embedding::vector <=> %s::vector)
                END AS vector_score
            FROM {TARGET_TABLE}
            WHERE 
                embedding IS NOT NULL
                -- Filter out vectors with NaN or Infinity values
                AND NOT embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf'
                -- Ensure the vector has the correct dimensions
                AND array_length(embedding::real[], 1) = {EMBEDDING_DIMENSIONS}
                {" AND document_id = %s" if doc_id else ""}
            ORDER BY vector_score DESC NULLS LAST
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

            # Debug: Log the keys for the first record to see what columns we got
            if i == 0:
                logger.info(f"First record keys from SQL: {list(record.keys())}")
                logger.info(
                    f"vector_score in first record: {record.get('vector_score')}"
                )

            results.append(record)

            # Debug: Log vector scores to understand similarity quality
            if i < 5:  # Log top 5 scores
                vector_score = record.get("vector_score")
                doc_id = record.get("document_id", "")
                chunk_num = record.get("chunk_number", "")

                # Handle None values explicitly - this indicates a serious problem
                if vector_score is None:
                    logger.error(
                        f"  Rank {i+1}: vector_score is NULL! This means embedding similarity failed."
                    )
                    logger.error(
                        f"    Possible causes: embedding is NULL in DB, dimension mismatch, or invalid vector"
                    )
                    logger.error(f"    Doc: {doc_id}, Chunk: {chunk_num}")
                    vector_score = 0  # Default for display

                logger.info(
                    f"  Rank {i+1}: score={vector_score:.4f}, doc={doc_id}, chunk={chunk_num}"
                )

        # Warn if top scores are low
        if results:
            top_score = results[0].get("vector_score")
            if top_score is not None and top_score < 0.5:
                logger.warning(
                    f"Low similarity scores detected! Top score is only {top_score:.4f}"
                )
                logger.warning(
                    "This may indicate embedding mismatch between query and stored vectors"
                )

        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return []


def _filter_by_relevance(
    query: str, chunks: List[Dict[str, Any]], token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], LlmUsageDetails]:
    """Use LLM to filter chunks by relevance based on summaries."""
    logger.info(f"Filtering {len(chunks)} chunks by relevance")
    usage_details: LlmUsageDetails = None

    # TEMPORARY: Option to bypass filter for debugging
    BYPASS_FILTER = os.getenv("BYPASS_RELEVANCE_FILTER", "false").lower() == "true"
    if BYPASS_FILTER:
        logger.warning("BYPASSING relevance filter - returning all chunks!")
        return chunks, usage_details

    if not chunks:
        return [], usage_details

    # Debug: Log sample chunk data
    if chunks:
        sample_chunk = chunks[0]
        logger.debug(f"Sample chunk keys: {list(sample_chunk.keys())}")
        logger.debug(
            f"Sample chapter_summary: {sample_chunk.get('chapter_summary', 'MISSING')[:200] if sample_chunk.get('chapter_summary') else 'EMPTY'}"
        )
        logger.debug(
            f"Sample section_summary: {sample_chunk.get('section_summary', 'MISSING')[:200] if sample_chunk.get('section_summary') else 'EMPTY'}"
        )

    # Prepare summaries for LLM evaluation with simple 1-based numbering
    summaries_list = []
    chunk_by_number = {}  # Map number to actual chunk
    empty_summary_count = 0
    current_number = 1  # Track actual numbering for non-empty chunks

    for chunk in chunks:
        chunk_id = chunk.get("id")
        chapter_summary = chunk.get("chapter_summary", "")
        section_summary = chunk.get("section_summary", "")

        # Debug: Check for empty summaries
        if not chapter_summary and not section_summary:
            empty_summary_count += 1
            logger.debug(f"Chunk {chunk_id} has empty summaries - skipping")
            continue  # Skip chunks with no summaries

        # Store chunk with sequential numbering (no gaps)
        chunk_by_number[current_number] = chunk
        summaries_list.append(
            f"{current_number}. Chapter: {chapter_summary}\n   Section: {section_summary}"
        )

        # Debug: Check if vector_score exists
        if chunk.get("vector_score") is None:
            logger.warning(f"Chunk {chunk_id} missing vector_score!")

        current_number += 1  # Only increment for chunks we keep

    logger.info(
        f"Prepared {len(summaries_list)} summaries for evaluation, {empty_summary_count} chunks had empty summaries"
    )

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

    system_message = """You are a relevance filter evaluating HIGH-LEVEL SUMMARIES of document sections.

CRITICAL CONTEXT:
- You are seeing ONLY 1-2 sentence summaries of chapters/sections that may be 10-100+ pages long
- These summaries are abstractions that won't contain specific details from the actual content
- The full content contains detailed information not visible in these summaries
- Your role is to filter out COMPLETELY UNRELATED topics, not to find exact answers

Your task: Identify which document sections are POTENTIALLY RELEVANT to explore further.

KEEP sections if they:
- Mention ANY concept, term, or domain related to the query
- Could POSSIBLY contain relevant information based on the topic area
- Discuss related systems, processes, or subject matter
- Provide context, background, or foundational concepts
- Cover adjacent or tangentially related topics

ONLY REMOVE sections that are:
- About completely different subject domains with ZERO overlap
- Discussing unrelated technical areas or business functions
- Clearly about different products, systems, or topics entirely

Remember: A summary saying "Overview of accounting principles" won't mention specific standards,
but the full 50-page chapter likely contains detailed guidance on many specific accounting topics.

BE EXTREMELY CONSERVATIVE - the actual content is much richer than these brief summaries suggest.
Respond with a JSON ARRAY of numbers to REMOVE (only completely off-topic sections)."""

    user_message = f"""Query: "{query}"

Chapter and Section Summaries (1-2 sentences each, representing 10-100+ pages of content):
{prompt_summaries}

These are HIGH-LEVEL SUMMARIES only. The actual sections contain extensive details not reflected here.

Return a JSON ARRAY of summary numbers that represent COMPLETELY UNRELATED topics to remove.
- Consider whether the TOPIC AREA could contain relevant information
- DO NOT expect summaries to contain specific query terms or details
- Return empty array [] if all sections might contain relevant information
- Example: [3, 15] means sections 3 and 15 are about completely different domains

CRITICAL: These summaries are abstractions. Judge by TOPIC RELEVANCE, not whether the summary answers the query."""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
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
            logger.debug(
                f"LLM relevance response: {content[:500] if content else 'EMPTY'}"
            )

            # Parse the array of numbers to remove
            numbers_to_remove = json.loads(content)
            logger.debug(f"Numbers to remove (irrelevant): {numbers_to_remove}")

            # Handle both array and dict formats for backward compatibility
            if isinstance(numbers_to_remove, dict):
                logger.warning(
                    "LLM returned dict format instead of array - attempting to extract irrelevant items"
                )
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
                logger.info(
                    f"Extracted {len(remove_list)} items to remove from dict format"
                )
            elif not isinstance(numbers_to_remove, list):
                logger.error(f"Expected array but got: {type(numbers_to_remove)}")
                logger.warning("Returning all chunks without filtering")
                return chunks, usage_details

            # Convert to set for efficient lookup
            remove_set = set(numbers_to_remove)
            logger.info(
                f"LLM marked {len(remove_set)} summaries as completely irrelevant for removal: {sorted(remove_set)[:10]}{'...' if len(remove_set) > 10 else ''}"
            )

            # Keep chunks that are NOT in the remove list
            filtered_chunks = []
            removed_summaries = []
            kept_summaries = []

            for number, chunk in chunk_by_number.items():
                vector_score = chunk.get("vector_score")
                # Handle None or missing vector_score
                score_str = f"{vector_score:.3f}" if vector_score is not None else "N/A"
                chapter_summary = chunk.get("chapter_summary", "")[:100]
                section_summary = chunk.get("section_summary", "")[:100]

                if number not in remove_set:
                    filtered_chunks.append(chunk)
                    kept_summary = f"  KEPT #{number} (score={score_str}): Ch: {chapter_summary}... | Sec: {section_summary}..."
                    kept_summaries.append(kept_summary)
                    logger.debug(
                        f"Keeping chunk {number} (ID: {chunk.get('id')}) as relevant"
                    )
                else:
                    removed_summary = f"  REMOVED #{number} (score={score_str}): Ch: {chapter_summary}... | Sec: {section_summary}..."
                    removed_summaries.append(removed_summary)
                    logger.debug(
                        f"Removing chunk {number} (ID: {chunk.get('id')}) as irrelevant"
                    )

            logger.info(
                f"Kept {len(filtered_chunks)} relevant chunks out of {len(chunk_by_number)}"
            )

            # Always log what was kept and removed at INFO level for debugging
            if kept_summaries:
                logger.info(f"KEPT chunks (top scores):")
                for summary in kept_summaries[:5]:  # Show top 5 kept
                    logger.info(summary)

            if removed_summaries:
                logger.info(f"REMOVED chunks (filtered out):")
                for summary in removed_summaries[:5]:  # Show top 5 removed
                    logger.info(summary)

            # If aggressive filtering, show what was removed
            if (
                len(removed_summaries) > 0
                and len(removed_summaries) > len(chunk_by_number) * 0.5
            ):
                logger.warning(
                    f"Aggressive filtering detected! Removed {len(removed_summaries)} chunks:"
                )
                for summary in removed_summaries[:3]:  # Show first 3 removed
                    logger.warning(summary)
                if len(removed_summaries) > 3:
                    logger.warning(f"  ... and {len(removed_summaries) - 3} more")

            # If too many chunks were filtered out, use fallback
            if len(filtered_chunks) <= 2 and len(chunk_by_number) > 0:
                logger.warning(
                    f"Only {len(filtered_chunks)} chunks kept out of {len(chunk_by_number)}!"
                )
                logger.warning(f"Query was: {query}")
                logger.warning(
                    "Overly aggressive filtering detected - using top 5 chunks as fallback"
                )
                # Return top 5 chunks by vector score as fallback
                filtered_chunks = list(chunk_by_number.values())[:5]
                logger.warning(
                    f"Returning top 5 chunks by vector similarity as fallback"
                )

            return filtered_chunks, usage_details

    except Exception as e:
        logger.error(f"Relevance filtering failed: {e}", exc_info=True)

    return chunks, usage_details


def _expand_to_full_sections(
    cursor, chunks: List[Dict[str, Any]]
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
                    logger.debug(
                        f"Expanded section {section_key} to {len(section_chunks)} chunks"
                    )
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


def _fill_section_gaps(cursor, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                for missing_section in range(
                    sorted_sections[i] + 1, sorted_sections[i + 1]
                ):
                    sections_to_add.append((doc_id, chapter_num, missing_section))
                    logger.debug(
                        f"Gap filling: Adding section {missing_section} in chapter {chapter_num}"
                    )

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


def _format_context_with_blocks(chunks: List[Dict[str, Any]]) -> str:
    """Format chunks into a clear, structured format for LLM parsing."""
    logger.info(f"Formatting {len(chunks)} chunks into structured context")

    # Group by document, then chapter, then section
    doc_structure = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for chunk in chunks:
        doc_id = chunk.get("document_id")
        chapter_num = chunk.get("chapter_number")
        section_num = chunk.get("section_number")

        if doc_id and chapter_num is not None and section_num is not None:
            doc_structure[doc_id][chapter_num][section_num].append(chunk)

    # Build structured context with clear XML-like tags for easy parsing
    context_parts = []

    for doc_id in sorted(doc_structure.keys()):
        # Document block
        context_parts.append(f'\n<DOCUMENT id="{doc_id}">')

        for chapter_num in sorted(doc_structure[doc_id].keys()):
            # Get chapter metadata from first chunk
            first_chunk = next(
                iter(next(iter(doc_structure[doc_id][chapter_num].values())))
            )
            chapter_name = first_chunk.get("chapter_name", f"Chapter {chapter_num}")
            chapter_summary = first_chunk.get("chapter_summary", "")
            filename = first_chunk.get("filename", "")
            source_filename = first_chunk.get("source_filename", "")
            filepath = first_chunk.get("filepath", "")

            # Chapter block with metadata
            context_parts.append(f'\n<CHAPTER number="{chapter_num}">')
            context_parts.append(f"  <metadata>")
            context_parts.append(f"    <chapter_name>{chapter_name}</chapter_name>")
            context_parts.append(f"    <filename>{filename}</filename>")
            context_parts.append(
                f"    <source_filename>{source_filename}</source_filename>"
            )
            if filepath:
                context_parts.append(f"    <filepath>{filepath}</filepath>")
            if chapter_summary:
                context_parts.append(
                    f"    <chapter_summary>{chapter_summary}</chapter_summary>"
                )
            context_parts.append(f"  </metadata>")

            # Process sections
            context_parts.append(f"  <sections>")

            for section_num in sorted(doc_structure[doc_id][chapter_num].keys()):
                section_chunks = sorted(
                    doc_structure[doc_id][chapter_num][section_num],
                    key=lambda x: x.get("chunk_number", 0),
                )

                first_chunk = section_chunks[0]
                section_page_count = first_chunk.get("section_page_count", 0)
                is_full_section = (
                    section_page_count <= SECTION_EXPANSION_MAX_PAGES
                    and len(section_chunks) > 1
                )

                # Section block
                context_parts.append(
                    f"\n    <SECTION number=\"{section_num}\" type=\"{'full' if is_full_section else 'partial'}\">"
                )
                context_parts.append(f"      <section_metadata>")
                context_parts.append(
                    f"        <filename>{first_chunk.get('filename', '')}</filename>"
                )
                context_parts.append(
                    f"        <source_filename>{first_chunk.get('source_filename', '')}</source_filename>"
                )
                context_parts.append(
                    f"        <start_page>{first_chunk.get('section_start_page', '')}</start_page>"
                )
                context_parts.append(
                    f"        <end_page>{first_chunk.get('section_end_page', '')}</end_page>"
                )
                context_parts.append(
                    f"        <start_reference>{first_chunk.get('section_start_reference', '')}</start_reference>"
                )
                context_parts.append(
                    f"        <end_reference>{first_chunk.get('section_end_reference', '')}</end_reference>"
                )
                if first_chunk.get("section_summary"):
                    context_parts.append(
                        f"        <section_summary>{first_chunk.get('section_summary')}</section_summary>"
                    )
                context_parts.append(f"      </section_metadata>")

                # Content blocks
                context_parts.append(f"      <content_blocks>")

                if is_full_section:
                    # Combine all chunks for full section
                    combined_content = []

                    # Add section-level page markers at the start
                    section_start_page = first_chunk.get("section_start_page", "")
                    section_start_ref = first_chunk.get("section_start_reference", "")
                    section_end_page = first_chunk.get("section_end_page", "")
                    section_end_ref = first_chunk.get("section_end_reference", "")

                    if section_start_page and section_start_ref:
                        combined_content.append(
                            f'<!-- SECTION START: PageNumber="{section_start_page}" PageReference="{section_start_ref}" -->'
                        )

                    for chunk in section_chunks:
                        content = chunk.get("chunk_content", "")
                        if content:
                            # Include chunk metadata as comments for reference
                            chunk_meta = (
                                f"<!-- Chunk {chunk.get('chunk_number')}: "
                                f"Pages {chunk.get('chunk_start_page')}-{chunk.get('chunk_end_page')}, "
                                f"Refs {chunk.get('chunk_start_reference')}-{chunk.get('chunk_end_reference')} -->"
                            )
                            combined_content.append(chunk_meta)
                            combined_content.append(content)

                    # Add section-level page markers at the end
                    if section_end_page and section_end_ref:
                        combined_content.append(
                            f'<!-- SECTION END: PageNumber="{section_end_page}" PageReference="{section_end_ref}" -->'
                        )

                    if combined_content:
                        context_parts.append(f"        <content>")
                        context_parts.extend(
                            [f"          {line}" for line in combined_content]
                        )
                        context_parts.append(f"        </content>")
                else:
                    # Individual chunks
                    for chunk in section_chunks:
                        context_parts.append(
                            f"        <chunk number=\"{chunk.get('chunk_number')}\">"
                        )
                        context_parts.append(f"          <chunk_metadata>")
                        context_parts.append(
                            f"            <filename>{chunk.get('filename', '')}</filename>"
                        )
                        context_parts.append(
                            f"            <source_filename>{chunk.get('source_filename', '')}</source_filename>"
                        )
                        context_parts.append(
                            f"            <start_page>{chunk.get('chunk_start_page', '')}</start_page>"
                        )
                        context_parts.append(
                            f"            <end_page>{chunk.get('chunk_end_page', '')}</end_page>"
                        )
                        context_parts.append(
                            f"            <start_reference>{chunk.get('chunk_start_reference', '')}</start_reference>"
                        )
                        context_parts.append(
                            f"            <end_reference>{chunk.get('chunk_end_reference', '')}</end_reference>"
                        )
                        context_parts.append(f"          </chunk_metadata>")

                        content = chunk.get("chunk_content", "")
                        if content:
                            context_parts.append(f"          <content>")

                            # Add explicit page markers at the start of chunk content
                            # This ensures LLM always has page info even if HTML tags are missing
                            chunk_start_page = chunk.get("chunk_start_page", "")
                            chunk_start_ref = chunk.get("chunk_start_reference", "")
                            chunk_end_page = chunk.get("chunk_end_page", "")
                            chunk_end_ref = chunk.get("chunk_end_reference", "")

                            # Add start marker if we have page info
                            if chunk_start_page and chunk_start_ref:
                                context_parts.append(
                                    f'            <!-- CHUNK START: PageNumber="{chunk_start_page}" PageReference="{chunk_start_ref}" -->'
                                )

                            # Add the actual content (which may also contain HTML page markers)
                            for line in content.split("\n"):
                                context_parts.append(f"            {line}")

                            # Add end marker if different from start
                            if (
                                chunk_end_page
                                and chunk_end_ref
                                and (
                                    chunk_end_page != chunk_start_page
                                    or chunk_end_ref != chunk_start_ref
                                )
                            ):
                                context_parts.append(
                                    f'            <!-- CHUNK END: PageNumber="{chunk_end_page}" PageReference="{chunk_end_ref}" -->'
                                )

                            context_parts.append(f"          </content>")
                        context_parts.append(f"        </chunk>")

                context_parts.append(f"      </content_blocks>")
                context_parts.append(f"    </SECTION>")

            context_parts.append(f"  </sections>")
            context_parts.append(f"</CHAPTER>")

        context_parts.append(f"</DOCUMENT>")

    formatted_context = "\n".join(context_parts)
    logger.info(f"Formatted context length: {len(formatted_context)} characters")

    return formatted_context


# Note: _build_reference_index function removed - no longer needed
# The LLM now extracts page-based research directly in _generate_synthesis_response
# This matches the catalog search approach where the LLM determines what to reference


def _analyze_extraction_discrepancy(
    expected_pages: int, 
    actual_pages: int,
    formatted_context: str,
    page_research: List[Dict[str, Any]]
) -> None:
    """Debug function to analyze why we're not extracting all expected pages."""
    logger.info("=" * 80)
    logger.info("DEBUG: EXTRACTION DISCREPANCY ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"DEBUG: Expected at least {expected_pages} pages, but got {actual_pages}")
    
    if actual_pages < expected_pages:
        logger.warning(f"DEBUG: MISSING {expected_pages - actual_pages} pages!")
        
        # Check if context might be truncated
        if "..." in formatted_context[-100:]:
            logger.warning("DEBUG: Context might be truncated (ends with '...')")
        
        # Check for specific patterns that might limit extraction
        
        # Check if prompt mentions any limits
        if "first" in formatted_context[:1000].lower() or "one" in formatted_context[:1000].lower():
            logger.warning("DEBUG: Context or prompt might contain limiting words like 'first' or 'one'")
        
        # Count actual page markers vs extracted
        page_markers = re.findall(r'PageNumber="(\d+)"', formatted_context)
        unique_markers = set(page_markers)
        extracted_pages = set(str(item.get('page_number')) for item in page_research if item.get('page_number'))
        
        missing_pages = unique_markers - extracted_pages
        if missing_pages:
            logger.warning(f"DEBUG: Pages in context but NOT extracted: {sorted(missing_pages)[:20]}")
        
        # Check if all chapters are represented
        chapter_pattern = r'<CHAPTER number="(\d+)">'
        chapters_in_context = set(re.findall(chapter_pattern, formatted_context))
        extracted_chapters = set(str(item.get('chapter_number')) for item in page_research if item.get('chapter_number'))
        
        missing_chapters = chapters_in_context - extracted_chapters
        if missing_chapters:
            logger.warning(f"DEBUG: Chapters in context but NOT extracted: {sorted(missing_chapters)}")
    
    logger.info("=" * 80)


def _generate_synthesis_response(
    query: str,
    formatted_context: str,
    chunks: List[Dict[str, Any]],
    token: Optional[str] = None,
) -> Tuple[Dict[str, Any], LlmUsageDetails]:
    """
    Generate synthesis response with page-based extraction EXACTLY like catalog search.
    Returns structured output: {doc_name: {page_x: {research_content, file_link, file_name, page_number}}}
    This matches catalog search output format for consistent REF generation.
    """
    logger.info(
        "Generating synthesis response with page-based extraction (catalog search format)"
    )
    usage_details: LlmUsageDetails = None
    
    # DEBUG: Log comprehensive input analysis
    logger.info("=" * 80)
    logger.info("DEBUG: PRE-LLM CALL ANALYSIS")
    logger.info("=" * 80)
    
    # 1. Analyze formatted_context
    logger.info(f"DEBUG: Formatted context length: {len(formatted_context)} characters")
    logger.info(f"DEBUG: First 2000 chars of formatted_context:\n{formatted_context[:2000]}")
    
    # 2. Analyze chunks
    logger.info(f"DEBUG: Total chunks being processed: {len(chunks)}")
    
    # 3. Count distinct pages and documents in chunks
    distinct_pages = set()
    distinct_docs = set()
    distinct_chapters = set()
    pages_per_doc = {}
    
    for i, chunk in enumerate(chunks):
        filename = chunk.get("filename", "")
        source_filename = chunk.get("source_filename", "")
        start_page = chunk.get("chunk_start_page", "")
        end_page = chunk.get("chunk_end_page", "")
        chapter_num = chunk.get("chapter_number", "")
        
        if filename and start_page:
            page_key = f"{filename}_page_{start_page}"
            distinct_pages.add(page_key)
            
            if source_filename not in pages_per_doc:
                pages_per_doc[source_filename] = set()
            pages_per_doc[source_filename].add(start_page)
        
        if source_filename:
            distinct_docs.add(source_filename)
        if chapter_num:
            distinct_chapters.add(f"Chapter_{chapter_num}")
            
        # Log sample chunk data (first 3 chunks)
        if i < 3:
            logger.info(f"DEBUG: Sample Chunk {i}:")
            logger.info(f"  - filename: {filename}")
            logger.info(f"  - source_filename: {source_filename}")
            logger.info(f"  - chapter_number: {chapter_num}")
            logger.info(f"  - start_page: {start_page}, end_page: {end_page}")
            logger.info(f"  - start_ref: {chunk.get('chunk_start_reference', '')}")
            logger.info(f"  - end_ref: {chunk.get('chunk_end_reference', '')}")
            content_preview = chunk.get("chunk_content", "")[:200]
            logger.info(f"  - content preview: {content_preview}...")
    
    logger.info(f"DEBUG: Distinct pages found in chunks: {len(distinct_pages)}")
    logger.info(f"DEBUG: Distinct documents: {list(distinct_docs)}")
    logger.info(f"DEBUG: Distinct chapters: {list(distinct_chapters)}")
    logger.info(f"DEBUG: Pages per document:")
    for doc, pages in pages_per_doc.items():
        logger.info(f"  - {doc}: {sorted(pages)}")
    
    # 4. Analyze formatted_context for page markers
    
    # Count CHAPTER tags
    chapter_pattern = r'<CHAPTER number="(\d+)">'
    chapters_in_context = re.findall(chapter_pattern, formatted_context)
    logger.info(f"DEBUG: CHAPTER tags found in context: {chapters_in_context}")
    
    # Count page markers in HTML comments
    page_marker_pattern = r'PageNumber="(\d+)"'
    page_markers = re.findall(page_marker_pattern, formatted_context)
    unique_page_markers = set(page_markers)
    logger.info(f"DEBUG: Total PageNumber markers: {len(page_markers)}, Unique: {len(unique_page_markers)}")
    logger.info(f"DEBUG: Unique page numbers from markers: {sorted(unique_page_markers)[:20]}...")  # First 20
    
    # Count SECTION tags
    section_pattern = r'<SECTION.*?type="(.*?)"'
    sections = re.findall(section_pattern, formatted_context)
    logger.info(f"DEBUG: SECTION tags found: {len(sections)} (full: {sections.count('full')}, partial: {sections.count('partial')})")
    
    # Count chunk tags
    chunk_tag_pattern = r'<chunk>'
    chunk_tags = re.findall(chunk_tag_pattern, formatted_context)
    logger.info(f"DEBUG: <chunk> tags found: {len(chunk_tags)}")
    
    logger.info("=" * 80)
    logger.info("DEBUG: EXPECTED EXTRACTION")
    logger.info("=" * 80)
    logger.info(f"DEBUG: Based on input analysis, expecting AT LEAST:")
    logger.info(f"  - {len(distinct_pages)} distinct page findings")
    logger.info(f"  - From {len(distinct_docs)} documents")
    logger.info(f"  - Across {len(distinct_chapters)} chapters")
    logger.info("=" * 80)

    synthesis_prompt = get_content_synthesis_prompt(query, formatted_context)
    
    # DEBUG: Log the actual prompt being sent
    logger.info("=" * 80)
    logger.info("DEBUG: PROMPT ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"DEBUG: Synthesis prompt length: {len(synthesis_prompt)} characters")
    
    # Check for any limiting keywords in the prompt
    limiting_keywords = ["first", "one", "single", "only one", "limit"]
    for keyword in limiting_keywords:
        if keyword in synthesis_prompt.lower():
            count = synthesis_prompt.lower().count(keyword)
            logger.warning(f"DEBUG: Found limiting keyword '{keyword}' {count} times in prompt")
    
    # Log the first part of the prompt (before context)
    prompt_before_context = synthesis_prompt.split("<DOCUMENT>")[0] if "<DOCUMENT>" in synthesis_prompt else synthesis_prompt[:2000]
    logger.info(f"DEBUG: Prompt instructions (before context):\n{prompt_before_context}")
    logger.info("=" * 80)

    try:
        model_config = config.get_model_config(RESPONSE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": [
                {"role": "system", "content": synthesis_prompt},
                {
                    "role": "user",
                    "content": (
                        "Extract research findings from ALL relevant pages in the context. "
                        "Create MULTIPLE page_research array items - one for EACH page that contains relevant information. "
                        "Do NOT stop after one page. The page_research array should contain MANY items, not just one. "
                        "Each distinct page with relevant content should have its own entry in the array."
                    ),
                },
            ],
            "max_tokens": MAX_RESPONSE_TOKENS,
            "temperature": RESPONSE_TEMPERATURE,
            "tools": [get_synthesis_tool_schema()],
            "tool_choice": {
                "type": "function",
                "function": {"name": get_synthesis_tool_schema()["function"]["name"]},
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
            
            # DEBUG: Log raw LLM response
            logger.info("=" * 80)
            logger.info("DEBUG: LLM RESPONSE ANALYSIS")
            logger.info("=" * 80)
            logger.info(f"DEBUG: Raw arguments from LLM: {json.dumps(arguments, indent=2)[:3000]}...")  # First 3000 chars
            
            status_summary = arguments.get("status_summary", "❌ No status")
            page_research = arguments.get("page_research", [])
            
            logger.info(f"DEBUG: Status summary: {status_summary}")
            logger.info(f"DEBUG: Number of page_research items received: {len(page_research)}")
            
            # Log each page_research item
            for i, page_item in enumerate(page_research[:10]):  # First 10 items
                logger.info(f"DEBUG: Page research item {i}:")
                logger.info(f"  - filename: {page_item.get('filename', 'MISSING')}")
                logger.info(f"  - page_number: {page_item.get('page_number', 'MISSING')}")
                logger.info(f"  - page_reference: {page_item.get('page_reference', 'MISSING')}")
                logger.info(f"  - chapter_number: {page_item.get('chapter_number', 'MISSING')}")
                logger.info(f"  - source_filename: {page_item.get('source_filename', 'MISSING')}")
                logger.info(f"  - research_content length: {len(page_item.get('research_content', ''))}")
                logger.info(f"  - research_content preview: {page_item.get('research_content', '')[:200]}...")
            
            if len(page_research) > 10:
                logger.info(f"DEBUG: ... and {len(page_research) - 10} more page research items")
            
            logger.info("=" * 80)
            
            # Call debug analysis function to compare expected vs actual
            _analyze_extraction_discrepancy(
                expected_pages=len(distinct_pages),
                actual_pages=len(page_research),
                formatted_context=formatted_context,
                page_research=page_research
            )

            # Build structured output matching catalog search format EXACTLY
            # Format: {doc_name: {page_x: {research_content, file_link, file_name, page_number}}}
            structured_output = {}

            # Create a map of chunks for metadata lookup using filename + page
            chunk_map = {}
            source_filename_map = {}  # Track source_filename consistency
            
            logger.info("=" * 80)
            logger.info("DEBUG: BUILDING CHUNK MAP")
            logger.info("=" * 80)

            for chunk in chunks:
                filename = chunk.get("filename")
                page_num = chunk.get("chunk_start_page")
                source_fn = chunk.get("source_filename")

                if filename and page_num:
                    key = f"{filename}_{page_num}"
                    chunk_map[key] = chunk
                    logger.debug(f"DEBUG: Added to chunk_map: {key}")

                # Track source_filename for consistency validation
                if filename and source_fn:
                    if (
                        filename in source_filename_map
                        and source_filename_map[filename] != source_fn
                    ):
                        logger.warning(
                            f"Inconsistent source_filename for {filename}: "
                            f"'{source_filename_map[filename]}' vs '{source_fn}'"
                        )
                    source_filename_map[filename] = source_fn
            
            logger.info(f"DEBUG: Chunk map has {len(chunk_map)} entries")
            logger.info(f"DEBUG: Source filename map: {source_filename_map}")
            logger.info("=" * 80)
            logger.info("DEBUG: PROCESSING PAGE RESEARCH ITEMS")
            logger.info("=" * 80)

            # Process each page research item from LLM
            processed_count = 0
            skipped_count = 0
            
            for idx, page_item in enumerate(page_research):
                filename = page_item.get("filename")  # LLM extracts this from context
                page_number = page_item.get("page_number")
                page_reference = page_item.get("page_reference")  # For display
                research_content = page_item.get("research_content", "")
                chapter_name = page_item.get("chapter_name", "")
                chapter_number = page_item.get(
                    "chapter_number"
                )  # Extract chapter number
                
                # Ensure page_number is valid (not 0 or None)
                if page_number == 0 or page_number is None:
                    logger.warning(f"DEBUG: Invalid page_number={page_number} for item {idx}, will try to extract from chunk")
                    page_number = None  # Reset to None to trigger chunk lookup

                logger.info(f"DEBUG: Processing item {idx}: filename={filename}, page={page_number}, chapter={chapter_number}")
                
                if not all([filename, page_number, research_content]):
                    logger.warning(
                        f"DEBUG: SKIPPING incomplete page item {idx}: filename={filename}, page={page_number}, "
                        f"has_content={bool(research_content)}"
                    )
                    skipped_count += 1
                    continue

                # Find corresponding chunk for additional metadata
                chunk_key = f"{filename}_{page_number}" if page_number else None
                chunk = {}
                
                if chunk_key:
                    logger.info(f"DEBUG: Looking up chunk with key: {chunk_key}")
                    chunk = chunk_map.get(chunk_key, {})
                    
                    if chunk:
                        logger.info(f"DEBUG: Found chunk for {chunk_key}")
                    else:
                        logger.warning(f"DEBUG: No chunk found for {chunk_key} - will use page_item data only")
                else:
                    # Try to find chunk by filename alone if page_number is missing
                    logger.warning(f"DEBUG: No page_number, searching chunks by filename={filename}")
                    for key, ch in chunk_map.items():
                        if key.startswith(f"{filename}_"):
                            chunk = ch
                            # Extract page number from chunk
                            extracted_page = chunk.get("chunk_start_page")
                            if extracted_page:
                                page_number = extracted_page
                                logger.info(f"DEBUG: Extracted page_number={page_number} from chunk")
                            break

                # Get filepath and source_filename from chunk if available
                filepath = chunk.get("filepath", "")
                source_filename = chunk.get("source_filename", "")

                # Get chapter_number from chunk if not provided by LLM
                if not chapter_number:
                    chapter_number = chunk.get("chapter_number")
                    
                # Try to get page_number from chunk if still missing or 0
                if not page_number or page_number == 0:
                    chunk_page = chunk.get("chunk_start_page")
                    if chunk_page and chunk_page != 0:
                        page_number = chunk_page
                        logger.info(f"DEBUG: Using page_number={page_number} from chunk_start_page")

                # Use consistent source_filename from map if available
                if filename in source_filename_map:
                    source_filename = source_filename_map[filename]
                    logger.debug(
                        f"Using consistent source_filename '{source_filename}' for {filename}"
                    )

                # If no source_filename, try to derive from filename
                if not source_filename:
                    # Use filename without chapter prefix as fallback
                    source_filename = filename
                    logger.warning(
                        f"Missing source_filename for {filename}, using filename as fallback"
                    )

                # Create unique document name that includes chapter info to prevent overwriting
                # Use source_filename + chapter for uniqueness, but preserve source_filename for display
                if chapter_number:
                    doc_name = f"{source_filename}_Ch{chapter_number}"
                    # Also store a display-friendly version
                    display_name = f"{source_filename} - Chapter {chapter_number}"
                else:
                    # Fallback if no chapter number - use filename to ensure uniqueness
                    doc_name = (
                        f"{source_filename}_{filename}"
                        if source_filename != filename
                        else source_filename
                    )
                    display_name = source_filename

                # Initialize document entry if needed
                if doc_name not in structured_output:
                    structured_output[doc_name] = {
                        "_display_name": display_name  # Store display name for reference
                    }

                # Final validation of page_number - default to 1 if still invalid
                if not page_number or page_number == 0:
                    logger.warning(f"DEBUG: page_number still invalid ({page_number}), defaulting to 1")
                    page_number = 1
                
                # Create page key
                page_key = f"page_{page_number}"

                # Build full S3 link from filepath or use filename as fallback
                if filepath:
                    file_link = filepath  # Use full filepath from database
                else:
                    # Fallback to constructing from config S3_BASE_PATH
                    s3_base = (
                        getattr(config, "S3_BASE_PATH", "")
                        or "https://s3.amazonaws.com/your-bucket/"
                    )
                    file_link = f"{s3_base}{filename}" if s3_base else filename

                # Store in format compatible with model.py
                structured_output[doc_name][page_key] = {
                    "research_content": research_content,
                    "file_link": file_link,  # Full S3 link to chapter PDF
                    "file_name": filename,  # Chapter PDF filename
                    "page": page_number,  # Changed from page_number to page for model.py compatibility
                    "page_reference": page_reference
                    or str(page_number),  # For display text, fallback if missing
                    "chapter_number": chapter_number,  # For display in hyperlink
                    "source_filename": source_filename,  # Original document name for display
                    "chapter_name": chapter_name,  # Chapter name for additional context
                    "doc_name": doc_name,  # Document name for grouping
                }
                
                logger.info(
                    f"DEBUG: SUCCESSFULLY added page to output: {doc_name}/{page_key} - "
                    f"page={page_number}, page_reference={page_reference}"
                )
                processed_count += 1
            
            logger.info("=" * 80)
            logger.info("DEBUG: PROCESSING SUMMARY")
            logger.info("=" * 80)
            logger.info(f"DEBUG: Total page_research items from LLM: {len(page_research)}")
            logger.info(f"DEBUG: Successfully processed: {processed_count}")
            logger.info(f"DEBUG: Skipped (incomplete): {skipped_count}")
            logger.info(f"DEBUG: Final structured_output documents: {len(structured_output)}")
            
            # Count total pages in final output
            total_pages = sum(len([k for k in doc.keys() if k.startswith('page_')]) for doc in structured_output.values())
            logger.info(f"DEBUG: Total pages in final output: {total_pages}")
            
            # List all doc_names and their page counts
            for doc_name, doc_data in structured_output.items():
                page_count = len([k for k in doc_data.keys() if k.startswith('page_')])
                logger.info(f"DEBUG:   - {doc_name}: {page_count} pages")
            logger.info("=" * 80)

            logger.info(
                f"Built structured output from {len(page_research)} page findings for {len(structured_output)} documents"
            )

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
    logger.info(
        f"Querying {database_name}: '{query}' with scope: {scope}, type: {query_type}"
    )

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
                "status_summary": "❌ Embedding Generation Failed",
            }
            return (error_response, None, None, None, None, None)

        # Handle different scopes
        if scope == "metadata":
            # For metadata, return section summaries
            all_results = []

            if query_type == "multi_document":
                # Search each document separately
                for doc_id, k_value in documents.items():
                    results = _perform_vector_search(
                        cursor, query_embedding, k_value, doc_id
                    )
                    all_results.extend(results)
            else:
                # Single document search
                doc_id = list(documents.keys())[0] if documents else None
                k_value = list(documents.values())[0] if documents else INITIAL_K
                results = _perform_vector_search(
                    cursor, query_embedding, k_value, doc_id
                )
                all_results = results

            # Build metadata response
            metadata_response = []
            seen_sections = set()

            for chunk in all_results:
                section_key = (
                    chunk.get("document_id"),
                    chunk.get("chapter_number"),
                    chunk.get("section_number"),
                )

                if section_key not in seen_sections:
                    seen_sections.add(section_key)
                    metadata_response.append(
                        {
                            "id": chunk.get("id"),
                            "document_name": f"{chunk.get('chapter_name')} - Section {chunk.get('section_number')}",
                            "document_description": chunk.get("section_summary", ""),
                            "source": database_name,
                            "source_document_id": chunk.get("document_id"),
                        }
                    )

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
                    chunks = _perform_vector_search(
                        cursor, query_embedding, k_value, doc_id
                    )
                    initial_chunk_ids.extend(
                        [str(c.get("id")) for c in chunks if c.get("id")]
                    )

                    # Filter by relevance
                    relevant_chunks, filter_usage = _filter_by_relevance(
                        query, chunks, token
                    )
                    if filter_usage:
                        all_usage_details.append(filter_usage)

                    all_chunks.extend(relevant_chunks)
            else:
                # Single document processing
                doc_id = list(documents.keys())[0] if documents else None
                k_value = list(documents.values())[0] if documents else INITIAL_K

                chunks = _perform_vector_search(
                    cursor, query_embedding, k_value, doc_id
                )
                initial_chunk_ids = [str(c.get("id")) for c in chunks if c.get("id")]

                relevant_chunks, filter_usage = _filter_by_relevance(
                    query, chunks, token
                )
                if filter_usage:
                    all_usage_details.append(filter_usage)

                all_chunks = relevant_chunks

            if not all_chunks:
                return (
                    {
                        "detailed_research": "No relevant information found.",
                        "status_summary": "📄 No relevant information found",
                    },
                    initial_chunk_ids,
                    None,
                    all_usage_details,
                    None,
                )

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
                        result_count=len(initial_chunk_ids),
                    )
                if final_chunk_ids:
                    process_monitor.add_stage_details(
                        stage_name, final_document_ids=final_chunk_ids
                    )

            # For backward compatibility, create a simple response dict
            # The actual research is in the structured_output which goes in reference_index position
            response_dict = {
                "detailed_research": f"Found research from {len(structured_output)} documents",
                "status_summary": "✅ Research extracted",
            }

            return (
                response_dict,  # Simple response for compatibility
                initial_chunk_ids,
                None,  # file_links (not needed as they're in structured_output)
                None,  # page_section_refs
                None,  # section_content_map
                structured_output,  # This is the reference_index with page-based research (SAME FORMAT AS CATALOG SEARCH)
            )

        else:
            logger.error(f"Invalid scope: {scope}")
            return (
                {
                    "detailed_research": f"Invalid scope: {scope}",
                    "status_summary": "❌ Invalid Scope",
                },
                None,
                None,
                None,
                None,
                None,
            )

    except Exception as e:
        logger.error(f"Error in query_database_sync: {e}", exc_info=True)

        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=str(e))

        return (
            {
                "detailed_research": f"Error: {str(e)}",
                "status_summary": "❌ Query Error",
            },
            None,
            None,
            None,
            None,
            None,
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

        elapsed_time = time.time() - start_time
        logger.info(f"Query completed in {elapsed_time:.2f} seconds")
