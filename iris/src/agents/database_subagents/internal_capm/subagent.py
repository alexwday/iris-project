# internal_capm/subagent.py
"""
Internal CAPM (Central Accounting Policy Manual) Subagent

This module handles queries to the Internal CAPM database,
including catalog retrieval, document selection, section selection,
content retrieval, and response synthesis.

Functions:
    query_database_sync: Synchronously query the Internal CAPM database
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Define response types consistent with database_router
MetadataResponse = List[Dict[str, Any]]
# ResearchResponse is now a dictionary containing detailed research and status
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]

from ....chat_model.model_settings import ENVIRONMENT, get_model_config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm
from .catalog_selection_prompt import get_catalog_selection_prompt
from .section_selection_prompt import get_section_selection_prompt
# Removed: from .description_condensation_prompt import get_description_condensation_prompt
from .content_synthesis_prompt import (
    get_content_synthesis_prompt,
    get_individual_file_synthesis_prompt,
    INDIVIDUAL_DOCUMENT_TOOL_SCHEMA,
)

# Get module logger
logger = logging.getLogger(__name__)

# Approximate tokens per character (used for token size estimation)
TOKENS_PER_CHAR = 0.25

# Define the tool schema for research synthesis
SYNTHESIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "synthesize_research_findings",
        "description": "Synthesizes research findings from provided documents and generates a status summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_summary": {
                    "type": "string",
                    "description": "Concise status summary (1 sentence) indicating finding relevance (e.g., '✅ Found direct answer.', '📄 No relevant info found.').",
                },
                "detailed_research": {
                    "type": "string",
                    "description": "Detailed, structured markdown report synthesizing information from documents, including citations (document and section names).",
                },
            },
            "required": ["status_summary", "detailed_research"],
        },
    },
}


# Formatting functions
# Removed generate_condensed_description function


def format_catalog_for_llm(catalog_records: List[Dict[str, Any]]) -> str:
    """
    Format the catalog records into a string that is optimized for LLM comprehension.
    """
    formatted_catalog = ""
    for record in catalog_records:
        doc_id = record.get("id", "unknown")
        doc_name = record.get("document_name", "Untitled")
        doc_desc = record.get("document_description", "No description available")
        formatted_catalog += f"Document ID: {doc_id}\n"
        formatted_catalog += f"Document Name: {doc_name}\n"
        formatted_catalog += f"Document Description: {doc_desc}\n\n"
    return formatted_catalog.strip()


def format_sections_and_summaries_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format document sections and summaries into a string optimized for LLM analysis.
    This is used for the section selection step.
    """
    formatted_docs = ""
    for doc in documents:
        doc_name = doc.get("document_name", "Untitled")
        formatted_docs += f"# {doc_name}\n\n"
        sections = doc.get("sections", [])
        for section in sections:
            section_id = section.get("section_id", "unknown") # Get section_id
            section_name = section.get("section_name", "Untitled Section")
            section_summary = section.get("section_summary", "No summary available")
            # Include section_id in the formatted output
            formatted_docs += f"## Section ID: {section_id} | Name: {section_name}\n"
            formatted_docs += f"Summary: {section_summary}\n\n"
        formatted_docs += "---\n\n"
    return formatted_docs.strip()


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a string that is optimized for LLM analysis.
    This is used for the content synthesis step.
    """
    formatted_docs = ""
    for doc in documents:
        doc_name = doc.get("document_name", "Untitled")
        formatted_docs += f"# {doc_name}\n\n"
        sections = doc.get("sections", [])
        for section in sections:
            section_name = section.get("section_name", "Untitled Section")
            section_content = section.get("section_content", "No content available")
            formatted_docs += f"## {section_name}\n\n"
            formatted_docs += f"{section_content}\n\n"
        formatted_docs += "---\n\n"
    return formatted_docs.strip()


def format_single_document_for_llm(document: Dict[str, Any]) -> str:
    """
    Format a single document into a string that is optimized for LLM analysis.
    This is used when processing documents individually due to token limits.
    """
    doc_name = document.get("document_name", "Untitled")
    formatted_doc = f"# {doc_name}\n\n"
    sections = document.get("sections", [])
    for section in sections:
        section_name = section.get("section_name", "Untitled Section")
        section_content = section.get("section_content", "No content available")
        formatted_doc += f"## {section_name}\n\n"
        formatted_doc += f"{section_content}\n\n"
    return formatted_doc.strip()


# Database interaction functions
def fetch_capm_catalog() -> List[Dict[str, Any]]:
    """
    Fetch the full internal CAPM catalog from the database.
    """
    logger.info(f"Fetching full CAPM catalog (environment: {ENVIRONMENT})")
    conn = connect_to_db(ENVIRONMENT)
    catalog_records: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for CAPM catalog")
        return catalog_records
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, document_name, document_description
                FROM apg_catalog
                WHERE document_source = 'internal_capm'
                ORDER BY document_name
            """
            )
            for row in cur.fetchall():
                catalog_records.append(
                    {
                        "id": str(row[0]),
                        "document_name": row[1],
                        "document_description": row[2],
                    }
                )
        logger.info(
            f"Retrieved {len(catalog_records)} CAPM catalog entries from database"
        )
    except Exception as e:
        logger.error(f"Error fetching CAPM catalog from database: {str(e)}")
    finally:
        if conn:
            conn.close()
    return catalog_records


def fetch_document_sections_and_summaries(doc_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch the sections and summaries of specified CAPM documents from the database.
    This is used for the section selection step.
    """
    logger.info(f"Fetching CAPM sections and summaries for documents: {doc_ids}")
    if not doc_ids:
        logger.warning("No CAPM document IDs to fetch")
        return []
    conn = connect_to_db(ENVIRONMENT)
    result: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for CAPM sections and summaries")
        return result
    try:
        doc_names = {}
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(doc_ids))
            cur.execute(
                f"""
                SELECT id, document_name
                FROM apg_catalog
                WHERE id::text IN ({placeholders})
                AND document_source = 'internal_capm'
            """,
                doc_ids,
            )
            for row in cur.fetchall():
                doc_names[row[0]] = row[1]
            logger.info(f"Found {len(doc_names)} CAPM documents for IDs: {doc_ids}")

        for doc_id, doc_name in doc_names.items():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT section_id, section_name, section_summary
                    FROM apg_content
                    WHERE document_source = 'internal_capm'
                    AND document_name = %s
                    ORDER BY section_id
                """,
                    (doc_name,),
                )
                sections = []
                for row in cur.fetchall():
                    sections.append(
                        {
                            "section_id": row[0],
                            "section_name": (row[1] if row[1] else f"Section {row[0]}"),
                            "section_summary": (
                                row[2] if row[2] else "No summary available"
                            ),
                        }
                    )
                if sections:
                    result.append({"document_name": doc_name, "sections": sections})
        logger.info(
            f"Retrieved CAPM sections and summaries for {len(result)} documents from database"
        )
    except Exception as e:
        logger.error(
            f"Error fetching CAPM sections and summaries from database: {str(e)}"
        )
    finally:
        if conn:
            conn.close()
    return result


def fetch_section_content(
    section_id_selections: Dict[str, List[str]], # Renamed parameter
) -> List[Dict[str, Any]]:
    """
    Fetch the full content of specified sections from CAPM documents using section IDs.

    Args:
        section_id_selections: Dictionary mapping document names to lists of selected section IDs (as strings).

    Returns:
        List of documents with their selected sections (including name and content)
    """
    logger.info(f"Fetching CAPM content for selected section IDs: {section_id_selections}")
    if not section_id_selections:
        logger.warning("No CAPM section IDs provided to fetch content")
        return []
    conn = connect_to_db(ENVIRONMENT)
    result: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for CAPM section content")
        return result
    try:
        for doc_name, section_ids in section_id_selections.items():
            logger.debug(f"Querying content for doc: '{doc_name}', section IDs: {section_ids}") # Log query details
            if not section_ids:
                logger.warning(f"Skipping document '{doc_name}' as no section IDs were selected.")
                continue

            # Ensure section IDs are appropriate for the query (e.g., integers if the column is integer)
            # Assuming section_id in DB is integer, attempt conversion. If it's text, use strings directly.
            try:
                # Assuming section_id is stored as an integer in the DB
                int_section_ids = [int(sid) for sid in section_ids]
                placeholders = ",".join(["%s"] * len(int_section_ids))
                query_params = [doc_name] + int_section_ids
                id_column_name = "section_id" # Use the correct column name
            except ValueError:
                 logger.error(f"Could not convert all section IDs to integers for doc '{doc_name}': {section_ids}. Check LLM output format.", exc_info=True)
                 continue # Skip this document if IDs are not valid integers

            with conn.cursor() as cur:
                try: # Add try/except around DB execution
                    sql_query = f"""
                        SELECT section_id, section_name, section_content
                        FROM apg_content
                        WHERE document_source = 'internal_capm'
                        AND document_name = %s
                        AND {id_column_name} IN ({placeholders})
                        ORDER BY section_id
                    """
                    cur.execute(sql_query, query_params)
                    rows = cur.fetchall()
                    logger.debug(f"Found {len(rows)} sections in DB for doc: '{doc_name}' with IDs: {int_section_ids}") # Log result count
                    sections = []
                    for row in rows:
                        sections.append(
                            {
                            # Keep section_name in the output for synthesis context
                            "section_name": (row[1] if row[1] else f"Section {row[0]}"),
                            "section_content": row[2],
                            }
                        )
                    if sections:
                        result.append({"document_name": doc_name, "sections": sections})
                    elif rows is None: # Check if fetchall returned None (might indicate error)
                         logger.error(f"Database query returned None for doc: '{doc_name}' with IDs {int_section_ids}")
                    # else: sections is empty and rows is not None (means query ran but found 0 matching rows)
                         # logger.debug(f"Query executed successfully but found 0 matching sections for doc: '{doc_name}' with IDs {int_section_ids}") # Optional

                except Exception as db_exec_err:
                     logger.error(f"Database error executing query for doc '{doc_name}' with IDs {int_section_ids}: {db_exec_err}", exc_info=True)

        logger.info(f"Retrieved CAPM content for {len(result)} documents from database") # This log remains correct
    except Exception as e:
        logger.error(f"Error during CAPM section content fetching loop: {str(e)}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return result


# LLM interaction helper
def get_completion(
    capability: str,
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    token: Optional[str] = None,
    database_name: Optional[str] = None,
    **kwargs: Any,  # Accept additional kwargs for tools, tool_choice etc.
) -> Any:  # Returns the raw OpenAI response object or content string or error string
    """
    Helper function to get a completion from the LLM.
    Handles standard completions and tool calls.
    """
    try:
        model_config = get_model_config(capability)
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        completion_cost = model_config["completion_token_cost"]
    except Exception as config_err:
        logger.error(
            f"Failed to get model configuration for capability '{capability}': {config_err}"
        )
        return f"Error: Configuration error for model capability '{capability}'"

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]

    call_params = {
        "oauth_token": token or "placeholder_token",
        "prompt_token_cost": prompt_cost,
        "completion_token_cost": completion_cost,
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "database_name": database_name,
        **kwargs,
    }

    is_tool_call = "tools" in kwargs and kwargs["tools"]
    if is_tool_call:
        call_params["stream"] = False
        logger.info("Forcing non-streaming mode for tool call.")
    else:
        call_params.setdefault("stream", False)

    try:
        # Direct synchronous call
        response = call_llm(**call_params)
    except Exception as llm_err:
        logger.error(f"call_llm failed: {llm_err}", exc_info=True)
        return f"Error: LLM call failed ({type(llm_err).__name__})"

    if is_tool_call:
        logger.debug("Returning raw response object for tool call.")
        if (
            not response
            or not hasattr(response, "choices")
            or not response.choices
            or not hasattr(response.choices[0], "message")
            or not hasattr(response.choices[0].message, "tool_calls")
        ):
            logger.error("Invalid response structure received for tool call.")
            return "Error: Invalid response structure for tool call."
        return response
    else:
        response_value = ""
        if response and hasattr(response, "choices") and response.choices:
            message = response.choices[0].message
            if message and hasattr(message, "content") and message.content is not None:
                response_value = message.content.strip()
            else:
                logger.warning("LLM response message content was missing or None.")
                response_value = ""
        else:
            logger.error("LLM response object or choices attribute missing/empty.")
            response_value = "Error: Could not retrieve response content."
        logger.debug("Returning extracted content string for standard completion.")
        return response_value


def select_relevant_documents(
    query: str,
    catalog: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_capm",
) -> List[str]:
    """
    Use an LLM to select the most relevant CAPM documents.
    """
    logger.info("Selecting relevant CAPM documents from catalog")
    formatted_catalog = format_catalog_for_llm(catalog)
    selection_prompt = get_catalog_selection_prompt(query, formatted_catalog)

    try:
        logger.info(
            f"Initiating CAPM Document Selection API call (DB: {database_name})"
        )
        # Direct synchronous call
        response_str = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=200,
            token=token,
            database_name=database_name,
        )

        # Check if get_completion returned an error string
        if isinstance(response_str, str) and response_str.startswith("Error:"):
            logger.error(
                f"get_completion failed during document selection: {response_str}"
            )
            return []

        try:
            selected_ids = json.loads(response_str)
            if isinstance(selected_ids, list) and all(
                isinstance(i, str) for i in selected_ids
            ):
                logger.info(f"LLM selected CAPM document IDs: {selected_ids}")
                return selected_ids
            else:
                logger.error(
                    f"LLM response for CAPM selection was valid JSON but not list of strings: {response_str}"
                )
                return []
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse CAPM selection LLM response as JSON, attempting fallback"
            )
            matches = re.findall(r'"([^"]+)"', response_str)
            valid_ids = [
                m for m in matches if m.isdigit()
            ]  # Assuming CAPM IDs are numeric strings
            if valid_ids:
                logger.warning(
                    f"Extracted CAPM document IDs using fallback regex: {valid_ids}"
                )
                return valid_ids
            logger.error(
                "Could not extract CAPM document IDs from response using fallback."
            )
            return []
    except Exception as e:
        logger.error(f"Error during LLM CAPM document selection: {str(e)}")
        return []


def select_relevant_sections(
    query: str,
    documents_with_summaries: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_capm",
) -> Dict[str, List[str]]:
    """
    Use an LLM to select the most relevant sections from CAPM documents based on summaries.

    Args:
        query: The user query
        documents_with_summaries: List of documents with their sections and summaries
        token: Optional authentication token
        database_name: Database name for logging

    Returns:
        Dictionary mapping document names to lists of selected section names
    """
    logger.info("Selecting relevant CAPM sections based on summaries")
    formatted_sections = format_sections_and_summaries_for_llm(documents_with_summaries)
    selection_prompt = get_section_selection_prompt(query, formatted_sections)

    try:
        logger.info(f"Initiating CAPM Section Selection API call (DB: {database_name})")
        # Direct synchronous call
        response_str = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=500,
            token=token,
            database_name=database_name,
        )

        # Check if get_completion returned an error string
        if isinstance(response_str, str) and response_str.startswith("Error:"):
            logger.error(
                f"get_completion failed during section selection: {response_str}"
            )
            return {}

        try:
            # Attempt to extract JSON block using regex
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                selected_sections = json.loads(json_str) # Parse the extracted string
            else:
                # Log if no JSON block found
                logger.error(f"Could not find JSON block in LLM response for section selection. Response: {response_str}")
                return {}

            # Validate the parsed structure (expecting dict[str, list[str]] where list contains section IDs)
            if isinstance(selected_sections, dict) and all(
                isinstance(doc_name, str)
                and isinstance(section_ids, list)
                and all(isinstance(sid, str) for sid in section_ids) # Ensure IDs are strings
                for doc_name, section_ids in selected_sections.items()
            ):
                logger.info(f"LLM selected CAPM section IDs: {selected_sections}")
                # Cast section IDs to the expected type if necessary, though string is fine for DB query
                # For now, directly return the dict[str, list[str]]
                return selected_sections # Return the dictionary mapping doc names to lists of section IDs
            else:
                # Log the original response if structure is wrong after successful parse
                logger.error(
                    f"LLM response for CAPM section ID selection was valid JSON but not in expected format (dict[str, list[str]]): {response_str}"
                )
                return {}
        except json.JSONDecodeError as e:
             # Log the raw response string that failed parsing
            logger.error(f"Failed to parse CAPM section selection LLM response as JSON. Error: {e}. Raw Response: {response_str}")
            return {}
    except Exception as e:
        logger.error(f"Error during LLM CAPM section selection: {str(e)}", exc_info=True) # Added exc_info for more detail
        return {}


def estimate_token_size(documents: List[Dict[str, Any]]) -> int:
    """
    Estimate the token size of the document content.
    This is used to determine if we need to process documents individually.

    Args:
        documents: List of documents with their sections and content

    Returns:
        Estimated token count
    """
    total_chars = 0
    for doc in documents:
        sections = doc.get("sections", [])
        for section in sections:
            content = section.get("section_content", "")
            total_chars += len(content)

    # Approximate token count based on characters
    return int(total_chars * TOKENS_PER_CHAR)


def synthesize_individual_document(
    query: str,
    document: Dict[str, Any],
    token: Optional[str] = None,
    database_name: str = "internal_capm",
) -> str:
    """
    Use an LLM to synthesize a response from a single CAPM document.
    Used when total content exceeds token limits.

    Args:
        query: The user query
        document: A single document with its sections and content
        token: Optional authentication token
        database_name: Database name for logging

    Returns:
        Synthesized response for the document
    """
    logger.info(
        f"Synthesizing response for individual CAPM document: {document.get('document_name')}"
    )
    formatted_document = format_single_document_for_llm(document)
    synthesis_prompt = get_individual_file_synthesis_prompt(query, formatted_document)

    try:
        logger.info(
            f"Initiating Individual CAPM Document Synthesis API call (DB: {database_name})"
        )
        # Direct synchronous call
        response_obj = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=1500,
            temperature=0.2,
            token=token,
            database_name=database_name,
            tools=[INDIVIDUAL_DOCUMENT_TOOL_SCHEMA],
            tool_choice={
                "type": "function",
                "function": {
                    "name": INDIVIDUAL_DOCUMENT_TOOL_SCHEMA["function"]["name"]
                },
            },
        )

        if isinstance(response_obj, str) and response_obj.startswith("Error:"):
            logger.error(
                f"get_completion failed for individual CAPM document synthesis: {response_obj}"
            )
            return f"Error processing document {document.get('document_name')}: {response_obj}"

        # Process Tool Call Response
        if (
            hasattr(response_obj, "choices")
            and response_obj.choices
            and hasattr(response_obj.choices[0], "message")
            and response_obj.choices[0].message
            and hasattr(response_obj.choices[0].message, "tool_calls")
            and response_obj.choices[0].message.tool_calls
        ):

            tool_call = response_obj.choices[0].message.tool_calls[0]
            if (
                tool_call.function.name
                == INDIVIDUAL_DOCUMENT_TOOL_SCHEMA["function"]["name"]
            ):
                arguments_str = tool_call.function.arguments
                logger.debug(f"Received tool arguments string: {arguments_str}")
                try:
                    arguments = json.loads(arguments_str)
                    if "document_summary" in arguments:
                        logger.info(
                            f"Successfully parsed individual document synthesis tool call for {database_name}."
                        )
                        summary = arguments.get("document_summary", "")
                        if not isinstance(summary, str):
                            summary = ""
                        return summary
                    else:
                        logger.error(
                            f"Missing required keys in parsed tool arguments for individual document: {arguments}"
                        )
                        return f"Error: Tool call arguments missing required keys for document {document.get('document_name')}."
                except json.JSONDecodeError as json_err:
                    logger.error(
                        f"Failed to parse tool arguments JSON for individual document: {json_err}. Arguments: {arguments_str}"
                    )
                    return f"Error: Failed to parse tool arguments JSON for document {document.get('document_name')} - {json_err}"
            else:
                logger.error(
                    f"Unexpected tool called for individual document: {tool_call.function.name}"
                )
                return f"Error: Unexpected tool called for document {document.get('document_name')}: {tool_call.function.name}"
        else:
            logger.error(
                f"No tool call received from LLM for individual document synthesis, despite being requested."
            )
            content = ""
            if (
                hasattr(response_obj, "choices")
                and response_obj.choices
                and hasattr(response_obj.choices[0], "message")
                and response_obj.choices[0].message
                and hasattr(response_obj.choices[0].message, "content")
                and response_obj.choices[0].message.content
            ):
                content = response_obj.choices[0].message.content
                logger.warning(
                    f"LLM returned content instead of tool call: {content[:200]}..."
                )
                return f"Error: LLM returned text instead of tool call for document {document.get('document_name')}. Content: {content[:200]}..."
            else:
                return f"Error: No tool call or content received from LLM for document {document.get('document_name')}."

    except Exception as e:
        logger.error(
            f"Exception during individual document synthesis: {str(e)}",
            exc_info=True,
        )
        return f"Error during synthesis of document {document.get('document_name')}: {str(e)}"


def synthesize_response_and_status(
    query: str,
    documents: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_capm",
) -> ResearchResponse:
    """
    Use an LLM tool call to synthesize a detailed research response AND status summary for CAPM.
    Processes each document individually in separate, staggered LLM calls.
    """
    logger.info(
        f"Synthesizing response and status for {database_name} by processing documents individually."
    )
    default_error_status = f"❌ Error processing {database_name} query."
    default_no_info_status = f"📄 No relevant information found in {database_name}."
    default_research = f"No detailed research generated for {database_name} due to missing documents or error."

    if not documents:
        logger.warning(f"No documents provided for {database_name} synthesis.")
        return {
            "detailed_research": default_research,
            "status_summary": default_no_info_status,
        }

    individual_results = []
    success_count = 0
    error_count = 0

    for i, document in enumerate(documents):
        doc_name = document.get("document_name", "Untitled")
        logger.info(f"Processing document {i+1}/{len(documents)}: {doc_name}")

        # Stagger calls
        if i > 0:
            logger.debug(f"Sleeping for 1 second before processing next document.")
            time.sleep(1)

        doc_result = synthesize_individual_document(
            query, document, token, database_name
        )

        if isinstance(doc_result, str) and doc_result.startswith("Error:"):
            logger.error(f"Error synthesizing document {doc_name}: {doc_result}")
            individual_results.append((doc_name, doc_result))
            error_count += 1
        else:
            logger.info(f"Successfully synthesized document {doc_name}")
            individual_results.append((doc_name, doc_result))
            success_count += 1

    # Combine individual results with formatting
    combined_research = ""
    for doc_name, result in individual_results:
        combined_research += f"## {doc_name}\n\n"
        combined_research += f"{result}\n\n"
        combined_research += "---\n\n"

    # Generate final status summary
    if success_count > 0 and error_count == 0:
        status_summary = f"✅ Found information from {success_count} document(s)."
    elif success_count > 0 and error_count > 0:
        status_summary = f"⚠️ Found information from {success_count} document(s), but encountered errors processing {error_count} other(s)."
    elif success_count == 0 and error_count > 0:
        status_summary = f"❌ Errors encountered while processing {error_count} document(s)."
    else: # success_count == 0 and error_count == 0 (shouldn't happen if documents list is not empty, but handle defensively)
        status_summary = default_no_info_status

    return {
        "detailed_research": combined_research.strip(),
        "status_summary": status_summary,
    }


def query_database_sync(
    query: str, scope: str, token: Optional[str] = None
) -> DatabaseResponse:
    """
    Synchronously query the Internal CAPM database based on the specified scope.

    This function implements the CAPM-specific query flow, which includes:
    1. Fetching the catalog
    2. Selecting relevant documents
    3. For research scope:
       a. Fetching sections and summaries
       b. Selecting relevant sections based on summaries
       c. Fetching full content for selected sections
       d. Synthesizing response (with token size handling)

    Args:
        query (str): The search query to execute.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token for API access.

    Returns:
        DatabaseResponse: Query results, either a List[Dict] for 'metadata' scope
                          or a Dict[str, str] for 'research' scope.
    """
    logger.info(f"Querying Internal CAPM database: '{query}' with scope: {scope}")
    database_name = "internal_capm"
    default_error_status = "❌ Error during query processing."

    try:
        # Fetch catalog
        catalog = fetch_capm_catalog()
        logger.info(f"Retrieved {len(catalog)} total CAPM catalog entries")
        if not catalog:
            if scope == "metadata":
                return []
            else:
                return {
                    "detailed_research": "No documents found in the Internal CAPM database catalog.",
                    "status_summary": "📄 No documents found in catalog.",
                }

        # Select documents
        doc_ids = select_relevant_documents(
            query, catalog, token, database_name=database_name
        )
        logger.info(
            f"LLM selected {len(doc_ids)} relevant CAPM document IDs: {doc_ids}"
        )
        if not doc_ids:
            if scope == "metadata":
                return []
            else:
                return {
                    "detailed_research": "LLM did not select any relevant documents from the catalog based on the query.",
                    "status_summary": "📄 No relevant documents selected by LLM.",
                }

        # Process based on scope
        if scope == "metadata":
            # Get selected items from catalog
            selected_items = [item for item in catalog if item.get("id") in doc_ids]

            # Removed generation of condensed descriptions

            logger.info(
                f"Returning {len(selected_items)} selected CAPM metadata items."
            )
            return selected_items
        elif scope == "research":
            # Fetch sections and summaries
            documents_with_summaries = fetch_document_sections_and_summaries(doc_ids)
            logger.info(
                f"Retrieved sections and summaries for {len(documents_with_summaries)} CAPM documents."
            )
            if not documents_with_summaries:
                return {
                    "detailed_research": "Could not retrieve sections and summaries for the selected CAPM documents.",
                    "status_summary": "❌ Error retrieving document sections.",
                }

            # Select relevant sections based on summaries
            section_selections = select_relevant_sections(
                query, documents_with_summaries, token, database_name=database_name
            )
            # Removed redundant/confusing log line here
            if not section_selections:
                logger.warning("LLM did not select any relevant sections.") # Added more specific warning
                return {
                    "detailed_research": "LLM did not select any relevant sections from the CAPM documents based on the query.",
                    "status_summary": "📄 No relevant sections selected by LLM.",
                }

            # Fetch full content for selected sections
            documents_with_content = fetch_section_content(section_selections)
            logger.info(
                f"Retrieved content for {len(documents_with_content)} CAPM documents for research."
            )
            if not documents_with_content:
                return {
                    "detailed_research": "Could not retrieve content for the selected CAPM sections.",
                    "status_summary": "❌ Error retrieving section content.",
                }

            # Synthesize response
            research_result = synthesize_response_and_status(
                query, documents_with_content, token, database_name=database_name
            )
            return research_result
        else:
            logger.error(f"Invalid scope provided to internal_capm subagent: {scope}")
            raise ValueError(f"Invalid scope: {scope}")

    except Exception as e:
        error_msg = f"Error querying Internal CAPM database (scope: {scope}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            return []
        else:  # research scope
            return {
                "detailed_research": f"**Error processing request for Internal CAPM:** {str(e)}",
                "status_summary": default_error_status,
            }
