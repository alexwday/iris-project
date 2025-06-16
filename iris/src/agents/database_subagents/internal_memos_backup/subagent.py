# internal_memos/subagent.py
"""
Internal Memos Subagent (Async Version)

This module handles queries to the Internal Memos database asynchronously,
including catalog retrieval, document selection, content retrieval,
and response synthesis (generating detailed research and status summary using tool calls).

Functions:
    query_database_sync: Synchronously query the Internal Memos database
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Union, cast, Tuple

# Define response types consistent with database_router
MetadataResponse = List[Dict[str, Any]]
# ResearchResponse is now a dictionary containing detailed research and status
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
# Updated to include file links
FileLink = Dict[str, str]  # Contains 'file_link' and 'document_name'
SubagentResult = Tuple[DatabaseResponse, Optional[List[str]], Optional[List[FileLink]]]  # result + doc_ids + file_links

from ....initial_setup.env_config import config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm
from .catalog_selection_prompt import get_catalog_selection_prompt
from .content_synthesis_prompt import (
    get_content_synthesis_prompt,
)  # Will need simplification

# Get module logger
logger = logging.getLogger(__name__)


# Formatting functions remain synchronous as they are CPU-bound
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


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a string that is optimized for LLM analysis.
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


# Database interaction functions (now synchronous)
def fetch_memos_catalog() -> List[Dict[str, Any]]:
    """
    Fetch the full internal Memos catalog from the database synchronously.
    """
    logger.info(f"Fetching full Memos catalog (environment: {config.ENVIRONMENT})")
    conn = connect_to_db()
    catalog_records: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for Memos catalog")
        return catalog_records
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, document_name, document_description
                FROM apg_catalog
                WHERE document_source = 'internal_memo'
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
            f"Retrieved {len(catalog_records)} Memos catalog entries from database"
        )
    except Exception as e:
        logger.error(f"Error fetching Memos catalog from database: {str(e)}")
    finally:
        if conn:
            conn.close()
    return catalog_records


def fetch_document_content(doc_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch the content of specified Memos documents from the database synchronously.
    """
    logger.info(f"Fetching Memos content for documents: {doc_ids}")
    if not doc_ids:
        logger.warning("No Memos document IDs to fetch")
        return []
    conn = connect_to_db()
    result: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for Memos content")
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
                AND document_source = 'internal_memo'
            """,
                doc_ids,
            )
            for row in cur.fetchall():
                doc_names[row[0]] = row[1]
            logger.info(f"Found {len(doc_names)} Memos documents for IDs: {doc_ids}")

        for doc_id, doc_name in doc_names.items():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT section_id, section_name, section_content
                    FROM apg_content
                    WHERE document_source = 'internal_memo'
                    AND document_name = %s
                    ORDER BY section_id
                """,
                    (doc_name,),
                )
                sections = []
                for row in cur.fetchall():
                    sections.append(
                        {
                            "section_name": (row[1] if row[1] else f"Section {row[0]}"),
                            "section_content": row[2],
                        }
                    )
                if sections:
                    result.append({"document_name": doc_name, "sections": sections})
        logger.info(f"Retrieved Memos content for {len(result)} documents from database")
    except Exception as e:
        logger.error(f"Error fetching Memos document content from database: {str(e)}")
    finally:
        if conn:
            conn.close()
    return result


# LLM interaction helper (Updated for Tool Calling, now synchronous)
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
        model_config = config.get_model_config(capability)
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
        "database_name": database_name, # Pass database_name from caller
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


def select_relevant_documents(
    query: str,
    catalog: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_memos", # Default to memos
    process_monitor=None, # Added process_monitor
    stage_name: Optional[str] = None # Added stage_name
) -> List[str]:
    """
    Use an LLM to select the most relevant Memos documents from the catalog based on the query (synchronous).
    """
    logger.info("Selecting relevant Memos documents from catalog")
    formatted_catalog = format_catalog_for_llm(catalog)
    selection_prompt = get_catalog_selection_prompt(
        query, formatted_catalog
    )  # Assumes this prompt asks for JSON list

    try:
        logger.info(
            f"Initiating Memos Document Selection API call (DB: {database_name})"
        )  # Added contextual log
        # Direct synchronous call - now returns a tuple
        selection_response_str, selection_usage = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=200,
            token=token,
            database_name=database_name # Pass the specific database name
        )

        # Track token usage from LLM calls
        if selection_usage:
            logger.debug(f"Document selection usage: {selection_usage}")
            # Update process monitor if available
            if process_monitor and stage_name: # Check if monitor and stage_name exist
                process_monitor.add_llm_call_details_to_stage(stage_name, selection_usage)
                process_monitor.add_stage_details(stage_name, task="document_selection") # Add task detail

        # Check if get_completion returned an error string
        if isinstance(selection_response_str, str) and selection_response_str.startswith("Error:"):
            logger.error(
                f"get_completion failed during document selection: {selection_response_str}"
            )
            return []

        try:
            # Assuming selection_response_str is the string content now
            selected_ids = json.loads(selection_response_str)
            if isinstance(selected_ids, list) and all(
                isinstance(i, str) for i in selected_ids
            ):
                logger.info(f"LLM selected Memos document IDs: {selected_ids}")
                return selected_ids
            else:
                logger.error(
                    f"LLM response was valid JSON but not a list of strings: {selection_response_str}"
                )
                return []
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse LLM response as JSON, attempting fallback extraction"
            )
            # More comprehensive regex to extract document IDs
            matches = re.findall(r'["\'](.*?)["\']', selection_response_str)
            # Accept any ID, not just digits, since IDs might be strings
            # Rewrite list comprehension as a for loop to avoid potential hidden character issues
            valid_ids = []
            for m in matches:
                stripped_m = m.strip()
                if stripped_m:
                    valid_ids.append(stripped_m)
            # End rewrite
            if valid_ids:
                logger.warning(
                    f"Extracted Memos document IDs using fallback regex: {valid_ids}"
                )
                return valid_ids
            logger.error("Could not extract Memos document IDs from response using fallback.")
            return []
    except Exception as e:
        logger.error(f"Error during LLM Memos document selection: {str(e)}")
        return []


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


# Updated function using Tool Calling (now synchronous)
def synthesize_response_and_status(
    query: str,
    documents: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_memos", # Default to memos
    process_monitor=None, # Added process_monitor
    stage_name: Optional[str] = None # Added stage_name
) -> ResearchResponse: # Return only ResearchResponse
    """
    Use an LLM tool call to synthesize a detailed research response AND status summary for Memos (synchronous).
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
    # synthesis_usage = None # No longer need to track usage here

    if not documents:
        logger.warning(f"No documents provided for {database_name} synthesis.")
        return {
            "detailed_research": default_research,
            "status_summary": default_no_info_status,
        } # Removed None return

    formatted_documents = format_documents_for_llm(documents)
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_documents)

    try:
        logger.info(
            f"Initiating Memos Synthesis API call (DB: {database_name})"
        )  # Added contextual log
        # Direct synchronous call - now returns a tuple
        synthesis_response_obj, synthesis_usage = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=2500,
            temperature=0.2,
            token=token,
            database_name=database_name, # Pass the specific database name
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
            if process_monitor and stage_name: # Check if monitor and stage_name exist
                process_monitor.add_llm_call_details_to_stage(stage_name, synthesis_usage)
                process_monitor.add_stage_details(stage_name, task="research_synthesis") # Add task detail

        # Check if get_completion returned an error string in the response part
        if isinstance(synthesis_response_obj, str) and synthesis_response_obj.startswith("Error:"):
            logger.error(
                f"get_completion failed for {database_name} synthesis: {synthesis_response_obj}"
            )
            error_result["detailed_research"] = synthesis_response_obj
            return error_result # Return error dict

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
                        # Ensure values are strings, default if not (though schema should enforce)
                        status = arguments.get("status_summary", default_error_status)
                        research = arguments.get("detailed_research", default_research)
                        if not isinstance(status, str):
                            status = default_error_status
                        if not isinstance(research, str):
                            research = default_research
                        return {"status_summary": status, "detailed_research": research} # Return result dict
                    else:
                        logger.error(
                            f"Missing required keys in parsed tool arguments for {database_name}: {arguments}"
                        )
                        error_result["detailed_research"] = (
                            "Error: Tool call arguments missing required keys."
                        )
                        return error_result
                except json.JSONDecodeError as json_err:
                    logger.error(
                        f"Failed to parse tool arguments JSON for {database_name}: {json_err}. Arguments: {arguments_str}"
                    )
                    error_result["detailed_research"] = (
                        f"Error: Failed to parse tool arguments JSON - {json_err}"
                    )
                    return error_result
            else:
                logger.error(
                    f"Unexpected tool called for {database_name}: {tool_call.function.name}"
                )
                error_result["detailed_research"] = (
                    f"Error: Unexpected tool called: {tool_call.function.name}"
                )
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
                error_result["detailed_research"] = (
                    f"Error: LLM returned text instead of tool call. Content: {content[:200]}..."
                )
            else:
                error_result["detailed_research"] = (
                    "Error: No tool call or content received from LLM."
                )
            return error_result

    except Exception as e:
        logger.error(
            f"Exception during synthesis tool call for {database_name}: {str(e)}",
            exc_info=True,
        )
        error_result["detailed_research"] = f"Error during synthesis: {str(e)}"
        return error_result


def query_database_sync(
    query: str, scope: str, token: Optional[str] = None, process_monitor=None, query_stage_name: Optional[str] = None
) -> SubagentResult: # Added query_stage_name
    """
    Synchronously query the Internal Memos database based on the specified scope.
    
    Args:
        query: The user's query to process
        scope: The type of data to return ("metadata" or "research")
        token: Optional OAuth token
        process_monitor: Optional process monitor to track token usage
        query_stage_name (str, optional): The specific stage name for this query instance
                                          provided by the caller (e.g., worker).
        
    Returns:
        Tuple containing the main database response, a list of selected document IDs (or None),
        and a list of file links (or None).
    """
    logger.info(
        f"Querying Internal Memos database (sync): '{query}' with scope: {scope}"
    )
    database_name = "internal_memos" # Set database name
    default_error_status = "❌ Error during query processing."
    selected_doc_ids: Optional[List[str]] = None  # Initialize
    file_links: Optional[List[FileLink]] = None  # Initialize file links
    # Use the passed-in stage name if available, otherwise default
    stage_name = query_stage_name or f"db_query_{database_name}_unknown"
    logger.debug(f"Using process monitor stage name: {stage_name}")
    # REMOVED manual tracking variables and list

    try:
        # Direct synchronous calls
        catalog = fetch_memos_catalog() # Use memos function
        logger.info(f"Retrieved {len(catalog)} total Memos catalog entries")
        if not catalog:
            response: DatabaseResponse
            if scope == "metadata":
                response = []
            else:
                response = {
                    "detailed_research": "No documents found in the Internal Memos database catalog.",
                    "status_summary": "📄 No documents found in catalog.",
                }
            return response, selected_doc_ids, file_links  # Return empty response and None IDs/links

        # Select documents using the updated helper function
        selected_doc_ids = select_relevant_documents(
            query, catalog, token, database_name, process_monitor, stage_name
        )
        
        logger.info(
            f"LLM selected {len(selected_doc_ids)} relevant Memos document IDs: {selected_doc_ids}"
        )
        if not selected_doc_ids:
            response: DatabaseResponse
            if scope == "metadata":
                response = []
            else:
                response = {
                    "detailed_research": "LLM did not select any relevant documents from the catalog based on the query.",
                    "status_summary": "📄 No relevant documents selected by LLM.",
                }
            
            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(stage_name, 
                    result_count=0, 
                    document_ids=selected_doc_ids
                )
                
            return response, selected_doc_ids, file_links  # Return empty response and empty IDs list/links

        # Process based on scope
        if scope == "metadata":
            selected_items = [item for item in catalog if item.get("id") in selected_doc_ids]
            logger.info(
                f"Returning {len(selected_items)} selected Memos metadata items."
            )
            
            # Collect file links from selected items (including blank ones)
            file_links = []
            for item in selected_items:
                file_links.append({
                    "file_link": item.get("file_link", ""),  # Use empty string if None
                    "document_name": item.get("document_name", "Unknown")
                })
            
            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(stage_name, 
                    result_count=len(selected_items), 
                    document_ids=selected_doc_ids
                )
                
            return selected_items, selected_doc_ids, file_links  # Return metadata, IDs, and file links
            
        elif scope == "research":
            # Collect file links from catalog before fetching content (including blank ones)
            file_links = []
            for item in catalog:
                if item.get("id") in selected_doc_ids:
                    file_links.append({
                        "file_link": item.get("file_link", ""),  # Use empty string if None
                        "document_name": item.get("document_name", "Unknown")
                    })
            
            # Fetch content and synthesize
            documents = fetch_document_content(selected_doc_ids) # Use memos function
            logger.info(
                f"Retrieved content for {len(documents)} Memos documents for research."
            )
            
            # Get research synthesis using the updated helper function
            # synthesize_response_and_status now returns only the ResearchResponse dict
            research_result = synthesize_response_and_status(
                query, documents, token, database_name, process_monitor, stage_name
            )
            
            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(stage_name, 
                    result_count=len(documents), 
                    document_ids=selected_doc_ids,
                    status_summary=research_result.get("status_summary", "")
                )
            
            return research_result, selected_doc_ids, file_links  # Return research result, IDs, and file links
            
        else:
            logger.error(f"Invalid scope provided to internal_memos subagent: {scope}")
            raise ValueError(f"Invalid scope: {scope}")  # Let the error propagate

    except Exception as e:
        error_msg = f"Error querying Internal Memos database (scope: {scope}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        response: DatabaseResponse
        if scope == "metadata":
            response = []
        else:
            response = {
                "detailed_research": f"**Error processing request for Internal Memos:** {str(e)}",
                "status_summary": default_error_status,
            }
            
            # Add details to process monitor before returning
        if process_monitor: # Check if monitor exists before adding error details
            process_monitor.add_stage_details(stage_name, 
                error=str(e),
                document_ids=selected_doc_ids # Keep doc IDs if available
            )
            
        # Return error response and potentially selected IDs/links if selection succeeded before error
        return response, selected_doc_ids, file_links
