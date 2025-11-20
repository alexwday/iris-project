# services/src/agents/database_subagents/semantic_search/subagent.py
"""
External Search Subagent (Unified External Database Handler)

Handles queries to external guidance content stored in the database,
supporting both single-document and multi-document search patterns.
Performs vector search, refinement, and response synthesis.

Functions:
    query_database_sync: Synchronously query external databases with configurable document settings
"""

import json
import logging
import os
import time
import traceback
import itertools
import yaml
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import psycopg2
import psycopg2.extras  # For DictCursor
from pgvector.psycopg2 import register_vector

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None
    print(
        "WARNING: tabulate not installed. Log tables will be basic."
        " `pip install tabulate`"
    )
# Removed tiktoken import attempt


from ....initial_setup.env_config import config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm

# Define response types consistent with database_router and catalog_search
MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
# Updated to match catalog_search return format with reference_index
FileLink = Dict[str, str]  # Contains file link info (not applicable for external)
PageSectionRefs = Dict[int, List[int]]  # Not used for external
SectionContentMap = Dict[str, str]  # Not used for external
ReferenceIndex = Dict[str, Dict[str, Any]]  # Maps reference ID to reference details
SubagentResult = Tuple[
    DatabaseResponse,
    Optional[List[str]],
    Optional[List[FileLink]],
    Optional[PageSectionRefs],
    Optional[SectionContentMap],
    Optional[ReferenceIndex],
]  # result + doc_ids + file_links + page_sections + section_content + reference_index

# Get module logger
logger = logging.getLogger(__name__)


def load_content_synthesis_config():
    """
    Load content synthesis configuration from YAML file.

    Returns:
        dict: Configuration with system prompt and settings
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "content_synthesis_prompt.yaml")

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Extract system prompt from YAML
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception(
                "No system_prompt found in semantic search content synthesis YAML configuration"
            )

        # No context replacement needed for content synthesis (focused extraction task)
        return yaml_config

    except Exception as e:
        logger.error(
            f"Failed to load semantic search content synthesis YAML config: {str(e)}"
        )
        raise


def get_content_synthesis_prompt(query: str, formatted_cards: str) -> str:
    """
    Generate a prompt for synthesizing content from IASB context cards using YAML config.

    Args:
        query (str): The user's original query
        formatted_cards (str): The string containing all context cards formatted for the LLM

    Returns:
        str: The formatted prompt for the LLM
    """
    config = load_content_synthesis_config()
    system_prompt = config.get("system_prompt", "")

    # Replace template variables
    system_prompt = system_prompt.replace("{{query}}", query)
    system_prompt = system_prompt.replace("{{formatted_cards}}", formatted_cards)

    return system_prompt


def get_synthesis_tool_schema() -> Dict[str, Any]:
    """
    Get the synthesis tool schema from YAML configuration.

    Returns:
        dict: Tool schema for content synthesis
    """
    config = load_content_synthesis_config()
    tools = config.get("tools", [])

    if not tools:
        raise Exception(
            "No tools found in semantic search content synthesis YAML configuration"
        )

    # Return the first tool (should be synthesize_research_findings)
    return tools[0]


# --- Configuration Constants ---
TARGET_TABLE = "iris_textbook_database"

# Model Capabilities
EMBEDDING_MODEL_CAPABILITY = "embedding"
RELEVANCE_MODEL_CAPABILITY = "small"
RESPONSE_MODEL_CAPABILITY = "large"

# Embedding Configuration
EMBEDDING_DIMENSIONS = 2000  # From example script

# Search & Refinement Configuration (from example script)
INITIAL_K = 20
IMPORTANCE_FACTOR = 0.2
SECTION_EXPANSION_TOP_K_RANK = 5
SECTION_EXPANSION_TOP_K_TOKENS = 8000
SECTION_EXPANSION_GENERAL_TOKENS = 4000
GAP_FILL_MAX_SEQUENCE_GAP = 8
MAX_RESPONSE_TOKENS = 32768
RESPONSE_TEMPERATURE = 0.7

# --- Helper Functions (Adapted from example.py) ---
# Removed Tokenizer Helper section

# Define type for LLM usage details
LlmUsageDetails = Optional[Dict[str, Any]]


def _generate_query_embedding(
    query: str, token: Optional[str] = None
) -> Tuple[Optional[List[float]], LlmUsageDetails]:
    """
    Generates embedding for the query string using call_llm.

    Args:
        query (str): The input query string to embed
        token (Optional[str]): OAuth token for API authentication

    Returns:
        Tuple[Optional[List[float]], LlmUsageDetails]: Embedding vector and usage details
    """
    logger.info(f"Generating embedding for query: '{query}'...")
    usage_details: LlmUsageDetails = None
    try:
        model_config = config.get_model_config(EMBEDDING_MODEL_CAPABILITY)
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        # Embeddings typically don't have completion cost, set to 0 or small value
        completion_cost = model_config.get("completion_token_cost", 0.0)

        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": prompt_cost,
            "completion_token_cost": completion_cost,
            "model": model_name,
            "input": [query],  # API expects a list
            "dimensions": EMBEDDING_DIMENSIONS,
            "database_name": "external_database",
            "is_embedding": True,  # Flag for call_llm
        }

        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result  # Assign usage_details here
            if usage_details:
                logger.debug(f"Embedding Usage details: {usage_details}")
        else:
            # For backward compatibility in case it doesn't return a tuple
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


def _perform_vector_search(
    cursor, query_embedding: List[float], initial_k: int, doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Performs vector search against the database, optionally filtering by document ID.

    Args:
        cursor: Database cursor with DictCursor factory
        query_embedding (List[float]): The query embedding vector
        initial_k (int): Number of top results to retrieve
        doc_id (Optional[str]): Document ID to filter by, if specified

    Returns:
        List[Dict[str, Any]]: List of search results with metadata and scores
    """
    log_doc_filter = f" filtering for document_id='{doc_id}'" if doc_id else ""
    logger.info(
        f"Performing Initial Vector Search (Retrieving Top {initial_k}){log_doc_filter}"
    )
    results_raw = []

    if query_embedding is None:
        logger.error("Cannot perform vector search without embedding.")
        return []

    try:
        # Vector search SQL with reference fields for REF:x generation
        sql = f"""
            SELECT
                c.id,
                c.content,
                c.document_id,
                c.section_start_page,
                c.chapter_name,
                c.section_title,
                c.section_hierarchy,
                c.chapter_number,
                c.section_number,
                c.part_number,
                c.sequence_number,
                c.section_importance_score,
                c.section_token_count,
                c.section_standard,
                c.section_standard_codes,
                c.chapter_tags,
                c.chapter_summary,
                1 - (c.embedding <=> %s::vector) AS vector_score -- Calculate vector score
            FROM {TARGET_TABLE} c
            WHERE 1=1
            {" AND c.document_id = %s" if doc_id else ""}
            ORDER BY vector_score DESC -- Order by vector score
            LIMIT %s;
        """
        params = [query_embedding]
        if doc_id:
            params.append(doc_id)
        params.append(initial_k)

        cursor.execute(sql, params)
        results_raw = cursor.fetchall()  # Returns list of DictRow objects
        logger.info(f"Found {len(results_raw)} results via vector search.")

        # Convert DictRow to dict and add initial rank
        results = []
        for i, row in enumerate(results_raw):
            record = dict(row)
            record["rank"] = i + 1  # Add rank based on initial vector score order
            results.append(record)
        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return []


def search_apg_catalog_by_embedding(
    research_statement: str, token: Optional[str] = None, top_k: int = 5
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
    logger.info(f"Searching apg_catalog for research statement: '{research_statement[:100]}...'")
    usage_details = None
    
    try:
        # Generate embedding for the research statement
        query_embedding, usage_details = _generate_query_embedding(research_statement, token)
        
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
        
        cursor.execute(sql, [query_embedding, top_k])
        results_raw = cursor.fetchall()
        
        # Convert to list of dictionaries
        results = []
        for i, row in enumerate(results_raw):
            record = dict(row)
            record["rank"] = i + 1
            results.append(record)
        
        logger.info(f"Found {len(results)} matching documents in apg_catalog")
        
        # Close database connection
        cursor.close()
        conn.close()
        
        return results, usage_details
        
    except Exception as e:
        logger.error(f"Error searching apg_catalog: {e}", exc_info=True)
        return [], usage_details


def _filter_by_summary_relevance(
    query: str, results: list[dict], token: Optional[str] = None
) -> Tuple[List[dict], dict, LlmUsageDetails]:
    """
    Uses LLM to classify chunk summaries as relevant or irrelevant to the query.

    Args:
        query (str): The original search query
        results (list[dict]): List of search results to filter
        token (Optional[str]): OAuth token for API authentication

    Returns:
        Tuple[List[dict], dict, LlmUsageDetails]: Filtered results, relevance mapping, and usage details
    """
    logger.info(
        f"Filtering {len(results)} results by summary relevance using {RELEVANCE_MODEL_CAPABILITY}"
    )
    usage_details: LlmUsageDetails = None
    if not results:
        return [], {}, usage_details

    summaries_data = []
    for i, record in enumerate(results):
        chunk_id = record.get("id")
        # WORKAROUND: Use 'chapter_summary' field which contains the section summary (as per example)
        summary = record.get("chapter_summary", "")
        if chunk_id and summary:
            summaries_data.append({"id": chunk_id, "summary": summary})
        else:
            logger.warning(
                f"Skipping result index {i} due to missing id or chapter_summary."
            )

    if not summaries_data:
        logger.warning("No valid summaries found for relevance check.")
        return results, {}, usage_details

    prompt_summaries = "\n".join(
        [
            f"ID: {item['id']}\nSummary: {item['summary']}\n---"
            for item in summaries_data
        ]  # No change needed here
    )

    system_message = """You are an assistant tasked with evaluating the relevance of text summaries to a user's query.
Analyze the user's query and each provided summary.
For each summary ID, determine if the summary is:
- Directly relevant or highly related to the query (output 1)
- Completely irrelevant or unrelated to the query (output 0)

Respond ONLY with a valid JSON object where keys are the summary IDs (as strings) and values are either 1 (relevant) or 0 (irrelevant).
Example response format: {"chunk_id_1": 1, "chunk_id_2": 0, "chunk_id_3": 1}
Do not include any explanations or introductory text outside the JSON object."""

    user_message = f"""User Query: "{query}"

Evaluate the relevance of the following summaries to the query:
---
{prompt_summaries}
---
Provide your response as a single JSON object mapping each ID to 1 (relevant) or 0 (irrelevant)."""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    relevance_map = {}
    try:
        model_config = config.get_model_config(RELEVANCE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "database_name": "external_database",
            "stream": False,  # Required for JSON mode
        }

        logger.info(
            f"Calling {RELEVANCE_MODEL_CAPABILITY} for summary relevance check..."
        )
        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result  # Assign usage_details here
            if usage_details:
                logger.debug(
                    f"Relevance Check Usage details for external_database: {usage_details}"
                )
        else:
            # For backward compatibility in case it doesn't return a tuple
            response = result
            logger.debug("call_llm did not return usage_details")

        if (
            response
            and hasattr(response, "choices")
            and response.choices
            and hasattr(response.choices[0], "message")
            and response.choices[0].message
            and hasattr(response.choices[0].message, "content")
            and response.choices[0].message.content
        ):
            response_content = response.choices[0].message.content
            try:
                relevance_map = json.loads(response_content)
                if not isinstance(relevance_map, dict) or not all(
                    isinstance(k, str) and v in [0, 1] for k, v in relevance_map.items()
                ):
                    raise ValueError(
                        "Invalid JSON format received from relevance check API."
                    )
                logger.info("Summary relevance check successful.")
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to decode JSON response from relevance check: {e}. Response: {response_content}",
                    exc_info=True,
                )
            except ValueError as e:
                logger.error(
                    f"Invalid JSON structure from relevance check: {e}. Response: {response_content}"
                )

        else:
            logger.error(
                "Invalid or empty response received from relevance check LLM.",
                extra={"api_response": response},
            )

    except Exception as e:
        logger.error(f"Error during relevance check LLM call: {e}", exc_info=True)

    # Filter results based on relevance map
    filtered_results = []
    removed_count = 0
    if relevance_map:  # Only filter if we got a map
        for record in results:
            chunk_id = record.get("id")
            # Default to relevant if ID wasn't processed or returned by GPT
            is_relevant = relevance_map.get(str(chunk_id), 1)
            if is_relevant == 1:
                filtered_results.append(record)
            else:
                removed_count += 1
                logger.debug(
                    f"Filtering out chunk ID {chunk_id} (summary deemed irrelevant)."
                )
        logger.info(
            f"Finished summary filtering. Kept {len(filtered_results)} results, removed {removed_count}."
        )
    else:
        logger.warning("Skipping summary filtering due to errors in relevance check.")
        filtered_results = results  # Return original results if API failed

    return filtered_results, relevance_map, usage_details


def _rerank_by_importance(results: list[dict], importance_factor: float) -> list[dict]:
    """
    Reranks search results by combining vector similarity and section importance scores.

    Args:
        results (list[dict]): List of search results to rerank
        importance_factor (float): Weight factor for importance scoring

    Returns:
        list[dict]: Reranked results with updated scores and rankings
    """
    logger.info(f"Reranking by Importance & Sorting (Factor: {importance_factor})")
    if not results:
        return []

    items_with_scores = []
    for item in results:
        if not isinstance(item, dict):
            logger.warning(f"Skipping unexpected item type in reranking: {type(item)}")
            continue

        new_score = 0.0
        original_score = item.get("vector_score", 0.0) or 0.0
        # Use section_importance_score from schema
        importance = item.get("section_importance_score", 0.0) or 0.0
        try:
            original_score = float(original_score)
            importance = float(importance)
            boost = 1.0 + (importance_factor * importance)
            new_score = original_score * boost
        except (TypeError, ValueError) as e:
            logger.warning(
                f"Could not calculate score for Chunk {item.get('id', 'N/A')} due to invalid numeric values. Setting new_score to 0. Error: {e}"
            )
            new_score = 0.0

        item["new_score"] = new_score
        items_with_scores.append(item)

    # Sort by new_score (descending), use original rank as tie-breaker (ascending)
    items_with_scores.sort(
        key=lambda x: (x.get("new_score", 0.0), -x.get("rank", float("inf"))),
        reverse=True,
    )

    # Assign new_rank and log
    rerank_log_data = []
    headers_rerank = [
        "New Rank",
        "Orig Rank",
        "Chunk ID",
        "Orig Score",
        "Importance",
        "New Score",
    ]
    final_reranked_list = []
    original_ranks = {
        item.get("id"): item.get("rank") for item in items_with_scores if item.get("id")
    }

    for new_rank, item in enumerate(items_with_scores, 1):
        item_id = item.get("id")
        orig_rank = original_ranks.get(item_id, "N/A")
        item["rank"] = new_rank  # Overwrite original rank
        final_reranked_list.append(item)
        rerank_log_data.append(
            [
                new_rank,
                orig_rank,
                item_id,
                f"{item.get('vector_score', 0.0):.4f}",
                f"{item.get('section_importance_score', 0.0):.2f}",
                f"{item.get('new_score', 0.0):.4f}",
            ]
        )

    logger.info(f"Finished reranking and sorting {len(final_reranked_list)} items.")
    if tabulate and rerank_log_data:
        logger.debug(
            "\n--- Importance Reranking Results ---\n"
            + tabulate(rerank_log_data, headers=headers_rerank, tablefmt="grid")
        )
    elif rerank_log_data:
        logger.debug("\n--- Importance Reranking Results ---")
        for row in rerank_log_data:
            logger.debug(
                f"NewRank: {row[0]}, OrigRank: {row[1]}, ID: {row[2]}, OrigScore: {row[3]}, Importance: {row[4]}, NewScore: {row[5]}"
            )

    return final_reranked_list


def _expand_sections_by_token_count(
    cursor, results: List[dict], top_k_rank: int, top_k_tokens: int, general_tokens: int
) -> Tuple[List[Union[dict, List[dict]]], set]:
    """
    Expands chunks belonging to sections below token thresholds by fetching all chunks for that section.
    Returns processed list (with groups) and set of added chunk IDs.
    """
    logger.info(
        f"Expanding sections by token count (Top {top_k_rank} < {top_k_tokens} tokens, Others < {general_tokens} tokens)"
    )
    if not results:
        return [], set()

    processed_results = []
    expansion_log_data = []
    headers_expansion = [
        "Orig Chunk ID",
        "Rank",
        "Section Tokens",
        "Threshold",
        "Action",
        "Added Chunks",
    ]
    added_chunk_ids = set()
    expanded_sections = set()  # Track section_key tuples

    for record in results:
        orig_chunk_id = record.get("id")
        doc_id = record.get("document_id")
        chapter = record.get("chapter_name")
        hierarchy = record.get("section_hierarchy")
        section_tokens = record.get("section_token_count")
        rank = record.get("rank")
        section_key = (doc_id, chapter, hierarchy)

        log_row = [
            orig_chunk_id or "N/A",
            rank or "N/A",
            section_tokens or "N/A",
            "N/A",
            "Keep Single",
            0,
        ]

        if section_key in expanded_sections:
            continue  # Skip if already expanded

        should_expand = False
        threshold = "N/A"
        if section_tokens is not None and rank is not None:
            is_top_k = rank <= top_k_rank
            threshold = top_k_tokens if is_top_k else general_tokens
            log_row[3] = threshold
            if section_tokens <= threshold:
                should_expand = True

        if should_expand:
            try:
                sql = f"""
                    SELECT * FROM {TARGET_TABLE}
                    WHERE document_id = %s AND chapter_name = %s AND section_hierarchy = %s
                    ORDER BY sequence_number;
                """
                cursor.execute(sql, (doc_id, chapter, hierarchy))
                section_chunks_raw = cursor.fetchall()
                num_found = len(section_chunks_raw)

                if num_found > 1:
                    section_chunks = [dict(chunk) for chunk in section_chunks_raw]
                    group_info = {
                        "type": "group",
                        "original_rank": rank,
                        "original_vector_score": record.get("vector_score"),
                        "section_importance_score": record.get(
                            "section_importance_score"
                        ),
                        "new_score": record.get("new_score", 0.0),
                        "chunks": section_chunks,
                        "document_id": doc_id,
                        "chapter_name": chapter,
                        "section_hierarchy": hierarchy,
                        "min_seq": (
                            section_chunks[0].get("sequence_number")
                            if section_chunks
                            else None
                        ),
                    }
                    processed_results.append(group_info)
                    expanded_sections.add(section_key)
                    log_row[4] = f"Expand Group ({num_found} total)"
                    log_row[5] = num_found - 1
                    for chunk in section_chunks:
                        chunk_id = chunk.get("id")
                        if chunk_id and chunk_id != orig_chunk_id:
                            added_chunk_ids.add(chunk_id)
                else:
                    processed_results.append(record)
                    log_row[4] = "Keep Single (1 in DB)"
                    log_row[5] = 0
            except Exception as e:
                logger.error(
                    f"Failed to fetch/process expansion for section {section_key}: {e}",
                    exc_info=True,
                )
                processed_results.append(record)
                log_row[4] = "Error - Keep Single"
                log_row[5] = 0
        else:
            processed_results.append(record)

        expansion_log_data.append(log_row)

    if tabulate and expansion_log_data:
        logger.debug(
            "\n--- Section Expansion Log ---\n"
            + tabulate(expansion_log_data, headers=headers_expansion, tablefmt="grid")
        )
    elif expansion_log_data:
        logger.debug("\n--- Section Expansion Log ---")
        for row in expansion_log_data:
            logger.debug(
                f"ID: {row[0]}, Rank: {row[1]}, Tokens: {row[2]}, Threshold: {row[3]}, Action: {row[4]}, Added: {row[5]}"
            )

    logger.info(
        f"Finished section expansion. Intermediate count: {len(processed_results)}. Added {len(added_chunk_ids)} new chunks."
    )

    # --- Second Pass: Filter out single chunks now contained within groups ---
    final_processed_results = []
    grouped_chunk_ids = set()
    for item in processed_results:
        if isinstance(item, dict) and item.get("type") == "group":
            for chunk in item.get("chunks", []):
                if chunk.get("id"):
                    grouped_chunk_ids.add(chunk.get("id"))

    skipped_singles = 0
    for item in processed_results:
        if isinstance(item, dict) and item.get("type") == "group":
            final_processed_results.append(item)
        elif isinstance(item, dict):
            chunk_id = item.get("id")
            if chunk_id in grouped_chunk_ids:
                logger.debug(
                    f"Filtering out single chunk ID {chunk_id} (Rank: {item.get('rank', 'N/A')}) included in group."
                )
                skipped_singles += 1
            else:
                final_processed_results.append(item)
        else:
            logger.warning(
                f"Unexpected item type during final expansion filtering: {type(item)}"
            )
            final_processed_results.append(item)

    logger.info(
        f"Finished filtering expanded singles. Removed {skipped_singles}. Final count: {len(final_processed_results)}"
    )
    return final_processed_results, added_chunk_ids


def _fill_sequence_gaps(
    cursor, results: List[Union[dict, List[dict]]], max_seq_gap: int
) -> Tuple[List[Union[dict, List[dict]]], set]:
    """
    Identifies and fills small sequence number gaps between consecutive results.
    Returns updated list and set of added chunk IDs.
    """
    logger.info(f"Filling sequence gaps (Max Gap: {max_seq_gap} sequences)")
    if len(results) < 2:
        return results, set()

    items_with_sequences = []
    gap_log_data = []
    headers_gaps = [
        "Between Item (Seq)",
        "And Item (Seq)",
        "Sequence Gap",
        "Action",
        "Added Chunks",
    ]
    added_chunk_ids = set()

    for item in results:
        if isinstance(item, dict) and item.get("type") == "group":
            if not item.get("chunks"):
                continue
            first_chunk = item["chunks"][0]
            last_chunk = item["chunks"][-1]
            doc_id = first_chunk.get("document_id")
            min_seq = first_chunk.get("sequence_number")
            max_seq = last_chunk.get("sequence_number")
            if all(v is not None for v in [doc_id, min_seq, max_seq]):
                items_with_sequences.append(
                    {
                        "item": item,
                        "doc_id": doc_id,
                        "min_seq": min_seq,
                        "max_seq": max_seq,
                        "is_group": True,
                        "id_repr": f"Group({min_seq}-{max_seq})",
                    }
                )
        elif isinstance(item, dict):
            doc_id = item.get("document_id")
            seq = item.get("sequence_number")
            chunk_id = item.get("id")
            if all(v is not None for v in [doc_id, seq]):
                items_with_sequences.append(
                    {
                        "item": item,
                        "doc_id": doc_id,
                        "min_seq": seq,
                        "max_seq": seq,
                        "is_group": False,
                        "id_repr": f"Chunk({chunk_id})",
                    }
                )

    if len(items_with_sequences) < 2:
        logger.debug("Not enough items with sequence numbers to check for gaps.")
        return results, set()

    items_with_sequences.sort(key=lambda x: x["min_seq"])

    final_results_with_gaps = []
    last_item_info = None

    for current_item_info in items_with_sequences:
        if last_item_info and last_item_info["doc_id"] == current_item_info["doc_id"]:
            seq_gap = current_item_info["min_seq"] - last_item_info["max_seq"] - 1
            log_row = [
                f"{last_item_info['id_repr']} ({last_item_info['max_seq']})",
                f"{current_item_info['id_repr']} ({current_item_info['min_seq']})",
                seq_gap,
                "None",
                0,
            ]

            if 0 < seq_gap <= max_seq_gap:
                try:
                    sql = f"""
                        SELECT * FROM {TARGET_TABLE}
                        WHERE document_id = %s AND sequence_number > %s AND sequence_number < %s
                        ORDER BY sequence_number;
                    """
                    cursor.execute(
                        sql,
                        (
                            current_item_info["doc_id"],
                            last_item_info["max_seq"],
                            current_item_info["min_seq"],
                        ),
                    )
                    gap_chunks_raw = cursor.fetchall()
                    num_added = len(gap_chunks_raw)
                    if num_added > 0:
                        preceding_score = (
                            last_item_info.get("item", {}).get("new_score", 0.0) or 0.0
                        )
                        following_score = (
                            current_item_info.get("item", {}).get("new_score", 0.0)
                            or 0.0
                        )
                        average_score = (preceding_score + following_score) / 2.0

                        gap_chunks = []
                        for chunk_raw in gap_chunks_raw:
                            chunk = dict(chunk_raw)
                            chunk["new_score"] = average_score
                            gap_chunks.append(chunk)
                            if chunk.get("id"):
                                added_chunk_ids.add(chunk.get("id"))

                        final_results_with_gaps.extend(gap_chunks)
                        log_row[3] = (
                            f"Fill Gap ({num_added} chunks, Avg Score ~{average_score:.4f})"
                        )
                        log_row[4] = num_added
                    else:
                        log_row[3] = "No Chunks Found"
                        log_row[4] = 0
                except Exception as e:
                    logger.error(
                        f"Failed to fetch/process gap fill between seq {last_item_info['max_seq']} and {current_item_info['min_seq']}: {e}",
                        exc_info=True,
                    )
                    log_row[3] = "Error Fetching"
                    log_row[4] = 0
            elif seq_gap > max_seq_gap:
                log_row[3] = f"Gap > {max_seq_gap}"
            else:
                log_row[3] = "No Gap / Overlap"
            gap_log_data.append(log_row)

        final_results_with_gaps.append(current_item_info["item"])
        last_item_info = current_item_info

    if tabulate and gap_log_data:
        logger.debug(
            "\n--- Sequence Gap Filling Log ---\n"
            + tabulate(gap_log_data, headers=headers_gaps, tablefmt="grid")
        )
    elif gap_log_data:
        logger.debug("\n--- Sequence Gap Filling Log ---")
        for row in gap_log_data:
            logger.debug(
                f"Between: {row[0]}, And: {row[1]}, Seq Gap: {row[2]}, Action: {row[3]}, Added: {row[4]}"
            )

    logger.info(
        f"Finished sequence gap filling. Result count: {len(final_results_with_gaps)}. Added {len(added_chunk_ids)} new chunks."
    )
    return final_results_with_gaps, added_chunk_ids


def _build_reference_index(
    results: List[Union[dict, List[dict]]], query: str
) -> ReferenceIndex:
    """
    Build reference index from processed results for REF:x generation.

    Args:
        results: List of processed chunks/groups with reference metadata
        query: The original query for context

    Returns:
        ReferenceIndex: Structured reference data like catalog_search
    """
    logger.info(f"Building reference index from {len(results)} processed items")
    reference_index: ReferenceIndex = {}

    for item in results:
        if isinstance(item, dict) and item.get("type") == "group":
            # Handle grouped chunks
            chunks = item.get("chunks", [])
            if not chunks:
                continue

            # Use the first chunk's document info for the group
            first_chunk = chunks[0]
            doc_id = first_chunk.get("document_id")
            if not doc_id:
                continue

            if doc_id not in reference_index:
                reference_index[doc_id] = {}

            # Process each chunk in the group
            for chunk in chunks:
                page_num = chunk.get("section_start_page")
                if page_num is None:
                    continue

                page_key = f"page_{page_num}"

                # Build research content from chunk
                research_content = _build_research_content_from_chunk(chunk, query)

                reference_index[doc_id][page_key] = {
                    "research_content": research_content,
                    "document_source": doc_id,  # This matches file_name for external
                    "page_number": page_num,
                    "file_link": "",  # External sources don't have file links
                    "file_name": doc_id,  # Use document_id as file_name for consistency
                    "chapter_name": chunk.get("chapter_name", ""),
                    "section_title": chunk.get("section_title", ""),
                    "section_hierarchy": chunk.get("section_hierarchy", ""),
                }

        elif isinstance(item, dict):
            # Handle single chunks
            doc_id = item.get("document_id")
            page_num = item.get("section_start_page")

            if not doc_id or page_num is None:
                continue

            if doc_id not in reference_index:
                reference_index[doc_id] = {}

            page_key = f"page_{page_num}"

            # Build research content from chunk
            research_content = _build_research_content_from_chunk(item, query)

            reference_index[doc_id][page_key] = {
                "research_content": research_content,
                "document_source": doc_id,  # This matches file_name for external
                "page_number": page_num,
                "file_link": "",  # External sources don't have file links
                "file_name": doc_id,  # Use document_id as file_name for consistency
                "chapter_name": item.get("chapter_name", ""),
                "section_title": item.get("section_title", ""),
                "section_hierarchy": item.get("section_hierarchy", ""),
            }

    logger.info(f"Built reference index with {len(reference_index)} documents")
    return reference_index


def _build_research_content_from_chunk(chunk: Dict[str, Any], query: str) -> str:
    """
    Build research content from a single chunk for reference index.

    Args:
        chunk: Single chunk data with content and metadata
        query: Original query for context

    Returns:
        str: Formatted research content for this chunk
    """
    content = chunk.get("content", "")
    chapter_name = chunk.get("chapter_name", "")
    section_title = chunk.get("section_title", "")
    section_hierarchy = chunk.get("section_hierarchy", "")

    # Create a concise research content entry
    research_parts = []

    if section_title and section_title != chapter_name:
        research_parts.append(f"**{section_title}**")
    elif chapter_name:
        research_parts.append(f"**{chapter_name}**")

    if section_hierarchy:
        research_parts.append(f"*{section_hierarchy}*")

    # Add a portion of the content (truncated for reference purposes)
    if content:
        # Take first 500 characters for reference content
        truncated_content = content[:500] + "..." if len(content) > 500 else content
        research_parts.append(truncated_content)

    return "\n\n".join(research_parts)


def _format_chunks_as_cards(results: List[Union[dict, List[dict]]]) -> str:
    """Formats final results (chunks and groups) into cards for the LLM."""
    logger.info("Formatting Final Results as Cards for LLM")
    cards = []
    final_item_count = 0
    # Removed token counting initialization

    # Sort results by sequence number before formatting
    # Use a helper to get the minimum sequence number for sorting
    def get_min_sequence(item):
        if isinstance(item, dict) and item.get("type") == "group":
            try:
                return min(
                    c.get("sequence_number")
                    for c in item.get("chunks", [])
                    if c.get("sequence_number") is not None
                )
            except (ValueError, TypeError):
                return float("inf")
        elif isinstance(item, dict):
            return item.get("sequence_number", float("inf"))
        return float("inf")

    try:
        # Filter out items without sequence numbers before sorting
        items_to_sort = [
            item for item in results if get_min_sequence(item) != float("inf")
        ]
        items_without_sequence = [
            item for item in results if get_min_sequence(item) == float("inf")
        ]
        if items_without_sequence:
            logger.warning(
                f"Found {len(items_without_sequence)} items without sequence numbers, placing them at the end."
            )

        items_to_sort.sort(key=get_min_sequence)
        sorted_results = items_to_sort + items_without_sequence
    except Exception as sort_err:
        logger.error(
            f"Error sorting results before formatting: {sort_err}. Proceeding with unsorted results.",
            exc_info=True,
        )
        sorted_results = results  # Fallback to unsorted

    for i, item in enumerate(sorted_results):
        card_parts = []
        content_parts = []
        record_for_metadata = None
        # Removed item_token_count initialization

        if isinstance(item, dict) and item.get("type") == "group":
            if not item.get("chunks"):
                continue
            record_for_metadata = item["chunks"][0]
            card_parts.append(f"--- CARD {i+1} (Reconstructed Section) ---")
            for chunk in item["chunks"]:
                content = chunk.get("content", "")
                content_parts.append(content)
                # Removed token counting call
            content = "\n\n".join(filter(None, content_parts))
            logger.debug(
                f"Formatting Card {i+1}: Group of {len(item['chunks'])} chunks (Section: {record_for_metadata.get('section_hierarchy', 'N/A')})"
            )

        elif isinstance(item, dict):
            record_for_metadata = item
            card_parts.append(f"--- CARD {i+1} ---")
            content = record_for_metadata.get("content", "")
            # Removed token counting call
            logger.debug(
                f"Formatting Card {i+1}: Single Chunk ID {record_for_metadata.get('id', 'N/A')}"
            )
        else:
            logger.warning(
                f"Skipping unexpected item type during formatting: {type(item)}"
            )
            continue

        if not record_for_metadata or not content:
            logger.warning(f"Skipping Card {i+1} due to missing metadata or content.")
            continue

        # Extract and format required fields
        doc_id = record_for_metadata.get(
            "document_id", "Unknown Document"
        )  # Get doc ID
        chapter_name = record_for_metadata.get("chapter_name", "Unknown Chapter")
        section_title = record_for_metadata.get("section_title", "Unknown Section")
        section_hierarchy = record_for_metadata.get("section_hierarchy", "")
        standard = record_for_metadata.get("section_standard")  # Use section_standard
        standard_codes = record_for_metadata.get(
            "section_standard_codes"
        )  # Use section_standard_codes
        tags = record_for_metadata.get("chapter_tags")  # Use chapter_tags

        card_parts.append(f"Source Document ID: {doc_id}")  # Add Source Document ID
        card_parts.append(f"Chapter: {chapter_name}")
        card_parts.append(f"Section Title: {section_title}")
        if section_hierarchy:
            card_parts.append(f"Section Hierarchy: {section_hierarchy}")
        if standard:
            card_parts.append(f"Standard: {standard}")
        if standard_codes and isinstance(standard_codes, list) and standard_codes:
            card_parts.append(f"Standard Codes: {', '.join(standard_codes)}")
        if tags and isinstance(tags, list) and tags:
            card_parts.append(f"Chapter Tags: {', '.join(tags)}")

        card_parts.append("\nContent:")
        card_parts.append(content)

        cards.append("\n".join(card_parts))
        final_item_count += 1
        # Removed token counting accumulation

    logger.info(f"Formatted {final_item_count} cards.")  # Removed token count from log
    return "\n\n" + "\n\n".join(cards) + "\n\n"


def _generate_response_from_chunks(
    query: str, formatted_chunks: str, token: Optional[str] = None
) -> Tuple[ResearchResponse, LlmUsageDetails]:
    """
    Generates a response using LLM tool call based on the query and formatted chunks.
    Returns the response dictionary and usage details.
    """
    logger.info(
        f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}"
    )
    usage_details: LlmUsageDetails = None
    # Get the system prompt from YAML and substitute variables
    synthesis_system_prompt = get_content_synthesis_prompt(query, formatted_chunks)
    default_response = {
        "detailed_research": "Error: Failed to generate synthesized response.",
        "status_summary": "❌ Synthesis Error",
    }

    try:
        model_config = config.get_model_config(RESPONSE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": [
                {"role": "system", "content": synthesis_system_prompt},
                {
                    "role": "user",
                    "content": "Please analyze the provided IASB context cards and generate the research synthesis using the synthesize_research_findings tool.",
                },
            ],
            "max_tokens": MAX_RESPONSE_TOKENS,
            "temperature": RESPONSE_TEMPERATURE,
            "tools": [get_synthesis_tool_schema()],
            "tool_choice": {
                "type": "function",
                "function": {"name": get_synthesis_tool_schema()["function"]["name"]},
            },
            "database_name": "external_database",
            "stream": False,  # Tool calls require stream=False
        }

        logger.info(
            f"Calling {RESPONSE_MODEL_CAPABILITY} for final response synthesis..."
        )
        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result  # Assign usage_details here
            if usage_details:
                logger.debug(f"Synthesis Usage details: {usage_details}")
        else:
            # For backward compatibility in case it doesn't return a tuple
            response = result
            logger.debug("call_llm did not return usage_details")

        # Process Tool Call Response
        if (
            response
            and hasattr(response, "choices")
            and response.choices
            and hasattr(response.choices[0], "message")
            and response.choices[0].message
            and hasattr(response.choices[0].message, "tool_calls")
            and response.choices[0].message.tool_calls
        ):
            tool_call = response.choices[0].message.tool_calls[0]
            synthesis_tool_schema = get_synthesis_tool_schema()
            if tool_call.function.name == synthesis_tool_schema["function"]["name"]:
                arguments_str = tool_call.function.arguments
                logger.debug(f"Received tool arguments string: {arguments_str}")
                try:
                    arguments = json.loads(arguments_str)
                    # Check for the CORRECT key name 'detailed_research_report'
                    if (
                        "status_summary" in arguments
                        and "detailed_research_report" in arguments
                    ):
                        logger.info(
                            f"Successfully parsed synthesis tool call for external_database."
                        )
                        # Validate types
                        status = arguments.get("status_summary", "")
                        # Extract using the CORRECT key name 'detailed_research_report'
                        research_report = arguments.get("detailed_research_report", "")
                        if not isinstance(status, str):
                            status = str(status)  # Coerce
                        if not isinstance(research_report, str):
                            research_report = str(research_report)  # Coerce
                        # Return using the key 'detailed_research' as expected by the Summarizer/Router
                        return {
                            "detailed_research": research_report,  # Use the expected output key
                            "status_summary": status,
                        }, usage_details
                    else:
                        logger.error(
                            f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}"
                        )
                        return default_response, usage_details
                except json.JSONDecodeError as json_err:
                    logger.error(
                        f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}"
                    )
                    return default_response, usage_details
            else:
                logger.error(f"Unexpected tool called: {tool_call.function.name}")
                return default_response, usage_details
        else:
            # Handle case where LLM might return content instead of tool call
            content = ""
            if (
                response
                and hasattr(response, "choices")
                and response.choices
                and hasattr(response.choices[0], "message")
                and response.choices[0].message
                and hasattr(response.choices[0].message, "content")
                and response.choices[0].message.content
            ):
                content = response.choices[0].message.content
                logger.warning(
                    f"LLM returned content instead of tool call: {content[:200]}..."
                )
                return {
                    "detailed_research": f"LLM returned text instead of structured output:\n{content}",
                    "status_summary": "⚠️ LLM Response Format Issue",
                }, usage_details
            else:
                logger.error("No tool call or content received from LLM for synthesis.")
                return default_response, usage_details

    except Exception as e:
        logger.error(f"Exception during final response synthesis: {e}", exc_info=True)
        return default_response, usage_details


# --- Helper: Process Single Document ID ---


def _process_single_document_id(
    cursor,
    query: str,
    query_embedding: List[float],
    doc_id: str,
    initial_k: int,
    token: Optional[str] = None,
) -> Tuple[List[Union[dict, List[dict]]], Optional[List[str]], List[LlmUsageDetails]]:
    """
    Runs the search and refinement pipeline for a single document ID.
    Returns the list of processed chunks/groups, the final chunk IDs for this doc,
    and collected usage details for this document ID.
    """
    logger.info(f"--- Processing Document ID: {doc_id} (Initial K: {initial_k}) ---")
    processed_results = []  # Initialize empty list for this doc ID
    final_chunk_ids_for_doc: Optional[List[str]] = None  # Added
    usage_details_for_doc: List[LlmUsageDetails] = []  # Collect usage for this doc

    try:
        # 1. Initial Vector Search for this doc_id
        initial_results = _perform_vector_search(
            cursor, query_embedding, initial_k, doc_id=doc_id
        )
        if not initial_results:
            logger.info(f"No initial results found for {doc_id}.")
            return [], None, usage_details_for_doc  # Return empty list if no results

        processed_results = initial_results
        all_added_chunk_ids = set()  # Track added chunks for this doc_id run

        # 2. Summary Relevance Filtering
        filtered_results, _, relevance_usage = _filter_by_summary_relevance(
            query, processed_results, token
        )
        if relevance_usage:
            usage_details_for_doc.append(relevance_usage)
        if not filtered_results:
            logger.info(f"No relevant results after filtering for {doc_id}.")
            return [], None, usage_details_for_doc  # Return empty list
        processed_results = filtered_results

        # 3. Importance Reranking
        reranked_results = _rerank_by_importance(processed_results, IMPORTANCE_FACTOR)
        processed_results = reranked_results

        # 4. Section Expansion
        expanded_results, added_by_expansion = _expand_sections_by_token_count(
            cursor,
            processed_results,
            SECTION_EXPANSION_TOP_K_RANK,
            SECTION_EXPANSION_TOP_K_TOKENS,
            SECTION_EXPANSION_GENERAL_TOKENS,
        )
        if not expanded_results:
            logger.info(f"No results after section expansion for {doc_id}.")
            return [], None, usage_details_for_doc  # Return empty list
        all_added_chunk_ids.update(added_by_expansion)
        processed_results = expanded_results

        # 5. Sequence Gap Filling
        filled_results, added_by_gaps = _fill_sequence_gaps(
            cursor, processed_results, GAP_FILL_MAX_SEQUENCE_GAP
        )
        if not filled_results:
            logger.info(f"No results after gap filling for {doc_id}.")
            return [], None, usage_details_for_doc  # Return empty list
        all_added_chunk_ids.update(added_by_gaps)
        processed_results = filled_results

        # --- Extract Final Chunk IDs for this doc ---
        final_chunk_ids_for_doc = []
        for item in processed_results:
            if isinstance(item, dict) and item.get("type") == "group":
                for chunk in item.get("chunks", []):
                    if chunk.get("id"):
                        final_chunk_ids_for_doc.append(str(chunk.get("id")))
            elif isinstance(item, dict) and item.get("id"):
                final_chunk_ids_for_doc.append(str(item.get("id")))
        logger.info(
            f"Collected {len(final_chunk_ids_for_doc)} final chunk IDs for doc {doc_id}."
        )

        # Steps 6 & 7 (Format Cards, Generate Response) are moved to the main logic function

    except Exception as e:
        # Log error specific to this document ID processing
        logger.error(f"Error processing document ID {doc_id}: {e}", exc_info=True)
        # Return empty list on error during processing for this doc ID
        return [], None, usage_details_for_doc

    logger.info(
        f"--- Finished Processing Document ID: {doc_id} - Found {len(processed_results)} items ---"
    )
    # Return processed results, final IDs for this doc, and usage
    return processed_results, final_chunk_ids_for_doc, usage_details_for_doc


# --- Logic Function (Handles Core Query Processing) ---

# Define return type for logic function to include usage details and both initial/final chunk IDs plus reference index
LogicResult = Tuple[
    DatabaseResponse,
    Optional[List[str]],
    Optional[List[str]],
    List[LlmUsageDetails],
    Optional[ReferenceIndex],
]


def _query_database_logic(
    query: str, scope: str, document_config: Dict[str, Any], token: Optional[str] = None
) -> LogicResult:
    """
    Internal logic for external database queries with configurable document settings.
    Returns the database response, list of initial chunk IDs, list of final chunk IDs,
    collected LLM usage details, and reference index.
    """
    # Extract documents dict and derive database name for logging
    documents = document_config.get("documents", {})
    database_name = list(documents.keys())[0].split("_")[0] if documents else "external"

    default_error_status = f"❌ Error processing {database_name} query."
    default_no_info_status = f"📄 No relevant information found in {database_name}."
    default_research = f"No detailed research generated for {database_name}."
    initial_chunk_ids: Optional[List[str]] = None  # For combined initial IDs
    final_chunk_ids: Optional[List[str]] = None  # For combined final IDs
    all_usage_details: List[LlmUsageDetails] = []

    conn = None
    cursor = None

    # --- Database Connection & Embedding ---
    try:
        conn = connect_to_db()
        if not conn:
            raise ConnectionError("Failed to connect to the database.")
        register_vector(conn)
        logger.info("Database connection successful and pgvector registered.")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        query_embedding, embed_usage = _generate_query_embedding(query, token)
        if embed_usage:
            all_usage_details.append(embed_usage)

        if query_embedding is None:
            # Handle embedding failure based on scope
            if scope == "metadata":
                return (
                    [],
                    None,
                    None,
                    all_usage_details,
                    None,
                )  # Add None for reference_index
            else:  # research scope
                error_response = {
                    "detailed_research": "Could not generate embedding for the query.",
                    "status_summary": "❌ Embedding Generation Failed",
                }
                return (
                    error_response,
                    None,
                    None,
                    all_usage_details,
                    None,
                )  # Add None for reference_index

        # --- Metadata Scope Handling ---
        if scope == "metadata":
            logger.info(f"Processing '{scope}' scope for {database_name}")
            all_initial_results = []
            initial_chunk_ids = []  # Collect combined initial IDs
            # Perform vector search for each configured IASB document ID
            for doc_id, k_value in documents.items():
                logger.info(
                    f"Performing metadata vector search for {doc_id} (k={k_value})"
                )
                initial_results_for_doc = _perform_vector_search(
                    cursor, query_embedding, k_value, doc_id=doc_id
                )
                # --- Capture Initial IDs for this doc ---
                if initial_results_for_doc:
                    ids_for_doc = [
                        str(item.get("id"))
                        for item in initial_results_for_doc
                        if item.get("id")
                    ]
                    initial_chunk_ids.extend(ids_for_doc)
                all_initial_results.extend(initial_results_for_doc)

            if not all_initial_results:
                logger.info(
                    f"No initial vector search results for metadata query across all IASB sources."
                )
                return (
                    [],
                    None,
                    None,
                    all_usage_details,
                    None,
                )  # Return empty list, no IDs, usage, no refs

            unique_sections = {}
            # No separate metadata_chunk_ids needed, using combined initial_chunk_ids
            for record in all_initial_results:
                doc_id = record.get("document_id")
                chapter = record.get("chapter_name")
                hierarchy = record.get("section_hierarchy")
                title = record.get("section_title")
                summary = record.get("chapter_summary")  # Contains section summary
                chunk_id = record.get("id")

                if not all([doc_id, chapter, hierarchy, title, summary, chunk_id]):
                    logger.warning(
                        f"Skipping record due to missing fields: {record.get('id')}"
                    )
                    continue

                section_key = (doc_id, chapter, hierarchy)
                if section_key not in unique_sections:
                    unique_sections[section_key] = {
                        "id": chunk_id,  # Use first chunk ID found for this section
                        "title": title,
                        "summary": summary,
                        "doc_id": doc_id,  # Keep original doc_id for source_document_id
                    }
                    # metadata_chunk_ids.append(chunk_id) # No longer needed

            metadata_response: MetadataResponse = []
            for section_data in unique_sections.values():
                metadata_response.append(
                    {
                        "id": section_data["id"],
                        "document_name": section_data[
                            "title"
                        ],  # Use section title as name
                        "document_description": section_data[
                            "summary"
                        ],  # Use section summary as description
                        "source": database_name,
                        "source_document_id": section_data[
                            "doc_id"
                        ],  # Add the original document ID
                    }
                )

            logger.info(
                f"Returning {len(metadata_response)} unique sections for metadata scope from {database_name}."
            )
            # Return metadata, the combined *initial* chunk IDs (final IDs not applicable), and usage details
            return (
                metadata_response,
                initial_chunk_ids,
                None,
                all_usage_details,
                None,
            )  # No reference_index for metadata scope

        # --- Research Scope Handling ---
        elif scope == "research":
            logger.info(f"Processing '{scope}' scope for {database_name}")
            final_research_result: ResearchResponse = {
                "detailed_research": default_research,
                "status_summary": default_error_status,
            }

            all_processed_results = []  # Store processed results from all doc IDs
            initial_chunk_ids = []  # Store combined initial IDs
            final_chunk_ids = []  # Store combined final IDs

            # Process each Document ID defined in document_config
            for doc_id, k_value in documents.items():
                # --- Get Initial IDs for this doc ---
                initial_results_for_doc = _perform_vector_search(
                    cursor, query_embedding, k_value, doc_id=doc_id
                )
                if initial_results_for_doc:
                    ids_for_doc = [
                        str(item.get("id"))
                        for item in initial_results_for_doc
                        if item.get("id")
                    ]
                    initial_chunk_ids.extend(ids_for_doc)
                    logger.info(
                        f"Captured {len(ids_for_doc)} initial chunk IDs for doc {doc_id} (research scope)."
                    )

                # --- Process this doc (relevance, rerank, expand, gap fill) ---
                # Now returns processed chunks, final IDs for this doc, AND usage details
                processed_chunks_for_doc, final_ids_for_doc, usage_for_doc = (
                    _process_single_document_id(
                        cursor, query, query_embedding, doc_id, k_value, token
                    )
                )
                all_processed_results.extend(processed_chunks_for_doc)
                if final_ids_for_doc:
                    final_chunk_ids.extend(final_ids_for_doc)  # Collect final IDs
                all_usage_details.extend(usage_for_doc)  # Collect usage details

            # Check if any results were found across all documents
            if not all_processed_results:
                logger.info(
                    f"No relevant information found across any IASB document sources for query: '{query}'"
                )
                final_research_result["status_summary"] = default_no_info_status
                final_research_result["detailed_research"] = (
                    "No relevant information found across any IASB document sources."
                )
                # Return early, include the (potentially empty) initial IDs
                return (
                    final_research_result,
                    initial_chunk_ids,
                    None,
                    all_usage_details,
                    None,
                )  # No reference_index when no results
            else:
                # Log combined counts
                logger.info(
                    f"Collected {len(initial_chunk_ids)} total initial chunk IDs for research scope across all IASB sources."
                )
                logger.info(
                    f"Collected {len(final_chunk_ids)} total final chunk IDs for research scope across all IASB sources."
                )

                # Build reference index from processed results
                logger.info(
                    f"Building reference index from {len(all_processed_results)} processed items."
                )
                reference_index = _build_reference_index(all_processed_results, query)

                # Format combined chunks into cards
                logger.info(
                    f"Formatting combined {len(all_processed_results)} processed items from all IASB sources."
                )
                formatted_chunks = _format_chunks_as_cards(all_processed_results)

                # Generate ONE final response from the combined cards
                final_research_result, synthesis_usage = _generate_response_from_chunks(
                    query, formatted_chunks, token
                )
                if synthesis_usage:
                    all_usage_details.append(synthesis_usage)

                # Return the final research result, the combined *initial* IDs, the combined *final* IDs, usage details, and reference index
                return (
                    final_research_result,
                    initial_chunk_ids,
                    final_chunk_ids,
                    all_usage_details,
                    reference_index,
                )

        else:
            # Invalid scope handling
            logger.error(
                f"Invalid scope '{scope}' provided to {database_name} subagent."
            )
            if scope == "metadata":
                return [], None, None, all_usage_details, None
            else:
                error_response = {
                    "detailed_research": f"Invalid scope '{scope}' provided.",
                    "status_summary": "❌ Invalid Scope",
                }
                return error_response, None, None, all_usage_details, None

    except psycopg2.Error as db_err:
        logger.error(
            f"Database error during {database_name} query (Scope: {scope}): {db_err}",
            exc_info=True,
        )
        if conn:
            conn.rollback()
        if scope == "metadata":
            return [], None, None, all_usage_details, None
        else:
            error_response = {
                "detailed_research": f"**Database Error:** {str(db_err)}",
                "status_summary": "❌ Database Error",
            }
            return error_response, None, None, all_usage_details, None
    except ConnectionError as conn_err:
        logger.error(
            f"Connection error for {database_name} (Scope: {scope}): {conn_err}",
            exc_info=True,
        )
        if scope == "metadata":
            return [], None, None, all_usage_details, None
        else:
            error_response = {
                "detailed_research": f"**Connection Error:** {str(conn_err)}",
                "status_summary": "❌ DB Connection Error",
            }
            return error_response, None, None, all_usage_details, None
    except Exception as e:
        logger.error(
            f"Unexpected error querying {database_name} database (Scope: {scope}): {e}",
            exc_info=True,
        )
        if conn:
            conn.rollback()
        if scope == "metadata":
            return [], None, None, all_usage_details, None
        else:
            error_response = {
                "detailed_research": f"**Unexpected Error:** {str(e)}",
                "status_summary": default_error_status,
            }
            return error_response, None, None, all_usage_details, None
    finally:
        # Ensure connection is closed even if early returns happened
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed.")

    # Fallback return (should not be reached ideally)
    logger.error(
        f"Reached end of _query_database_logic unexpectedly for scope '{scope}' in {database_name}."
    )
    if scope == "metadata":
        return [], None, None, all_usage_details, None
    else:
        error_response = {
            "detailed_research": "Reached end of logic function unexpectedly.",
            "status_summary": "❌ Unexpected Flow",
        }
        return error_response, None, None, all_usage_details, None


# --- Main Function ---


def query_database_sync(
    query: str,
    scope: str,
    document_config: Dict[str, Any],
    token: Optional[str] = None,
    process_monitor=None,
    query_stage_name: Optional[str] = None,
    research_statement: Optional[str] = None,
) -> SubagentResult:  # Added document_config parameter
    """
    Synchronously query external databases with configurable document settings. Handles 'metadata' and 'research' scopes.

    Args:
        query (str): The search query to execute.
        scope (str): The scope of the query ('metadata' or 'research').
        document_config (Dict[str, Any]): Configuration specifying query_type and documents with their k-values.
        token (str, optional): Authentication token for API access.
        process_monitor: Optional process monitor to track token usage.
        query_stage_name (str, optional): The specific stage name for this query instance
                                          provided by the caller (e.g., worker).
        research_statement (str, optional): Research statement for similarity search context.

    Returns:
        SubagentResult: Tuple containing:
            - DatabaseResponse: Query results, either MetadataResponse or ResearchResponse.
            - Optional[List[str]]: List of chunk IDs used in the search, or None.
    """
    start_time = time.time()
    # Extract documents dict from config for logging
    documents = document_config.get("documents", {})
    database_name = (
        list(documents.keys())[0].split("_")[0] if documents else "external"
    )  # Derive name from first document
    logger.info(f"Querying {database_name} database: '{query}' with scope: {scope}")
    # Use the passed-in stage name if available, otherwise default (though it should always be passed now)
    stage_name = query_stage_name or f"db_query_{database_name}_unknown"
    logger.debug(f"Using process monitor stage name: {stage_name}")
    result: DatabaseResponse = {} if scope == "research" else []  # Initialize result
    initial_chunk_ids: Optional[List[str]] = None
    final_chunk_ids: Optional[List[str]] = None  # Added final_chunk_ids
    all_usage_details: List[LlmUsageDetails] = []
    reference_index: Optional[ReferenceIndex] = None  # Added reference_index

    # REMOVED: Stage start is now handled by the caller (_execute_query_worker)
    # if process_monitor:
    #     process_monitor.start_stage(stage_name)
    #     # Add initial details like scope and query
    #     process_monitor.add_stage_details(stage_name, scope=scope, query=query)

    try:
        # Call the logic function which now returns result, initial_ids, final_ids, usage_details, and reference_index
        (
            result,
            initial_chunk_ids,
            final_chunk_ids,
            all_usage_details,
            reference_index,
        ) = _query_database_logic(query, scope, document_config, token)

        # Process collected usage details if monitor is enabled
        if process_monitor and all_usage_details:
            for usage in all_usage_details:
                if usage:  # Ensure usage is not None
                    try:
                        # Add each LLM call's details to the monitor stage
                        process_monitor.add_llm_call_details_to_stage(stage_name, usage)
                    except Exception as monitor_err:
                        logger.error(
                            f"Error adding LLM usage details to process monitor for stage {stage_name}: {monitor_err}",
                            exc_info=True,
                        )

        # Add final details (like initial/final chunk IDs or status) to the monitor stage
        # Use the specific stage_name passed from the worker
        if process_monitor:
            details_to_add = {}
            if initial_chunk_ids:
                details_to_add["initial_document_ids"] = initial_chunk_ids  # New key
                details_to_add["result_count"] = len(
                    initial_chunk_ids
                )  # Keep overall count based on initial
            if final_chunk_ids:
                details_to_add["final_document_ids"] = final_chunk_ids  # New key
            if scope == "research" and isinstance(result, dict):
                details_to_add["status_summary"] = result.get("status_summary", "N/A")
            elif scope == "metadata" and isinstance(result, list):
                # result_count already added if chunk_ids exist
                pass  # No specific status for metadata usually

            if details_to_add:
                process_monitor.add_stage_details(stage_name, **details_to_add)

    except Exception as e:
        logger.error(
            f"Error during {database_name} query execution: {str(e)}", exc_info=True
        )
        # Ensure result is set to an error state if not already
        if scope == "research" and not (
            isinstance(result, dict)
            and result.get("status_summary", "").startswith("❌")
        ):
            result = {
                "detailed_research": f"**Unhandled Error:** {str(e)}",
                "status_summary": "❌ Unhandled Error",
            }
        elif scope == "metadata":
            result = []  # Return empty list on error for metadata

        # Add error details to process monitor
        # Use the specific stage_name passed from the worker
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=str(e))
            # REMOVED: Stage end (even for errors) is now handled by the caller (_execute_query_worker)
            # process_monitor.end_stage(stage_name, status="error")

        # Re-raise the exception? Or return the error result?
        # Current structure returns the error result. If re-raise is needed, uncomment below:
        # raise

    finally:
        # REMOVED: Stage end is now handled by the caller (_execute_query_worker)
        # if process_monitor and process_monitor.stages.get(stage_name) and process_monitor.stages[stage_name].status == "in_progress":
        #     process_monitor.end_stage(stage_name) # Default status is 'completed'

        try:
            # Force garbage collection to clean up any unreferenced connections
            import gc
            gc.collect()
        except Exception as gc_exc:
            logger.warning(f"Error during garbage collection in {database_name}: {gc_exc}")

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"{database_name} query completed in {duration:.2f} seconds.")

    # Return the result and all components to match catalog_search format
    return (
        result,
        initial_chunk_ids,
        None,  # file_links (not applicable for external)
        None,  # page_section_refs (not used for external)
        None,  # section_content_map (not used for external)
        reference_index,  # reference_index for REF:x generation
    )
