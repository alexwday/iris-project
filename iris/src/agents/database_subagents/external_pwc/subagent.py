# external_pwc/subagent.py
"""
External PwC Guidance Subagent

Handles queries to the PwC guidance content stored in the database,
performing vector search, refinement, and response synthesis.

Functions:
    query_database_sync: Synchronously query the PwC guidance database
"""

import json
import logging
import time
import traceback
import itertools
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Define response types consistent with database_router
MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str] # ResearchResponse is a dictionary containing detailed research and status
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
SubagentResult = Tuple[DatabaseResponse, Optional[List[str]]]  # Define a tuple for result + doc_ids

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

# Get module logger
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
DATABASE_NAME = "external_pwc" # Changed to PwC
TARGET_TABLE = "iris_textbook_database"  # Keeping the same table name as confirmed
PWC_DOCUMENT_ID = "pwc_ca_ifrs_manual" # Specific PwC doc ID

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


def _generate_query_embedding(
    query: str, token: Optional[str] = None
) -> Union[List[float], None]:
    """Generates embedding for the query string using call_llm."""
    logger.info(f"Generating embedding for query: '{query}'...")
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
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Usage details: {usage_details}")
        else:
            # For backward compatibility in case it doesn\'t return a tuple
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
            return response.data[0].embedding
        else:
            logger.error(
                "No embedding data received from API.",
                extra={"api_response": response},
            )
            return None

    except Exception as e:
        logger.error(
            f"Failed to generate embedding: {e}", exc_info=True
        )
        return None


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
) -> tuple[list[dict], dict]:
    """
    Uses LLM via call_llm to classify chunk summaries as relevant (1) or irrelevant (0).
    Filters out irrelevant chunks. Returns filtered list and relevance map.
    """
    logger.info(
        f"Filtering {len(results)} results by summary relevance using {RELEVANCE_MODEL_CAPABILITY}"
    )
    if not results:
        return [], {}

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
        return results, {}

    prompt_summaries = "\n".join(
        [f"ID: {item['id']}\nSummary: {item['summary']}\n---" for item in summaries_data]
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
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Usage details for {DATABASE_NAME}: {usage_details}")
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

    return filtered_results, relevance_map


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
        chapter_name = record_for_metadata.get('chapter_name', 'Unknown Chapter')
        section_title = record_for_metadata.get('section_title', 'Unknown Section')
        section_hierarchy = record_for_metadata.get('section_hierarchy', '')
        standard = record_for_metadata.get('section_standard') # Use section_standard
        standard_codes = record_for_metadata.get('section_standard_codes') # Use section_standard_codes
        tags = record_for_metadata.get('chapter_tags') # Use chapter_tags

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
) -> ResearchResponse:
    """
    Generates a response using LLM tool call based on the query and formatted chunks.
    """
    logger.info(f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}")

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
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Usage details: {usage_details}")
        else:
            # For backward compatibility in case it doesn\'t return a tuple
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
                        }
                    else:
                        logger.error(f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}")
                        return default_response
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}")
                    return default_response
            else:
                logger.error(f"Unexpected tool called: {tool_call.function.name}")
                return default_response
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
                }
            else:
                logger.error("No tool call or content received from LLM for synthesis.")
                return default_response

    except Exception as e:
        logger.error(f"Exception during final response synthesis: {e}", exc_info=True)
        return default_response


# --- Logic Function (Handles Core Query Processing) ---

def _query_database_logic(
    query: str, scope: str, token: Optional[str] = None
) -> DatabaseResponse:
    """
    Internal logic to handle database connection, embedding, scope routing,
    and error handling for the PWC subagent query.
    """
    default_error_status = f"❌ Error processing {DATABASE_NAME} query."
    default_no_info_status = f"📄 No relevant information found in {DATABASE_NAME}."
    default_research = f"No detailed research generated for {DATABASE_NAME}."

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

        query_embedding = _generate_query_embedding(query, token)
        if query_embedding is None:
            # Handle embedding failure based on scope
            if scope == "metadata":
                return []
            else: # research scope
                return {
                    "detailed_research": "Could not generate embedding for the query.",
                    "status_summary": "❌ Embedding Generation Failed"
                }

        # --- Metadata Scope Handling ---
        if scope == "metadata":
            logger.info(f"Processing '{scope}' scope for {DATABASE_NAME}")
            # Filter by specific PWC document ID for metadata search
            initial_results = _perform_vector_search(
                cursor, query_embedding, INITIAL_K, doc_id=PWC_DOCUMENT_ID
            )
            if not initial_results:
                logger.info(f"No initial vector search results for metadata query in {DATABASE_NAME}.")
                return []

            unique_sections = {}
            for record in initial_results:
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
            return metadata_response

        # --- Research Scope Handling ---
        elif scope == "research":
            logger.info(f"Processing '{scope}' scope for {DATABASE_NAME}")
            research_result: ResearchResponse = {
                "detailed_research": default_research,
                "status_summary": default_error_status,
            }
            
            # Start of the research pipeline
            # Filter by specific PWC document ID for research search
            initial_results = _perform_vector_search(
                cursor, query_embedding, INITIAL_K, doc_id=PWC_DOCUMENT_ID
            )
            if not initial_results:
                research_result["status_summary"] = default_no_info_status
                research_result["detailed_research"] = "No results found in the initial vector search."
                return research_result # Return early

            processed_results = initial_results
            all_added_chunk_ids = set()

            # 4. Summary Relevance Filtering
            filtered_results, _ = _filter_by_summary_relevance(query, processed_results, token)
            if not filtered_results:
                research_result["status_summary"] = default_no_info_status
                research_result["detailed_research"] = "No relevant information remained after summary filtering."
                return research_result
            processed_results = filtered_results

            # 5. Importance Reranking
            reranked_results = _rerank_by_importance(processed_results, IMPORTANCE_FACTOR)
            processed_results = reranked_results

            # 6. Section Expansion
            expanded_results, added_by_expansion = _expand_sections_by_token_count(
                cursor, processed_results, SECTION_EXPANSION_TOP_K_RANK, SECTION_EXPANSION_TOP_K_TOKENS, SECTION_EXPANSION_GENERAL_TOKENS
            )
            if not expanded_results:
                research_result["status_summary"] = default_no_info_status
                research_result["detailed_research"] = "No results remained after section expansion."
                return research_result
            all_added_chunk_ids.update(added_by_expansion)
            processed_results = expanded_results

            # 7. Sequence Gap Filling
            filled_results, added_by_gaps = _fill_sequence_gaps(
                cursor, processed_results, GAP_FILL_MAX_SEQUENCE_GAP
            )
            if not filled_results:
                research_result["status_summary"] = default_no_info_status
                research_result["detailed_research"] = "No results remained after sequence gap filling."
                return research_result
            all_added_chunk_ids.update(added_by_gaps)
            processed_results = filled_results

            # 8. Format Cards
            formatted_chunks = _format_chunks_as_cards(processed_results)

            # 9. Generate Final Response
            research_result = _generate_response_from_chunks(query, formatted_chunks, token)
            return research_result # Return the final research result

        else:
            # Invalid scope handling (should ideally be caught by router)
            logger.error(f"Invalid scope '{scope}' provided to {DATABASE_NAME} subagent.")
            # Return empty list for metadata-like scopes, error dict for research-like scopes
            if scope == "metadata": return []
            else: return {"detailed_research": f"Invalid scope '{scope}' provided.", "status_summary": "❌ Invalid Scope"}

    except psycopg2.Error as db_err:
        logger.error(f"Database error during {DATABASE_NAME} query (Scope: {scope}): {db_err}", exc_info=True)
        if conn: conn.rollback() # Rollback any transaction
        # Return appropriate error type based on scope
        if scope == "metadata": return []
        else: return {"detailed_research": f"**Database Error:** {str(db_err)}", "status_summary": "❌ Database Error"}
    except ConnectionError as conn_err:
         logger.error(f"Connection error for {DATABASE_NAME} (Scope: {scope}): {conn_err}", exc_info=True)
         if scope == "metadata": return []
         else: return {"detailed_research": f"**Connection Error:** {str(conn_err)}", "status_summary": "❌ DB Connection Error"}
    except Exception as e:
        logger.error(f"Unexpected error querying {DATABASE_NAME} database (Scope: {scope}): {e}", exc_info=True)
        if conn: conn.rollback()
        if scope == "metadata": return []
        else: return {"detailed_research": f"**Unexpected Error:** {str(e)}", "status_summary": default_error_status}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed.")

    # This part should ideally not be reached if all scopes return explicitly
    logger.error(f"Reached end of _query_database_logic unexpectedly for scope '{scope}' in {DATABASE_NAME}.")
    if scope == "metadata": return []
    else: return {"detailed_research": "Reached end of logic function unexpectedly.", "status_summary": "❌ Unexpected Flow"}


# --- Main Function ---

def query_database_sync(query: str, scope: str, token: Optional[str] = None, process_monitor=None) -> SubagentResult:
    """
    Synchronously query the External PwC database. Handles 'metadata' and 'research' scopes.

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
    total_tokens = 0
    total_cost = 0.0
    llm_usage_list = []  # Track all LLM call usage details
    
    # Start tracking this database query in the process monitor if provided
    if process_monitor:
        process_monitor.start_stage(stage_name)
        process_monitor.add_stage_details(stage_name, scope=scope, query=query)

    # Call the refactored logic function to get the main result
    # Wrapping this with token tracking
    try:
        result = _query_database_logic(query, scope, token)
        
        # Track token usage when embedding, relevance checking, and synthesis happen
        # Since we don't have direct access to modify _query_database_logic internals,
        # we're capturing the usage data from the result object if it includes it
        
        # For this database, we track the chunk IDs from vector search results
        # These are tracked indirectly across several helper functions
        chunk_ids = None
        
        # For research results, extract chunk IDs from initial results
        if scope == "research" and isinstance(result, dict) and result.get("status_summary") != "❌ Embedding Generation Failed":
            # Get chunk IDs from results, focus on those used for synthesis
            try:
                # Generate embedding and perform search to get chunks (simplified version of what's in _query_database_logic)
                conn = None
                try:
                    conn = connect_to_db(ENVIRONMENT)
                    if conn:
                        register_vector(conn)
                        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                            query_embedding = _generate_query_embedding(query, token)
                            if query_embedding:
                                initial_results = _perform_vector_search(cursor, query_embedding, 5, doc_id=PWC_DOCUMENT_ID)  # Smaller number for monitoring
                                if initial_results:
                                    chunk_ids = [str(item.get('id')) for item in initial_results if item.get('id')]
                finally:
                    if conn:
                        conn.close()
            except Exception as e:
                logger.warning(f"Failed to extract chunk IDs for monitoring: {e}")
        
        # For metadata scope, extract IDs from the result
        elif scope == "metadata" and isinstance(result, list) and result:
            chunk_ids = [item.get('id') for item in result if item.get('id')]
            logger.info(f"Extracted {len(chunk_ids)} chunk IDs from metadata result")
            
            # Add metadata result details to process monitor
            if process_monitor:
                process_monitor.add_stage_details(stage_name,
                    result_count=len(result),
                    document_ids=chunk_ids,
                    total_tokens=total_tokens,
                    total_cost=total_cost
                )
                
        # For research scope, update process monitor with research status
        if scope == "research" and isinstance(result, dict):
            # Add research result details to process monitor
            if process_monitor:
                process_monitor.add_stage_details(stage_name,
                    status_summary=result.get("status_summary", ""),
                    total_tokens=total_tokens,
                    total_cost=total_cost
                )
    
    except Exception as e:
        logger.error(f"Error in {DATABASE_NAME} query: {str(e)}", exc_info=True)
        
        # Add error details to process monitor
        if process_monitor:
            process_monitor.add_stage_details(stage_name,
                error=str(e),
                total_tokens=total_tokens,
                total_cost=total_cost
            )
            
        # Re-raise to let the outer handler deal with it
        raise
    
    finally:
        # End the tracking stage
        if process_monitor:
            process_monitor.end_stage(stage_name)
            
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"{DATABASE_NAME} query completed in {duration:.2f} seconds.")

    return result, chunk_ids
