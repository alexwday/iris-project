# external_iasb/subagent.py
"""
External IASB Guidance Subagent

Handles queries to the IASB guidance content stored in the database,
performing vector search, refinement, and response synthesis.

Functions:
    query_database_sync: Synchronously query the IASB guidance database
"""

import json
import logging
import time
import traceback
import itertools
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


from ....chat_model.model_settings import ENVIRONMENT, get_model_config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm
from .content_synthesis_prompt import (
    get_content_synthesis_prompt,
    SYNTHESIS_TOOL_SCHEMA,
)

# Define response types consistent with database_router
MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
SubagentResult = Tuple[DatabaseResponse, Optional[List[str]]]  # Define a tuple for result + doc_ids

# Get module logger
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
DATABASE_NAME = "external_iasb"
TARGET_TABLE = "iris_textbook_database"

# IASB Document IDs and their respective Initial K values
IASB_DOC_CONFIG = {
    "iasb_ias": 20,    # International Accounting Standards
    "iasb_ifrs": 20,   # International Financial Reporting Standards
    "iasb_ifrics": 10, # IFRS Interpretations Committee Interpretations
    "iasb_sic": 10,    # Standards Interpretations Committee Interpretations
}

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
MAX_RESPONSE_TOKENS = 4000
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
    Returns the embedding and usage details.
    """
    logger.info(f"Generating embedding for query: '{query}'...")
    usage_details: LlmUsageDetails = None
    try:
        model_config = get_model_config(EMBEDDING_MODEL_CAPABILITY)
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
            "database_name": DATABASE_NAME,
            "is_embedding": True,  # Flag for call_llm
        }

        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result # Assign usage_details here
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
        logger.error(
            f"Failed to generate embedding: {e}", exc_info=True
        )
        return None, usage_details


def _perform_vector_search(
    cursor, query_embedding: List[float], initial_k: int, doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Performs vector search, optionally filtering by a specific document ID.
    Returns a list of results as dictionaries.
    """
    log_doc_filter = f" filtering for document_id='{doc_id}'" if doc_id else ""
    logger.info(f"Performing Initial Vector Search (Retrieving Top {initial_k}){log_doc_filter}")
    results_raw = []

    if query_embedding is None:
        logger.error("Cannot perform vector search without embedding.")
        return []

    try:
        # Vector-only search SQL
        sql = f"""
            SELECT
                c.*, -- Select all columns from the target table
                1 - (c.embedding <=> %s::vector) AS vector_score -- Calculate vector score
            FROM {TARGET_TABLE} c -- Removed quotes, no longer needed
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
        results_raw = cursor.fetchall() # Returns list of DictRow objects
        logger.info(f"Found {len(results_raw)} results via vector search.")

        # Convert DictRow to dict and add initial rank
        results = []
        for i, row in enumerate(results_raw):
            record = dict(row)
            record['rank'] = i + 1 # Add rank based on initial vector score order
            results.append(record)
        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        return []


def _filter_by_summary_relevance(
    query: str, results: list[dict], token: Optional[str] = None
) -> Tuple[List[dict], dict, LlmUsageDetails]:
    """
    Uses LLM via call_llm to classify chunk summaries as relevant (1) or irrelevant (0).
    Filters out irrelevant chunks. Returns filtered list, relevance map, and usage details.
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
        [f"ID: {item['id']}\nSummary: {item['summary']}\n---" for item in summaries_data] # No change needed here
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
        model_config = get_model_config(RELEVANCE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "database_name": DATABASE_NAME,
            "stream": False, # Required for JSON mode
        }

        logger.info(f"Calling {RELEVANCE_MODEL_CAPABILITY} for summary relevance check...")
        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result # Assign usage_details here
            if usage_details:
                logger.debug(f"Relevance Check Usage details for {DATABASE_NAME}: {usage_details}")
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
                    raise ValueError("Invalid JSON format received from relevance check API.")
                logger.info("Summary relevance check successful.")
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to decode JSON response from relevance check: {e}. Response: {response_content}",
                    exc_info=True
                )
            except ValueError as e:
                 logger.error(f"Invalid JSON structure from relevance check: {e}. Response: {response_content}")

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
    if relevance_map: # Only filter if we got a map
        for record in results:
            chunk_id = record.get("id")
            # Default to relevant if ID wasn't processed or returned by GPT
            is_relevant = relevance_map.get(str(chunk_id), 1)
            if is_relevant == 1:
                filtered_results.append(record)
            else:
                removed_count += 1
                logger.info(f"Filtering out chunk ID {chunk_id} (summary deemed irrelevant).")
        logger.info(f"Finished summary filtering. Kept {len(filtered_results)} results, removed {removed_count}.")
    else:
        logger.warning("Skipping summary filtering due to errors in relevance check.")
        filtered_results = results # Return original results if API failed

    return filtered_results, relevance_map, usage_details


def _rerank_by_importance(
    results: list[dict], importance_factor: float
) -> list[dict]:
    """
    Calculates 'new_score' based on vector score and section importance,
    sorts by new score, assigns 'new_rank'. Handles only single chunks.
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
    headers_rerank = ["New Rank", "Orig Rank", "Chunk ID", "Orig Score", "Importance", "New Score"]
    final_reranked_list = []
    original_ranks = {item.get('id'): item.get('rank') for item in items_with_scores if item.get('id')}

    for new_rank, item in enumerate(items_with_scores, 1):
        item_id = item.get('id')
        orig_rank = original_ranks.get(item_id, 'N/A')
        item['rank'] = new_rank # Overwrite original rank
        final_reranked_list.append(item)
        rerank_log_data.append([
            new_rank,
            orig_rank,
            item_id,
            f"{item.get('vector_score', 0.0):.4f}",
            f"{item.get('section_importance_score', 0.0):.2f}",
            f"{item.get('new_score', 0.0):.4f}"
        ])

    logger.info(f"Finished reranking and sorting {len(final_reranked_list)} items.")
    if tabulate and rerank_log_data:
        logger.info("\n--- Importance Reranking Results ---\n" + tabulate(rerank_log_data, headers=headers_rerank, tablefmt="grid"))
    elif rerank_log_data:
         logger.info("\n--- Importance Reranking Results ---")
         for row in rerank_log_data: logger.info(f"NewRank: {row[0]}, OrigRank: {row[1]}, ID: {row[2]}, OrigScore: {row[3]}, Importance: {row[4]}, NewScore: {row[5]}")

    return final_reranked_list


def _expand_sections_by_token_count(
    cursor, results: List[dict], top_k_rank: int, top_k_tokens: int, general_tokens: int
) -> Tuple[List[Union[dict, List[dict]]], set]:
    """
    Expands chunks belonging to sections below token thresholds by fetching all chunks for that section.
    Returns processed list (with groups) and set of added chunk IDs.
    """
    logger.info(f"Expanding sections by token count (Top {top_k_rank} < {top_k_tokens} tokens, Others < {general_tokens} tokens)")
    if not results: return [], set()

    processed_results = []
    expansion_log_data = []
    headers_expansion = ["Orig Chunk ID", "Rank", "Section Tokens", "Threshold", "Action", "Added Chunks"]
    added_chunk_ids = set()
    expanded_sections = set() # Track section_key tuples

    for record in results:
        orig_chunk_id = record.get('id')
        doc_id = record.get('document_id')
        chapter = record.get('chapter_name')
        hierarchy = record.get('section_hierarchy')
        section_tokens = record.get('section_token_count')
        rank = record.get('rank')
        section_key = (doc_id, chapter, hierarchy)

        log_row = [orig_chunk_id or "N/A", rank or "N/A", section_tokens or "N/A", "N/A", "Keep Single", 0]

        if section_key in expanded_sections:
            continue # Skip if already expanded

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
                        'type': 'group',
                        'original_rank': rank,
                        'original_vector_score': record.get('vector_score'),
                        'section_importance_score': record.get('section_importance_score'),
                        'new_score': record.get('new_score', 0.0),
                        'chunks': section_chunks,
                        'document_id': doc_id,
                        'chapter_name': chapter,
                        'section_hierarchy': hierarchy,
                        'min_seq': section_chunks[0].get('sequence_number') if section_chunks else None
                    }
                    processed_results.append(group_info)
                    expanded_sections.add(section_key)
                    log_row[4] = f"Expand Group ({num_found} total)"
                    log_row[5] = num_found - 1
                    for chunk in section_chunks:
                        chunk_id = chunk.get('id')
                        if chunk_id and chunk_id != orig_chunk_id:
                             added_chunk_ids.add(chunk_id)
                else:
                    processed_results.append(record)
                    log_row[4] = "Keep Single (1 in DB)"
                    log_row[5] = 0
            except Exception as e:
                logger.error(f"Failed to fetch/process expansion for section {section_key}: {e}", exc_info=True)
                processed_results.append(record)
                log_row[4] = "Error - Keep Single"
                log_row[5] = 0
        else:
            processed_results.append(record)

        expansion_log_data.append(log_row)

    if tabulate and expansion_log_data:
        logger.info("\n--- Section Expansion Log ---\n" + tabulate(expansion_log_data, headers=headers_expansion, tablefmt="grid"))
    elif expansion_log_data:
        logger.info("\n--- Section Expansion Log ---")
        for row in expansion_log_data: logger.info(f"ID: {row[0]}, Rank: {row[1]}, Tokens: {row[2]}, Threshold: {row[3]}, Action: {row[4]}, Added: {row[5]}")

    logger.info(f"Finished section expansion. Intermediate count: {len(processed_results)}. Added {len(added_chunk_ids)} new chunks.")

    # --- Second Pass: Filter out single chunks now contained within groups ---
    final_processed_results = []
    grouped_chunk_ids = set()
    for item in processed_results:
        if isinstance(item, dict) and item.get('type') == 'group':
            for chunk in item.get('chunks', []):
                if chunk.get('id'): grouped_chunk_ids.add(chunk.get('id'))

    skipped_singles = 0
    for item in processed_results:
        if isinstance(item, dict) and item.get('type') == 'group':
            final_processed_results.append(item)
        elif isinstance(item, dict):
            chunk_id = item.get('id')
            if chunk_id in grouped_chunk_ids:
                logger.debug(f"Filtering out single chunk ID {chunk_id} (Rank: {item.get('rank', 'N/A')}) included in group.")
                skipped_singles += 1
            else:
                final_processed_results.append(item)
        else:
             logger.warning(f"Unexpected item type during final expansion filtering: {type(item)}")
             final_processed_results.append(item)

    logger.info(f"Finished filtering expanded singles. Removed {skipped_singles}. Final count: {len(final_processed_results)}")
    return final_processed_results, added_chunk_ids


def _fill_sequence_gaps(
    cursor, results: List[Union[dict, List[dict]]], max_seq_gap: int
) -> Tuple[List[Union[dict, List[dict]]], set]:
    """
    Identifies and fills small sequence number gaps between consecutive results.
    Returns updated list and set of added chunk IDs.
    """
    logger.info(f"Filling sequence gaps (Max Gap: {max_seq_gap} sequences)")
    if len(results) < 2: return results, set()

    items_with_sequences = []
    gap_log_data = []
    headers_gaps = ["Between Item (Seq)", "And Item (Seq)", "Sequence Gap", "Action", "Added Chunks"]
    added_chunk_ids = set()

    for item in results:
        if isinstance(item, dict) and item.get('type') == 'group':
            if not item.get('chunks'): continue
            first_chunk = item['chunks'][0]
            last_chunk = item['chunks'][-1]
            doc_id = first_chunk.get('document_id')
            min_seq = first_chunk.get('sequence_number')
            max_seq = last_chunk.get('sequence_number')
            if all(v is not None for v in [doc_id, min_seq, max_seq]):
                items_with_sequences.append({
                    'item': item, 'doc_id': doc_id, 'min_seq': min_seq, 'max_seq': max_seq,
                    'is_group': True, 'id_repr': f"Group({min_seq}-{max_seq})"
                })
        elif isinstance(item, dict):
             doc_id = item.get('document_id')
             seq = item.get('sequence_number')
             chunk_id = item.get('id')
             if all(v is not None for v in [doc_id, seq]):
                 items_with_sequences.append({
                    'item': item, 'doc_id': doc_id, 'min_seq': seq, 'max_seq': seq,
                    'is_group': False, 'id_repr': f"Chunk({chunk_id})"
                 })

    if len(items_with_sequences) < 2:
        logger.info("Not enough items with sequence numbers to check for gaps.")
        return results, set()

    items_with_sequences.sort(key=lambda x: x['min_seq'])

    final_results_with_gaps = []
    last_item_info = None

    for current_item_info in items_with_sequences:
        if last_item_info and last_item_info['doc_id'] == current_item_info['doc_id']:
            seq_gap = current_item_info['min_seq'] - last_item_info['max_seq'] - 1
            log_row = [f"{last_item_info['id_repr']} ({last_item_info['max_seq']})", f"{current_item_info['id_repr']} ({current_item_info['min_seq']})", seq_gap, "None", 0]

            if 0 < seq_gap <= max_seq_gap:
                try:
                    sql = f"""
                        SELECT * FROM {TARGET_TABLE}
                        WHERE document_id = %s AND sequence_number > %s AND sequence_number < %s
                        ORDER BY sequence_number;
                    """
                    cursor.execute(sql, (current_item_info['doc_id'], last_item_info['max_seq'], current_item_info['min_seq']))
                    gap_chunks_raw = cursor.fetchall()
                    num_added = len(gap_chunks_raw)
                    if num_added > 0:
                        preceding_score = last_item_info.get('item', {}).get('new_score', 0.0) or 0.0
                        following_score = current_item_info.get('item', {}).get('new_score', 0.0) or 0.0
                        average_score = (preceding_score + following_score) / 2.0

                        gap_chunks = []
                        for chunk_raw in gap_chunks_raw:
                            chunk = dict(chunk_raw)
                            chunk['new_score'] = average_score
                            gap_chunks.append(chunk)
                            if chunk.get('id'): added_chunk_ids.add(chunk.get('id'))

                        final_results_with_gaps.extend(gap_chunks)
                        log_row[3] = f"Fill Gap ({num_added} chunks, Avg Score ~{average_score:.4f})"
                        log_row[4] = num_added
                    else:
                        log_row[3] = "No Chunks Found"
                        log_row[4] = 0
                except Exception as e:
                    logger.error(f"Failed to fetch/process gap fill between seq {last_item_info['max_seq']} and {current_item_info['min_seq']}: {e}", exc_info=True)
                    log_row[3] = "Error Fetching"
                    log_row[4] = 0
            elif seq_gap > max_seq_gap:
                 log_row[3] = f"Gap > {max_seq_gap}"
            else:
                 log_row[3] = "No Gap / Overlap"
            gap_log_data.append(log_row)

        final_results_with_gaps.append(current_item_info['item'])
        last_item_info = current_item_info

    if tabulate and gap_log_data:
        logger.info("\n--- Sequence Gap Filling Log ---\n" + tabulate(gap_log_data, headers=headers_gaps, tablefmt="grid"))
    elif gap_log_data:
        logger.info("\n--- Sequence Gap Filling Log ---")
        for row in gap_log_data: logger.info(f"Between: {row[0]}, And: {row[1]}, Seq Gap: {row[2]}, Action: {row[3]}, Added: {row[4]}")

    logger.info(f"Finished sequence gap filling. Result count: {len(final_results_with_gaps)}. Added {len(added_chunk_ids)} new chunks.")
    return final_results_with_gaps, added_chunk_ids


def _format_chunks_as_cards(results: List[Union[dict, List[dict]]]) -> str:
    """Formats final results (chunks and groups) into cards for the LLM."""
    logger.info("Formatting Final Results as Cards for LLM")
    cards = []
    final_item_count = 0
    # Removed token counting initialization

    # Sort results by sequence number before formatting
    # Use a helper to get the minimum sequence number for sorting
    def get_min_sequence(item):
        if isinstance(item, dict) and item.get('type') == 'group':
            try: return min(c.get('sequence_number') for c in item.get('chunks', []) if c.get('sequence_number') is not None)
            except (ValueError, TypeError): return float('inf')
        elif isinstance(item, dict): return item.get('sequence_number', float('inf'))
        return float('inf')

    try:
        # Filter out items without sequence numbers before sorting
        items_to_sort = [item for item in results if get_min_sequence(item) != float('inf')]
        items_without_sequence = [item for item in results if get_min_sequence(item) == float('inf')]
        if items_without_sequence:
            logger.warning(f"Found {len(items_without_sequence)} items without sequence numbers, placing them at the end.")

        items_to_sort.sort(key=get_min_sequence)
        sorted_results = items_to_sort + items_without_sequence
    except Exception as sort_err:
        logger.error(f"Error sorting results before formatting: {sort_err}. Proceeding with unsorted results.", exc_info=True)
        sorted_results = results # Fallback to unsorted

    for i, item in enumerate(sorted_results):
        card_parts = []
        content_parts = []
        record_for_metadata = None
        # Removed item_token_count initialization

        if isinstance(item, dict) and item.get('type') == 'group':
            if not item.get('chunks'): continue
            record_for_metadata = item['chunks'][0]
            card_parts.append(f"--- CARD {i+1} (Reconstructed Section) ---")
            for chunk in item['chunks']:
                 content = chunk.get('content', '')
                 content_parts.append(content)
                 # Removed token counting call
            content = "\n\n".join(filter(None, content_parts))
            logger.debug(f"Formatting Card {i+1}: Group of {len(item['chunks'])} chunks (Section: {record_for_metadata.get('section_hierarchy', 'N/A')})")

        elif isinstance(item, dict):
             record_for_metadata = item
             card_parts.append(f"--- CARD {i+1} ---")
             content = record_for_metadata.get('content', '')
             # Removed token counting call
             logger.debug(f"Formatting Card {i+1}: Single Chunk ID {record_for_metadata.get('id', 'N/A')}")
        else:
            logger.warning(f"Skipping unexpected item type during formatting: {type(item)}")
            continue

        if not record_for_metadata or not content:
            logger.warning(f"Skipping Card {i+1} due to missing metadata or content.")
            continue

        # Extract and format required fields
        doc_id = record_for_metadata.get('document_id', 'Unknown Document') # Get doc ID
        chapter_name = record_for_metadata.get('chapter_name', 'Unknown Chapter')
        section_title = record_for_metadata.get('section_title', 'Unknown Section')
        section_hierarchy = record_for_metadata.get('section_hierarchy', '')
        standard = record_for_metadata.get('section_standard') # Use section_standard
        standard_codes = record_for_metadata.get('section_standard_codes') # Use section_standard_codes
        tags = record_for_metadata.get('chapter_tags') # Use chapter_tags

        card_parts.append(f"Source Document ID: {doc_id}") # Add Source Document ID
        card_parts.append(f"Chapter: {chapter_name}")
        card_parts.append(f"Section Title: {section_title}")
        if section_hierarchy: card_parts.append(f"Section Hierarchy: {section_hierarchy}")
        if standard: card_parts.append(f"Standard: {standard}")
        if standard_codes and isinstance(standard_codes, list) and standard_codes:
            card_parts.append(f"Standard Codes: {', '.join(standard_codes)}")
        if tags and isinstance(tags, list) and tags:
             card_parts.append(f"Chapter Tags: {', '.join(tags)}")

        card_parts.append("\nContent:")
        card_parts.append(content)

        cards.append("\n".join(card_parts))
        final_item_count += 1
        # Removed token counting accumulation

    logger.info(f"Formatted {final_item_count} cards.") # Removed token count from log
    return "\n\n" + "\n\n".join(cards) + "\n\n"


def _generate_response_from_chunks(
    query: str, formatted_chunks: str, token: Optional[str] = None
) -> Tuple[ResearchResponse, LlmUsageDetails]:
    """
    Generates a response using LLM tool call based on the query and formatted chunks.
    Returns the response dictionary and usage details.
    """
    logger.info(f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}")
    usage_details: LlmUsageDetails = None
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_chunks)
    default_response = {
        "detailed_research": "Error: Failed to generate synthesized response.",
        "status_summary": "❌ Synthesis Error",
    }

    try:
        model_config = get_model_config(RESPONSE_MODEL_CAPABILITY)
        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": model_config["prompt_token_cost"],
            "completion_token_cost": model_config["completion_token_cost"],
            "model": model_config["name"],
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."}, # System prompt defined in get_content_synthesis_prompt
                {"role": "user", "content": synthesis_prompt},
            ],
            "max_tokens": MAX_RESPONSE_TOKENS,
            "temperature": RESPONSE_TEMPERATURE,
            "tools": [SYNTHESIS_TOOL_SCHEMA],
            "tool_choice": {
                "type": "function",
                "function": {"name": SYNTHESIS_TOOL_SCHEMA["function"]["name"]},
            },
            "database_name": DATABASE_NAME,
            "stream": False, # Tool calls require stream=False
        }

        logger.info(f"Calling {RESPONSE_MODEL_CAPABILITY} for final response synthesis...")
        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result # Assign usage_details here
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
            if tool_call.function.name == SYNTHESIS_TOOL_SCHEMA["function"]["name"]:
                arguments_str = tool_call.function.arguments
                logger.debug(f"Received tool arguments string: {arguments_str}")
                try:
                    arguments = json.loads(arguments_str)
                    # Check for the CORRECT key name 'detailed_research_report'
                    if "status_summary" in arguments and "detailed_research_report" in arguments:
                        logger.info(f"Successfully parsed synthesis tool call for {DATABASE_NAME}.")
                        # Validate types
                        status = arguments.get("status_summary", "")
                        # Extract using the CORRECT key name 'detailed_research_report'
                        research_report = arguments.get("detailed_research_report", "")
                        if not isinstance(status, str): status = str(status) # Coerce
                        if not isinstance(research_report, str): research_report = str(research_report) # Coerce
                        # Return using the key 'detailed_research' as expected by the Summarizer/Router
                        return {
                            "detailed_research": research_report, # Use the expected output key
                            "status_summary": status,
                        }, usage_details
                    else:
                        logger.error(f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}")
                        return default_response, usage_details
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}")
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
                logger.warning(f"LLM returned content instead of tool call: {content[:200]}...")
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
    processed_results = [] # Initialize empty list for this doc ID
    final_chunk_ids_for_doc: Optional[List[str]] = None # Added
    usage_details_for_doc: List[LlmUsageDetails] = [] # Collect usage for this doc

    try:
        # 1. Initial Vector Search for this doc_id
        initial_results = _perform_vector_search(
            cursor, query_embedding, initial_k, doc_id=doc_id
        )
        if not initial_results:
            logger.info(f"No initial results found for {doc_id}.")
            return [], None, usage_details_for_doc # Return empty list if no results

        processed_results = initial_results
        all_added_chunk_ids = set() # Track added chunks for this doc_id run

        # 2. Summary Relevance Filtering
        filtered_results, _, relevance_usage = _filter_by_summary_relevance(query, processed_results, token)
        if relevance_usage: usage_details_for_doc.append(relevance_usage)
        if not filtered_results:
            logger.info(f"No relevant results after filtering for {doc_id}.")
            return [], None, usage_details_for_doc # Return empty list
        processed_results = filtered_results

        # 3. Importance Reranking
        reranked_results = _rerank_by_importance(processed_results, IMPORTANCE_FACTOR)
        processed_results = reranked_results

        # 4. Section Expansion
        expanded_results, added_by_expansion = _expand_sections_by_token_count(
            cursor, processed_results, SECTION_EXPANSION_TOP_K_RANK, SECTION_EXPANSION_TOP_K_TOKENS, SECTION_EXPANSION_GENERAL_TOKENS
        )
        if not expanded_results:
             logger.info(f"No results after section expansion for {doc_id}.")
             return [], None, usage_details_for_doc # Return empty list
        all_added_chunk_ids.update(added_by_expansion)
        processed_results = expanded_results

        # 5. Sequence Gap Filling
        filled_results, added_by_gaps = _fill_sequence_gaps(
            cursor, processed_results, GAP_FILL_MAX_SEQUENCE_GAP
        )
        if not filled_results:
             logger.info(f"No results after gap filling for {doc_id}.")
             return [], None, usage_details_for_doc # Return empty list
        all_added_chunk_ids.update(added_by_gaps)
        processed_results = filled_results

        # --- Extract Final Chunk IDs for this doc ---
        final_chunk_ids_for_doc = []
        for item in processed_results:
            if isinstance(item, dict) and item.get('type') == 'group':
                for chunk in item.get('chunks', []):
                    if chunk.get('id'): final_chunk_ids_for_doc.append(str(chunk.get('id')))
            elif isinstance(item, dict) and item.get('id'):
                final_chunk_ids_for_doc.append(str(item.get('id')))
        logger.info(f"Collected {len(final_chunk_ids_for_doc)} final chunk IDs for doc {doc_id}.")

        # Steps 6 & 7 (Format Cards, Generate Response) are moved to the main logic function

    except Exception as e:
        # Log error specific to this document ID processing
        logger.error(f"Error processing document ID {doc_id}: {e}", exc_info=True)
        # Return empty list on error during processing for this doc ID
        return [], None, usage_details_for_doc

    logger.info(f"--- Finished Processing Document ID: {doc_id} - Found {len(processed_results)} items ---")
    # Return processed results, final IDs for this doc, and usage
    return processed_results, final_chunk_ids_for_doc, usage_details_for_doc


# --- Logic Function (Handles Core Query Processing) ---

# Define return type for logic function to include usage details and both initial/final chunk IDs
LogicResult = Tuple[DatabaseResponse, Optional[List[str]], Optional[List[str]], List[LlmUsageDetails]]

def _query_database_logic(
    query: str, scope: str, token: Optional[str] = None
) -> LogicResult:
    """
    Internal logic for the IASB subagent query.
    Returns the database response, list of initial chunk IDs, list of final chunk IDs,
    and collected LLM usage details.
    """
    default_error_status = f"❌ Error processing {DATABASE_NAME} query."
    default_no_info_status = f"📄 No relevant information found in {DATABASE_NAME}."
    default_research = f"No detailed research generated for {DATABASE_NAME}."
    initial_chunk_ids: Optional[List[str]] = None # For combined initial IDs
    final_chunk_ids: Optional[List[str]] = None # For combined final IDs
    all_usage_details: List[LlmUsageDetails] = []

    conn = None
    cursor = None

    # --- Database Connection & Embedding ---
    try:
        conn = connect_to_db(ENVIRONMENT)
        if not conn:
            raise ConnectionError("Failed to connect to the database.")
        register_vector(conn)
        logger.info("Database connection successful and pgvector registered.")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        query_embedding, embed_usage = _generate_query_embedding(query, token)
        if embed_usage: all_usage_details.append(embed_usage)

        if query_embedding is None:
            # Handle embedding failure based on scope
            if scope == "metadata":
                return [], None, None, all_usage_details # Add None for final_ids
            else: # research scope
                error_response = {
                    "detailed_research": "Could not generate embedding for the query.",
                    "status_summary": "❌ Embedding Generation Failed"
                }
                return error_response, None, None, all_usage_details # Add None for final_ids

        # --- Metadata Scope Handling ---
        if scope == "metadata":
            logger.info(f"Processing '{scope}' scope for {DATABASE_NAME}")
            all_initial_results = []
            initial_chunk_ids = [] # Collect combined initial IDs
            # Perform vector search for each configured IASB document ID
            for doc_id, k_value in IASB_DOC_CONFIG.items():
                logger.debug(f"Performing metadata vector search for {doc_id} (k={k_value})")
                initial_results_for_doc = _perform_vector_search(
                    cursor, query_embedding, k_value, doc_id=doc_id
                )
                # --- Capture Initial IDs for this doc ---
                if initial_results_for_doc:
                    ids_for_doc = [str(item.get('id')) for item in initial_results_for_doc if item.get('id')]
                    initial_chunk_ids.extend(ids_for_doc)
                all_initial_results.extend(initial_results_for_doc)

            if not all_initial_results:
                logger.info(f"No initial vector search results for metadata query across all IASB sources.")
                return [], None, None, all_usage_details # Return empty list, no IDs, usage

            unique_sections = {}
            # No separate metadata_chunk_ids needed, using combined initial_chunk_ids
            for record in all_initial_results:
                doc_id = record.get('document_id')
                chapter = record.get('chapter_name')
                hierarchy = record.get('section_hierarchy')
                title = record.get('section_title')
                summary = record.get('chapter_summary') # Contains section summary
                chunk_id = record.get('id')

                if not all([doc_id, chapter, hierarchy, title, summary, chunk_id]):
                    logger.warning(f"Skipping record due to missing fields: {record.get('id')}")
                    continue

                section_key = (doc_id, chapter, hierarchy)
                if section_key not in unique_sections:
                    unique_sections[section_key] = {
                        'id': chunk_id, # Use first chunk ID found for this section
                        'title': title,
                        'summary': summary,
                        'doc_id': doc_id # Keep original doc_id for source_document_id
                    }
                    # metadata_chunk_ids.append(chunk_id) # No longer needed

            metadata_response: MetadataResponse = []
            for section_data in unique_sections.values():
                metadata_response.append({
                    'id': section_data['id'],
                    'document_name': section_data['title'], # Use section title as name
                    'document_description': section_data['summary'], # Use section summary as description
                    'source': DATABASE_NAME,
                    'source_document_id': section_data['doc_id'] # Add the original document ID
                })

            logger.info(f"Returning {len(metadata_response)} unique sections for metadata scope from {DATABASE_NAME}.")
            # Return metadata, the combined *initial* chunk IDs (final IDs not applicable), and usage details
            return metadata_response, initial_chunk_ids, None, all_usage_details

        # --- Research Scope Handling ---
        elif scope == "research":
            logger.info(f"Processing '{scope}' scope for {DATABASE_NAME}")
            final_research_result: ResearchResponse = {
                "detailed_research": default_research,
                "status_summary": default_error_status,
            }

            all_processed_results = [] # Store processed results from all doc IDs
            initial_chunk_ids = [] # Store combined initial IDs
            final_chunk_ids = [] # Store combined final IDs

            # Process each Document ID defined in IASB_DOC_CONFIG
            for doc_id, k_value in IASB_DOC_CONFIG.items():
                # --- Get Initial IDs for this doc ---
                initial_results_for_doc = _perform_vector_search(cursor, query_embedding, k_value, doc_id=doc_id)
                if initial_results_for_doc:
                    ids_for_doc = [str(item.get('id')) for item in initial_results_for_doc if item.get('id')]
                    initial_chunk_ids.extend(ids_for_doc)
                    logger.info(f"Captured {len(ids_for_doc)} initial chunk IDs for doc {doc_id} (research scope).")

                # --- Process this doc (relevance, rerank, expand, gap fill) ---
                # Now returns processed chunks, final IDs for this doc, AND usage details
                processed_chunks_for_doc, final_ids_for_doc, usage_for_doc = _process_single_document_id(
                    cursor, query, query_embedding, doc_id, k_value, token
                )
                all_processed_results.extend(processed_chunks_for_doc)
                if final_ids_for_doc: final_chunk_ids.extend(final_ids_for_doc) # Collect final IDs
                all_usage_details.extend(usage_for_doc) # Collect usage details

            # Check if any results were found across all documents
            if not all_processed_results:
                logger.info(f"No relevant information found across any IASB document sources for query: '{query}'")
                final_research_result["status_summary"] = default_no_info_status
                final_research_result["detailed_research"] = "No relevant information found across any IASB document sources."
                # Return early, include the (potentially empty) initial IDs
                return final_research_result, initial_chunk_ids, None, all_usage_details
            else:
                # Log combined counts
                logger.info(f"Collected {len(initial_chunk_ids)} total initial chunk IDs for research scope across all IASB sources.")
                logger.info(f"Collected {len(final_chunk_ids)} total final chunk IDs for research scope across all IASB sources.")

                # Format combined chunks into cards
                logger.info(f"Formatting combined {len(all_processed_results)} processed items from all IASB sources.")
                formatted_chunks = _format_chunks_as_cards(all_processed_results)

                # Generate ONE final response from the combined cards
                final_research_result, synthesis_usage = _generate_response_from_chunks(query, formatted_chunks, token)
                if synthesis_usage: all_usage_details.append(synthesis_usage)

                # Return the final research result, the combined *initial* IDs, the combined *final* IDs, and usage details
                return final_research_result, initial_chunk_ids, final_chunk_ids, all_usage_details

        else:
            # Invalid scope handling
            logger.error(f"Invalid scope '{scope}' provided to {DATABASE_NAME} subagent.")
            if scope == "metadata":
                return [], None, None, all_usage_details
            else:
                error_response = {"detailed_research": f"Invalid scope '{scope}' provided.", "status_summary": "❌ Invalid Scope"}
                return error_response, None, None, all_usage_details

    except psycopg2.Error as db_err:
        logger.error(f"Database error during {DATABASE_NAME} query (Scope: {scope}): {db_err}", exc_info=True)
        if conn: conn.rollback()
        if scope == "metadata":
            return [], None, None, all_usage_details
        else:
            error_response = {"detailed_research": f"**Database Error:** {str(db_err)}", "status_summary": "❌ Database Error"}
            return error_response, None, None, all_usage_details
    except ConnectionError as conn_err:
         logger.error(f"Connection error for {DATABASE_NAME} (Scope: {scope}): {conn_err}", exc_info=True)
         if scope == "metadata":
             return [], None, None, all_usage_details
         else:
             error_response = {"detailed_research": f"**Connection Error:** {str(conn_err)}", "status_summary": "❌ DB Connection Error"}
             return error_response, None, None, all_usage_details
    except Exception as e:
        logger.error(f"Unexpected error querying {DATABASE_NAME} database (Scope: {scope}): {e}", exc_info=True)
        if conn: conn.rollback()
        if scope == "metadata":
            return [], None, None, all_usage_details
        else:
            error_response = {"detailed_research": f"**Unexpected Error:** {str(e)}", "status_summary": default_error_status}
            return error_response, None, None, all_usage_details
    finally:
        # Ensure connection is closed even if early returns happened
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed.")

    # Fallback return (should not be reached ideally)
    logger.error(f"Reached end of _query_database_logic unexpectedly for scope '{scope}' in {DATABASE_NAME}.")
    if scope == "metadata":
        return [], None, None, all_usage_details
    else:
        error_response = {"detailed_research": "Reached end of logic function unexpectedly.", "status_summary": "❌ Unexpected Flow"}
        return error_response, None, None, all_usage_details


# --- Main Function ---

def query_database_sync(query: str, scope: str, token: Optional[str] = None, process_monitor=None) -> SubagentResult:
    """
    Synchronously query the External IASB database. Handles 'metadata' and 'research' scopes.

    Args:
        query (str): The search query to execute.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token for API access.
        process_monitor: Optional process monitor to track token usage

    Returns:
        SubagentResult: Tuple containing:
            - DatabaseResponse: Query results, either MetadataResponse or ResearchResponse.
            - Optional[List[str]]: List of chunk IDs used in the search, or None.
    """
    start_time = time.time()
    logger.info(f"Querying {DATABASE_NAME} database: '{query}' with scope: {scope}")
    stage_name = f"db_query_{DATABASE_NAME}"
    result: DatabaseResponse = {} if scope == "research" else [] # Initialize result
    initial_chunk_ids: Optional[List[str]] = None
    final_chunk_ids: Optional[List[str]] = None # Added final_chunk_ids
    all_usage_details: List[LlmUsageDetails] = []

    # Start tracking this database query in the process monitor if provided
    if process_monitor:
        process_monitor.start_stage(stage_name)
        # Add initial details like scope and query
        process_monitor.add_stage_details(stage_name, scope=scope, query=query)

    try:
        # Call the logic function which now returns result, initial_ids, final_ids, and usage_details
        result, initial_chunk_ids, final_chunk_ids, all_usage_details = _query_database_logic(query, scope, token)

        # Process collected usage details if monitor is enabled
        if process_monitor and all_usage_details:
            for usage in all_usage_details:
                if usage: # Ensure usage is not None
                    try:
                        # Add each LLM call's details to the monitor stage
                        process_monitor.add_llm_call_details_to_stage(stage_name, usage)
                    except Exception as monitor_err:
                        logger.error(f"Error adding LLM usage details to process monitor for stage {stage_name}: {monitor_err}", exc_info=True)

        # Add final details (like initial/final chunk IDs or status) to the monitor stage
        if process_monitor:
            details_to_add = {}
            if initial_chunk_ids:
                details_to_add['initial_document_ids'] = initial_chunk_ids # New key
                details_to_add['result_count'] = len(initial_chunk_ids) # Keep overall count based on initial
            if final_chunk_ids:
                 details_to_add['final_document_ids'] = final_chunk_ids # New key
            if scope == "research" and isinstance(result, dict):
                details_to_add['status_summary'] = result.get("status_summary", "N/A")
            elif scope == "metadata" and isinstance(result, list):
                 # result_count already added if chunk_ids exist
                 pass # No specific status for metadata usually

            if details_to_add:
                process_monitor.add_stage_details(stage_name, **details_to_add)

    except Exception as e:
        logger.error(f"Error during {DATABASE_NAME} query execution: {str(e)}", exc_info=True)
        # Ensure result is set to an error state if not already
        if scope == "research" and not (isinstance(result, dict) and result.get("status_summary", "").startswith("❌")):
             result = {"detailed_research": f"**Unhandled Error:** {str(e)}", "status_summary": "❌ Unhandled Error"}
        elif scope == "metadata":
             result = [] # Return empty list on error for metadata

        # Add error details to process monitor
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=str(e))
            # End stage with error status
            process_monitor.end_stage(stage_name, status="error")

        # Re-raise the exception? Or return the error result?
        # Current structure returns the error result. If re-raise is needed, uncomment below:
        # raise

    finally:
        # End the tracking stage if it hasn't been ended due to error
        if process_monitor and process_monitor.stages.get(stage_name) and process_monitor.stages[stage_name].status == "in_progress":
            process_monitor.end_stage(stage_name) # Default status is 'completed'

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"{DATABASE_NAME} query completed in {duration:.2f} seconds.")

    # Return the result and the collected *initial* chunk IDs (main return value remains initial IDs)
    return result, initial_chunk_ids
