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
# Updated to include file links
FileLink = Dict[str, str]  # Contains 'file_link' and 'document_name'
SubagentResult = Tuple[DatabaseResponse, Optional[List[str]], Optional[List[FileLink]]]  # result + doc_ids + file_links

from ....chat_model.model_settings import ENVIRONMENT, get_model_config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm
from .catalog_selection_prompt import get_catalog_selection_prompt
from .section_selection_prompt import get_section_selection_prompt
from .content_synthesis_prompt import (
    get_content_synthesis_prompt,
    # Removed unused individual synthesis prompt and schema
)

# Get module logger
logger = logging.getLogger(__name__)

# Removed unused token estimation constant

# Define the tool schema for research synthesis (consistent with wiki)
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
            section_id = section.get("section_id", "unknown")  # Get section_id
            section_name = section.get("section_name", "Untitled Section")
            section_summary = section.get("section_summary", "No summary available")
            # Include section_id in the formatted output
            formatted_docs += f"## Section ID: {section_id} | Name: {section_name}\n"
            formatted_docs += f"Summary: {section_summary}\n\n"
        formatted_docs += "---\n\n"
    return formatted_docs.strip()


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents (with full content) into a string optimized for LLM analysis.
    This is used for the final content synthesis step.
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

# Removed unused format_single_document_for_llm function

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
                SELECT id, document_name, document_description, file_link
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
                        "file_link": row[3] if row[3] else None,
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
                            "section_id": row[0], # Keep section_id
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
    section_id_selections: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    """
    Fetch the full content of specified sections from CAPM documents using section IDs.

    Args:
        section_id_selections: Dictionary mapping document names to lists of selected section IDs (as strings).

    Returns:
        List of documents with their selected sections (including name and content)
    """
    logger.info(
        f"Fetching CAPM content for selected section IDs: {section_id_selections}"
    )
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
            logger.debug(
                f"Querying content for doc: '{doc_name}', section IDs: {section_ids}"
            )
            if not section_ids:
                logger.warning(
                    f"Skipping document '{doc_name}' as no section IDs were selected."
                )
                continue

            # Assuming section_id in DB is integer
            try:
                int_section_ids = [int(sid) for sid in section_ids]
                placeholders = ",".join(["%s"] * len(int_section_ids))
                query_params = [doc_name] + int_section_ids
                id_column_name = "section_id"
            except ValueError:
                logger.error(
                    f"Could not convert all section IDs to integers for doc '{doc_name}': {section_ids}. Check LLM output format.",
                    exc_info=True,
                )
                continue

            with conn.cursor() as cur:
                try:
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
                    logger.debug(
                        f"Found {len(rows)} sections in DB for doc: '{doc_name}' with IDs: {int_section_ids}"
                    )
                    sections = []
                    for row in rows:
                        sections.append(
                            {
                                "section_name": (
                                    row[1] if row[1] else f"Section {row[0]}"
                                ),
                                "section_content": row[2],
                            }
                        )
                    if sections:
                        result.append({"document_name": doc_name, "sections": sections})
                    elif rows is None:
                        logger.error(
                            f"Database query returned None for doc: '{doc_name}' with IDs {int_section_ids}"
                        )

                except Exception as db_exec_err:
                    logger.error(
                        f"Database error executing query for doc '{doc_name}' with IDs {int_section_ids}: {db_exec_err}",
                        exc_info=True,
                    )

        logger.info(
            f"Retrieved CAPM content for {len(result)} documents from database"
        )
    except Exception as e:
        logger.error(
            f"Error during CAPM section content fetching loop: {str(e)}", exc_info=True
        )
    finally:
        if conn:
            conn.close()
    return result


# LLM interaction helper (Updated to match wiki template)
def get_completion(
    capability: str,
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    token: Optional[str] = None,
    database_name: Optional[str] = None,
    **kwargs: Any,  # Accept additional kwargs for tools, tool_choice etc.
) -> Tuple[Any, Optional[Dict[str, Any]]]:  # Returns (response_content, usage_details) tuple
    """
    Helper function to get a completion from the LLM synchronously.
    Handles standard completions and tool calls. Returns content and usage details.
    """
    usage_details = None # Initialize
    response = None # Initialize
    try:
        model_config = get_model_config(capability)
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        completion_cost = model_config["completion_token_cost"]
    except Exception as config_err:
        logger.error(
            f"Failed to get model configuration for capability '{capability}': {config_err}"
        )
        # Return error string and None for usage details
        return f"Error: Configuration error for model capability '{capability}'", None

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
        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)
        
        # Handle the new tuple format: (api_response, usage_details)
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Usage details for {database_name}: {usage_details}")
        else:
            # For backward compatibility in case it doesn't return a tuple
            response = result
            usage_details = None # Ensure usage_details is None if not returned
            logger.debug("call_llm did not return usage_details")
            
    except Exception as llm_err:
        logger.error(f"call_llm failed: {llm_err}", exc_info=True)
        # Return error string and None for usage details
        return f"Error: LLM call failed ({type(llm_err).__name__})", None

    if is_tool_call:
        logger.debug("Returning raw response object and usage details for tool call.")
        if (
            not response
            or not hasattr(response, "choices")
            or not response.choices
            or not hasattr(response.choices[0], "message")
            or not hasattr(response.choices[0].message, "tool_calls")
        ):
            logger.error("Invalid response structure received for tool call.")
            # Return error string and usage details (which might be None)
            return "Error: Invalid response structure for tool call.", usage_details
        # Return the response object and usage details
        return response, usage_details
    else:
        # Handle standard completion
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
        logger.debug("Returning extracted content string and usage details for standard completion.")
        # Return the content string and usage details
        return response_value, usage_details


# Updated select_relevant_documents with process monitoring
def select_relevant_documents(
    query: str,
    catalog: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_capm",
    process_monitor=None,
    stage_name: Optional[str] = None
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
        # Direct synchronous call - now returns a tuple
        selection_response_str, selection_usage = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=200,
            token=token,
            database_name=database_name,
        )

        # Track token usage from LLM calls
        if selection_usage:
            logger.debug(f"Document selection usage: {selection_usage}")
            # Update process monitor if available
            if process_monitor and stage_name:
                process_monitor.add_llm_call_details_to_stage(stage_name, selection_usage)
                process_monitor.add_stage_details(stage_name, task="document_selection")

        # Check if get_completion returned an error string
        if isinstance(selection_response_str, str) and selection_response_str.startswith("Error:"):
            logger.error(
                f"get_completion failed during document selection: {selection_response_str}"
            )
            return []

        try:
            selected_ids = json.loads(selection_response_str)
            if isinstance(selected_ids, list) and all(
                isinstance(i, str) for i in selected_ids
            ):
                logger.info(f"LLM selected CAPM document IDs: {selected_ids}")
                return selected_ids
            else:
                logger.error(
                    f"LLM response for CAPM selection was valid JSON but not list of strings: {selection_response_str}"
                )
                return []
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse CAPM selection LLM response as JSON, attempting fallback"
            )
            matches = re.findall(r'["\'](.*?)["\']', selection_response_str)
            valid_ids = [m.strip() for m in matches if m.strip()]
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


# Updated select_relevant_sections with process monitoring
def select_relevant_sections(
    query: str,
    documents_with_summaries: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_capm",
    process_monitor=None,
    stage_name: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    Use an LLM to select the most relevant sections from CAPM documents based on summaries.
    Returns: Dictionary mapping document names to lists of selected section IDs (as strings)
    """
    logger.info("Selecting relevant CAPM sections based on summaries")
    formatted_sections = format_sections_and_summaries_for_llm(documents_with_summaries)
    selection_prompt = get_section_selection_prompt(query, formatted_sections)

    try:
        logger.info(f"Initiating CAPM Section Selection API call (DB: {database_name})")
        # Direct synchronous call - now returns a tuple
        section_response_str, section_usage = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=500, # Increased max_tokens slightly
            token=token,
            database_name=database_name,
        )

        # Track token usage from LLM calls
        if section_usage:
            logger.debug(f"Section selection usage: {section_usage}")
            # Update process monitor if available
            if process_monitor and stage_name:
                process_monitor.add_llm_call_details_to_stage(stage_name, section_usage)
                process_monitor.add_stage_details(stage_name, task="section_selection")

        # Check if get_completion returned an error string
        if isinstance(section_response_str, str) and section_response_str.startswith("Error:"):
            logger.error(
                f"get_completion failed during section selection: {section_response_str}"
            )
            return {}

        try:
            # Attempt to extract JSON block using regex
            json_match = re.search(r"\{.*\}", section_response_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                selected_sections = json.loads(json_str)
            else:
                logger.error(
                    f"Could not find JSON block in LLM response for section selection. Response: {section_response_str}"
                )
                return {}

            # Validate the parsed structure (expecting dict[str, list[str]] where list contains section IDs)
            if isinstance(selected_sections, dict) and all(
                isinstance(doc_name, str)
                and isinstance(section_ids, list)
                and all(isinstance(sid, str) for sid in section_ids)
                for doc_name, section_ids in selected_sections.items()
            ):
                logger.info(f"LLM selected CAPM section IDs: {selected_sections}")
                return selected_sections
            else:
                logger.error(
                    f"LLM response for CAPM section ID selection was valid JSON but not in expected format (dict[str, list[str]]): {section_response_str}"
                )
                return {}
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse CAPM section selection LLM response as JSON. Error: {e}. Raw Response: {section_response_str}"
            )
            return {}
    except Exception as e:
        logger.error(
            f"Error during LLM CAPM section selection: {str(e)}", exc_info=True
        )
        return {}

# Removed unused estimate_token_size and synthesize_individual_document functions

# Updated synthesize_response_and_status with process monitoring (using single synthesis call)
def synthesize_response_and_status(
    query: str,
    documents: List[Dict[str, Any]], # Expects documents with full section content
    token: Optional[str] = None,
    database_name: str = "internal_capm",
    process_monitor=None,
    stage_name: Optional[str] = None
) -> ResearchResponse:
    """
    Use an LLM tool call to synthesize a detailed research response AND status summary for CAPM (synchronous).
    """
    logger.info(
        f"Synthesizing response and status for {database_name} using tool call."
    )
    default_error_status = f"❌ Error processing {database_name} query."
    default_no_info_status = f"📄 No relevant information found in {database_name}."
    default_research = f"No detailed research generated for {database_name} due to missing documents or error."
    error_result = {
        "detailed_research": default_research,
        "status_summary": default_error_status,
    }

    if not documents:
        logger.warning(f"No documents provided for {database_name} synthesis.")
        return {
            "detailed_research": default_research,
            "status_summary": default_no_info_status,
        }

    formatted_documents = format_documents_for_llm(documents) # Use formatter for full content
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_documents)

    try:
        logger.info(
            f"Initiating CAPM Synthesis API call (DB: {database_name})"
        )
        # Direct synchronous call - now returns a tuple
        synthesis_response_obj, synthesis_usage = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=2500, # Adjust as needed for CAPM content size
            temperature=0.2,
            token=token,
            database_name=database_name,
            tools=[SYNTHESIS_TOOL_SCHEMA],
            tool_choice={
                "type": "function",
                "function": {"name": SYNTHESIS_TOOL_SCHEMA["function"]["name"]},
            },
        )

        # Track token usage from synthesis
        if synthesis_usage:
            logger.debug(f"Research synthesis usage: {synthesis_usage}")
            # Update process monitor if available
            if process_monitor and stage_name:
                process_monitor.add_llm_call_details_to_stage(stage_name, synthesis_usage)
                process_monitor.add_stage_details(stage_name, task="research_synthesis")

        # Check if get_completion returned an error string in the response part
        if isinstance(synthesis_response_obj, str) and synthesis_response_obj.startswith("Error:"):
            logger.error(
                f"get_completion failed for {database_name} synthesis: {synthesis_response_obj}"
            )
            error_result["detailed_research"] = synthesis_response_obj
            return error_result

        # Process Tool Call Response
        if (
            hasattr(synthesis_response_obj, "choices")
            and synthesis_response_obj.choices
            and hasattr(synthesis_response_obj.choices[0], "message")
            and synthesis_response_obj.choices[0].message
            and hasattr(synthesis_response_obj.choices[0].message, "tool_calls")
            and synthesis_response_obj.choices[0].message.tool_calls
        ):

            tool_call = synthesis_response_obj.choices[0].message.tool_calls[0]
            if tool_call.function.name == SYNTHESIS_TOOL_SCHEMA["function"]["name"]:
                arguments_str = tool_call.function.arguments
                logger.debug(f"Received tool arguments string: {arguments_str}")
                try:
                    arguments = json.loads(arguments_str)
                    if (
                        "status_summary" in arguments
                        and "detailed_research" in arguments
                    ):
                        logger.info(
                            f"Successfully parsed synthesis tool call for {database_name}."
                        )
                        status = arguments.get("status_summary", default_error_status)
                        research = arguments.get("detailed_research", default_research)
                        if not isinstance(status, str): status = default_error_status
                        if not isinstance(research, str): research = default_research
                        return {"status_summary": status, "detailed_research": research}
                    else:
                        logger.error(
                            f"Missing required keys in parsed tool arguments for {database_name}: {arguments}"
                        )
                        error_result["detailed_research"] = "Error: Tool call arguments missing required keys."
                        return error_result
                except json.JSONDecodeError as json_err:
                    logger.error(
                        f"Failed to parse tool arguments JSON for {database_name}: {json_err}. Arguments: {arguments_str}"
                    )
                    error_result["detailed_research"] = f"Error: Failed to parse tool arguments JSON - {json_err}"
                    return error_result
            else:
                logger.error(
                    f"Unexpected tool called for {database_name}: {tool_call.function.name}"
                )
                error_result["detailed_research"] = f"Error: Unexpected tool called: {tool_call.function.name}"
                return error_result
        else:
            logger.error(
                f"No tool call received from LLM for {database_name} synthesis, despite being requested."
            )
            content = ""
            if (
                hasattr(synthesis_response_obj, "choices")
                and synthesis_response_obj.choices
                and hasattr(synthesis_response_obj.choices[0], "message")
                and synthesis_response_obj.choices[0].message
                and hasattr(synthesis_response_obj.choices[0].message, "content")
                and synthesis_response_obj.choices[0].message.content
            ):
                content = synthesis_response_obj.choices[0].message.content
                logger.warning(
                    f"LLM returned content instead of tool call: {content[:200]}..."
                )
                error_result["detailed_research"] = f"Error: LLM returned text instead of tool call. Content: {content[:200]}..."
            else:
                error_result["detailed_research"] = "Error: No tool call or content received from LLM."
            return error_result

    except Exception as e:
        logger.error(
            f"Exception during synthesis tool call for {database_name}: {str(e)}",
            exc_info=True,
        )
        error_result["detailed_research"] = f"Error during synthesis: {str(e)}"
        return error_result


# Updated query_database_sync with process monitoring and CAPM workflow
def query_database_sync(
    query: str, scope: str, token: Optional[str] = None, process_monitor=None, query_stage_name: Optional[str] = None
) -> SubagentResult:
    """
    Synchronously query the Internal CAPM database based on the specified scope.
    Includes document selection, section selection, and content synthesis.
    """
    logger.info(f"Querying Internal CAPM database (sync): '{query}' with scope: {scope}")
    database_name = "internal_capm"
    default_error_status = "❌ Error during query processing."
    selected_doc_ids: Optional[List[str]] = None
    file_links: Optional[List[FileLink]] = None  # Initialize file links
    # Use the passed-in stage name if available, otherwise default
    stage_name = query_stage_name or f"db_query_{database_name}_unknown"
    logger.debug(f"Using process monitor stage name: {stage_name}")
    # Removed manual tracking variables

    try:
        # 1. Fetch Catalog
        catalog = fetch_capm_catalog()
        logger.info(f"Retrieved {len(catalog)} total CAPM catalog entries")
        if not catalog:
            response: DatabaseResponse = [] if scope == "metadata" else {
                "detailed_research": "No documents found in the Internal CAPM database catalog.",
                "status_summary": "📄 No documents found in catalog.",
            }
            return response, None, None  # Return None for both doc_ids and file_links

        # 2. Select Relevant Documents
        selected_doc_ids = select_relevant_documents(
            query, catalog, token, database_name, process_monitor, stage_name
        )
        logger.info(f"LLM selected {len(selected_doc_ids)} relevant CAPM document IDs: {selected_doc_ids}")

        if not selected_doc_ids:
            response: DatabaseResponse = [] if scope == "metadata" else {
                "detailed_research": "LLM did not select any relevant documents from the catalog based on the query.",
                "status_summary": "📄 No relevant documents selected by LLM.",
            }
            if process_monitor:
                process_monitor.add_stage_details(stage_name, result_count=0, document_ids=[])
            return response, [], None  # Return empty list for doc IDs and None for file_links

        # 3. Process based on scope
        if scope == "metadata":
            selected_items = [item for item in catalog if item.get("id") in selected_doc_ids]
            logger.info(f"Returning {len(selected_items)} selected CAPM metadata items.")
            
            # Collect file links from selected items
            file_links = []
            for item in selected_items:
                if item.get("file_link"):
                    file_links.append({
                        "file_link": item["file_link"],
                        "document_name": item.get("document_name", "Unknown")
                    })
            
            if process_monitor:
                process_monitor.add_stage_details(stage_name, result_count=len(selected_items), document_ids=selected_doc_ids)
            return selected_items, selected_doc_ids, file_links

        elif scope == "research":
            # Collect file links from catalog before proceeding
            file_links = []
            for item in catalog:
                if item.get("id") in selected_doc_ids and item.get("file_link"):
                    file_links.append({
                        "file_link": item["file_link"],
                        "document_name": item.get("document_name", "Unknown")
                    })
            
            # 4. Fetch Sections and Summaries for Selected Documents
            documents_with_summaries = fetch_document_sections_and_summaries(selected_doc_ids)
            if not documents_with_summaries:
                response = {
                    "detailed_research": "Could not retrieve sections and summaries for the selected CAPM documents.",
                    "status_summary": "❌ Error retrieving document sections.",
                }
                if process_monitor:
                    process_monitor.add_stage_details(stage_name, error="Could not retrieve document sections", document_ids=selected_doc_ids)
                return response, selected_doc_ids, file_links

            # 5. Select Relevant Sections based on Summaries
            section_selections = select_relevant_sections(
                query, documents_with_summaries, token, database_name, process_monitor, stage_name
            ) # Returns Dict[doc_name, List[section_id_str]]
            
            # Filter out documents with no selected sections
            valid_section_selections = {
                doc_name: sec_ids for doc_name, sec_ids in section_selections.items() if sec_ids
            }

            if not valid_section_selections:
                logger.warning("LLM did not select any relevant sections.")
                response = {
                    "detailed_research": "LLM did not select any relevant sections from the CAPM documents based on the query.",
                    "status_summary": "📄 No relevant sections selected by LLM.",
                }
                if process_monitor:
                     process_monitor.add_stage_details(stage_name, error="No relevant sections selected", document_ids=selected_doc_ids)
                return response, selected_doc_ids, file_links

            # 6. Fetch Full Content for Selected Sections
            documents_with_content = fetch_section_content(valid_section_selections)
            if not documents_with_content:
                response = {
                    "detailed_research": "Could not retrieve content for the selected CAPM sections.",
                    "status_summary": "❌ Error retrieving section content.",
                }
                if process_monitor:
                    process_monitor.add_stage_details(stage_name, error="Could not retrieve section content", document_ids=selected_doc_ids)
                return response, selected_doc_ids, file_links

            # 7. Synthesize Final Response
            research_result = synthesize_response_and_status(
                query, documents_with_content, token, database_name, process_monitor, stage_name
            )

            # Log final details for the stage
            if process_monitor:
                process_monitor.add_stage_details(
                    stage_name,
                    result_count=len(documents_with_content), # Count of docs with synthesized content
                    document_ids=selected_doc_ids, # Original selected doc IDs
                    status_summary=research_result.get("status_summary", "")
                )
            return research_result, selected_doc_ids, file_links

        else:
            logger.error(f"Invalid scope provided to internal_capm subagent: {scope}")
            raise ValueError(f"Invalid scope: {scope}")

    except Exception as e:
        error_msg = f"Error querying Internal CAPM database (scope: {scope}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        response: DatabaseResponse = [] if scope == "metadata" else {
            "detailed_research": f"**Error processing request for Internal CAPM:** {str(e)}",
            "status_summary": default_error_status,
        }
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=str(e), document_ids=selected_doc_ids)
        return response, selected_doc_ids, file_links
