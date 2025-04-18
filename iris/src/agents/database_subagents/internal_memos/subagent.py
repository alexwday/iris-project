# internal_memos/subagent.py
"""
Internal Memos Subagent

This module handles queries to the Internal Memos database synchronously,
including catalog retrieval, document selection, content retrieval,
and response synthesis (generating detailed research and status summary using tool calls).

Functions:
    query_database_sync: Synchronously query the Internal Memos database
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Union, cast

# Define response types consistent with database_router
MetadataResponse = List[Dict[str, Any]]
# ResearchResponse is now a dictionary containing detailed research and status
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]

from ....chat_model.model_settings import ENVIRONMENT, get_model_config
from ....initial_setup.db_config import connect_to_db
from ....llm_connectors.rbc_openai import call_llm
from .catalog_selection_prompt import get_catalog_selection_prompt
from .content_synthesis_prompt import (
    get_content_synthesis_prompt,
)

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
    logger.info(f"Fetching full Memos catalog (environment: {ENVIRONMENT})")
    conn = connect_to_db(ENVIRONMENT)
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
    conn = connect_to_db(ENVIRONMENT)
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
        logger.info(
            f"Retrieved Memos content for {len(result)} documents from database"
        )
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
) -> Any:  # Returns the raw OpenAI response object or content string or error string
    """
    Helper function to get a completion from the LLM synchronously.
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
    database_name: str = "internal_memo",
) -> List[str]:
    """
    Use an LLM to select the most relevant Memo documents synchronously.
    """
    logger.info("Selecting relevant Memo documents from catalog")
    formatted_catalog = format_catalog_for_llm(catalog)
    selection_prompt = get_catalog_selection_prompt(
        query, formatted_catalog
    )  # Assumes this prompt asks for JSON list

    try:
        logger.info(
            f"Initiating Memo Document Selection API call (DB: {database_name})"
        )  # Added contextual log
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
                logger.info(f"LLM selected Memo document IDs: {selected_ids}")
                return selected_ids
            else:
                logger.error(
                    f"LLM response for Memo selection was valid JSON but not list of strings: {response_str}"
                )
                return []
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse Memo selection LLM response as JSON, attempting fallback"
            )
            matches = re.findall(r'"([^"]+)"', response_str)
            # Accept any ID, not just digits, as Memo IDs might be strings
            valid_ids = [m.strip() for m in matches if m.strip()]
            if valid_ids:
                logger.warning(
                    f"Extracted Memo document IDs using fallback regex: {valid_ids}"
                )
                return valid_ids
            logger.error(
                "Could not extract Memo document IDs from response using fallback."
            )
            return []
    except Exception as e:
        logger.error(f"Error during LLM Memo document selection: {str(e)}")
        return []


# Define the tool schema for research synthesis (Copied from internal_wiki/par/icfr)
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
    database_name: str = "internal_memo",
) -> ResearchResponse:
    """
    Use an LLM tool call to synthesize a detailed research response AND status summary for Memo (synchronous).
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

    formatted_documents = format_documents_for_llm(documents)
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_documents)

    try:
        logger.info(
            f"Initiating Memo Synthesis API call (DB: {database_name})"
        )  # Added contextual log
        # Direct synchronous call
        response_obj = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=2500,
            temperature=0.2,
            token=token,
            database_name=database_name,
            tools=[SYNTHESIS_TOOL_SCHEMA],
            tool_choice={
                "type": "function",
                "function": {"name": SYNTHESIS_TOOL_SCHEMA["function"]["name"]},
            },
        )

        if isinstance(response_obj, str) and response_obj.startswith("Error:"):
            logger.error(
                f"get_completion failed for {database_name} synthesis: {response_obj}"
            )
            error_result["detailed_research"] = response_obj
            return error_result

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
                        if not isinstance(status, str):
                            status = default_error_status
                        if not isinstance(research, str):
                            research = default_research
                        return {"status_summary": status, "detailed_research": research}
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
    query: str, scope: str, token: Optional[str] = None
) -> DatabaseResponse:
    """
    Synchronously query the Internal Memo database based on the specified scope.
    """
    logger.info(
        f"Querying Internal Memo database (sync): '{query}' with scope: {scope}"
    )
    database_name = "internal_memo"
    default_error_status = "❌ Error during query processing."

    try:
        # Direct synchronous calls
        catalog = (
            fetch_memos_catalog()
        )  # Function name kept for consistency, queries 'internal_memo'
        logger.info(f"Retrieved {len(catalog)} total Memo catalog entries")
        if not catalog:
            if scope == "metadata":
                return []
            else:
                return {
                    "detailed_research": "No documents found in the Internal Memo database catalog.",
                    "status_summary": "📄 No documents found in catalog.",
                }

        # Select documents
        doc_ids = select_relevant_documents(  # Function name kept for consistency, uses 'internal_memo' db name
            query, catalog, token, database_name=database_name
        )
        logger.info(
            f"LLM selected {len(doc_ids)} relevant Memo document IDs: {doc_ids}"
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
            selected_items = [item for item in catalog if item.get("id") in doc_ids]
            logger.info(
                f"Returning {len(selected_items)} selected Memo metadata items."
            )
            return selected_items
        elif scope == "research":
            # Fetch content and synthesize
            documents = fetch_document_content(
                doc_ids
            )  # Function name kept for consistency, queries 'internal_memo'
            logger.info(
                f"Retrieved content for {len(documents)} Memo documents for research."
            )
            research_result = synthesize_response_and_status(  # Function name kept for consistency, uses 'internal_memo' db name
                query, documents, token, database_name=database_name
            )
            return research_result
        else:
            logger.error(f"Invalid scope provided to internal_memo subagent: {scope}")
            raise ValueError(f"Invalid scope: {scope}")

    except Exception as e:
        error_msg = f"Error querying Internal Memo database (scope: {scope}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            return []
        else:
            return {
                "detailed_research": f"**Error processing request for Internal Memo:** {str(e)}",
                "status_summary": default_error_status,
            }
