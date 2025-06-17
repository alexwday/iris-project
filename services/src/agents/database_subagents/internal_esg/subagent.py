# internal_esg/subagent.py
"""
Internal ESG Subagent (Async Version)

This module handles queries to the Internal ESG database asynchronously,
including catalog retrieval, document selection, content retrieval,
and response synthesis (generating detailed research and status summary using tool calls).

Functions:
    query_database_sync: Synchronously query the Internal ESG database
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
# Updated to include file links, page/section references, and section content
FileLink = Dict[str, str]  # Contains 'file_link' and 'document_name'
PageSectionRefs = Dict[int, List[int]]  # Maps page numbers to lists of section IDs
SectionContentMap = Dict[str, str]  # Maps "page_num:section_id" to section content
# Reference index for inline citations
ReferenceIndex = Dict[str, Dict[str, Any]]  # Maps reference ID to reference details
SubagentResult = Tuple[
    DatabaseResponse,
    Optional[List[str]],
    Optional[List[FileLink]],
    Optional[PageSectionRefs],
    Optional[SectionContentMap],
    Optional[ReferenceIndex],
]  # result + doc_ids + file_links + page_sections + section_content + reference_index

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


def build_structured_reference_index(
    page_numbers: List[int], 
    file_links: List[FileLink], 
    section_content_map: Dict[str, str]
) -> ReferenceIndex:
    """
    Build reference index from structured data instead of parsing citations.
    Creates simple page-based references with combined section text for highlighting.

    Args:
        page_numbers: List of page numbers referenced in the research
        file_links: File links for the documents
        section_content_map: Maps "page_num:section_id" to section content

    Returns:
        Reference index mapping ref_id to {file_link, page, doc_name, highlight_text}
    """
    import re

    logger.error(f"DEBUG STRUCTURED_REF: Building reference index from {len(page_numbers)} pages")
    logger.error(f"DEBUG STRUCTURED_REF: file_links: {file_links}")
    logger.error(f"DEBUG STRUCTURED_REF: section_content_map keys: {list(section_content_map.keys())}")

    # Build document name to file link mapping
    doc_to_file = {}
    for link_info in file_links:
        doc_name = link_info.get("document_name", "")
        file_link = link_info.get("file_link", "")
        if doc_name and file_link:
            doc_to_file[doc_name] = file_link

    logger.error(f"DEBUG STRUCTURED_REF: doc_to_file mapping: {doc_to_file}")

    reference_index = {}
    ref_counter = 1

    # Create one reference per page
    for page_num in sorted(set(page_numbers)):  # Remove duplicates and sort
        # Find all sections for this page in section_content_map
        page_sections = []
        for key, content in section_content_map.items():
            if key.startswith(f"{page_num}:"):
                page_sections.append(content)

        # Combine all section content for this page
        combined_content = " ".join(page_sections)
        
        # Clean the content for highlighting
        content_clean = re.sub(r"[|*#`_~\[\]{}\\<>@$%^&+=]", " ", combined_content)
        content_clean = re.sub(r'["\']', "", content_clean)
        content_clean = re.sub(r"\s+", " ", content_clean).strip()
        
        # Use first file_link available (assuming single document for now)
        file_link = ""
        doc_name = "Unknown Document"
        if file_links:
            file_link = file_links[0].get("file_link", "")
            doc_name = file_links[0].get("document_name", "Unknown Document")

        ref_id = str(ref_counter)
        reference_index[ref_id] = {
            "doc_name": doc_name,
            "file_link": file_link,
            "page": page_num,
            "section_name": f"Page {page_num}",
            "highlight_text": content_clean,
        }

        logger.error(f"DEBUG STRUCTURED_REF: Created ref {ref_id} for page {page_num}, file_link='{file_link}', highlight_length={len(content_clean)}")
        ref_counter += 1

    logger.error(f"DEBUG STRUCTURED_REF: Final reference_index: {reference_index}")
    return reference_index


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a string that is optimized for LLM analysis.
    Now reconstructs documents from page/section records in correct order and formats
    for clear section separation with page/section references that the LLM can cite.
    """
    formatted_docs = ""
    for doc in documents:
        doc_name = doc.get("document_name", "Untitled")
        formatted_docs += f"# {doc_name}\n\n"

        # Get page_sections and reconstruct document in proper order
        page_sections = doc.get("page_sections", [])
        if not page_sections:
            formatted_docs += "No content available.\n\n"
            continue

        # Group sections by page number for clear organization
        pages_dict: Dict[int, List[Dict[str, Any]]] = {}
        for section in page_sections:
            page_num = section.get("page_number", 0)
            if page_num not in pages_dict:
                pages_dict[page_num] = []
            pages_dict[page_num].append(section)

        # Process pages in order
        for page_num in sorted(pages_dict.keys()):
            formatted_docs += f"## Page {page_num}\n\n"

            # Process sections within the page in order
            page_sections_list = sorted(
                pages_dict[page_num], key=lambda x: x.get("section_id", 0)
            )

            for section in page_sections_list:
                section_id = section.get("section_id", 0)
                section_content = section.get("section_content", "No content available")
                section_name = section.get("section_name", f"Section {section_id}")
                section_summary = section.get(
                    "section_summary", f"Page {page_num}, Section {section_id}"
                )

                # Format each section with CLEAR metadata for LLM reference
                logger.info(
                    f"ESG DEBUG: Formatting section - Page {page_num}, Section {section_id}, Name: '{section_name}'"
                )
                formatted_docs += (
                    f"### [PAGE: {page_num}, SECTION: {section_id}] {section_name}\n"
                )
                formatted_docs += f"**Section Summary:** {section_summary}\n\n"
                # Add explicit instruction about section naming for citations
                if section_name and not section_name.startswith("Section "):
                    formatted_docs += f"**CITATION NOTE: When referencing this content, use the section name '{section_name}' rather than just the section number.**\n\n"
                    logger.info(
                        f"ESG DEBUG: Added citation note for descriptive section name: '{section_name}'"
                    )
                else:
                    logger.info(
                        f"ESG DEBUG: Generic section name detected: '{section_name}' - LLM should extract from content"
                    )
                formatted_docs += f"{section_content}\n\n"

            formatted_docs += "---\n\n"

    return formatted_docs.strip()


# Database interaction functions (now synchronous)
def fetch_esg_catalog() -> List[Dict[str, Any]]:
    """
    Fetch the full internal ESG catalog from the database synchronously.
    """
    logger.info(f"Fetching full ESG catalog (environment: {config.ENVIRONMENT})")
    conn = connect_to_db()
    catalog_records: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for ESG catalog")
        return catalog_records
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, document_name, document_description, file_link
                FROM apg_catalog
                WHERE document_source = 'internal_esg'
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
            f"Retrieved {len(catalog_records)} ESG catalog entries from database"
        )
    except Exception as e:
        logger.error(f"Error fetching ESG catalog from database: {str(e)}")
    finally:
        if conn:
            conn.close()
    return catalog_records


def fetch_esg_content(doc_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch the content of specified ESG documents from the database synchronously.
    Now retrieves all page/section records with page_number, section_id, section_summary fields.
    """
    logger.info(f"Fetching ESG content for documents: {doc_ids}")
    if not doc_ids:
        logger.warning("No ESG document IDs to fetch")
        return []
    conn = connect_to_db()
    result: List[Dict[str, Any]] = []
    if not conn:
        logger.error("Failed to connect to database for ESG content")
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
                AND document_source = 'internal_esg'
            """,
                doc_ids,
            )
            for row in cur.fetchall():
                doc_names[row[0]] = row[1]
            logger.info(f"Found {len(doc_names)} ESG documents for IDs: {doc_ids}")

        for doc_id, doc_name in doc_names.items():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT section_id, section_name, section_content, page_number, section_summary
                    FROM apg_content
                    WHERE document_source = 'internal_esg'
                    AND document_name = %s
                    ORDER BY page_number, section_id
                """,
                    (doc_name,),
                )
                page_sections = []
                for row in cur.fetchall():
                    page_sections.append(
                        {
                            "section_id": row[0],
                            "section_name": (row[1] if row[1] else f"Section {row[0]}"),
                            "section_content": row[2],
                            "page_number": row[3],
                            "section_summary": (
                                row[4]
                                if row[4]
                                else f"Page {row[3]}, Section {row[0]} of {doc_name}"
                            ),
                        }
                    )
                if page_sections:
                    result.append(
                        {"document_name": doc_name, "page_sections": page_sections}
                    )
        logger.info(f"Retrieved ESG content for {len(result)} documents from database")
    except Exception as e:
        logger.error(f"Error fetching ESG document content from database: {str(e)}")
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
) -> Tuple[
    Any, Optional[Dict[str, Any]]
]:  # Returns (response_content, usage_details) tuple
    """
    Helper function to get a completion from the LLM synchronously.
    Handles standard completions and tool calls. Returns content and usage details.
    """
    usage_details = None  # Initialize
    response = None  # Initialize
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
        "database_name": database_name,  # Pass database_name from caller
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
            usage_details = None  # Ensure usage_details is None if not returned
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
        logger.debug(
            "Returning extracted content string and usage details for standard completion."
        )
        # Return the content string and usage details
        return response_value, usage_details


def select_relevant_documents(
    query: str,
    catalog: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_esg",  # Default to par
    process_monitor=None,  # Added process_monitor
    stage_name: Optional[str] = None,  # Added stage_name
) -> List[str]:
    """
    Use an LLM to select the most relevant ESG documents from the catalog based on the query (synchronous).
    """
    logger.info("Selecting relevant ESG documents from catalog")
    formatted_catalog = format_catalog_for_llm(catalog)
    selection_prompt = get_catalog_selection_prompt(
        query, formatted_catalog
    )  # Assumes this prompt asks for JSON list

    try:
        logger.info(
            f"Initiating ESG Document Selection API call (DB: {database_name})"
        )  # Added contextual log
        # Direct synchronous call - now returns a tuple
        selection_response_str, selection_usage = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=200,
            token=token,
            database_name=database_name,  # Pass the specific database name
        )

        # Track token usage from LLM calls
        if selection_usage:
            logger.debug(f"Document selection usage: {selection_usage}")
            # Update process monitor if available
            if process_monitor and stage_name:  # Check if monitor and stage_name exist
                process_monitor.add_llm_call_details_to_stage(
                    stage_name, selection_usage
                )
                process_monitor.add_stage_details(
                    stage_name, task="document_selection"
                )  # Add task detail

        # Check if get_completion returned an error string
        if isinstance(
            selection_response_str, str
        ) and selection_response_str.startswith("Error:"):
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
                logger.info(f"LLM selected ESG document IDs: {selected_ids}")
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
                    f"Extracted ESG document IDs using fallback regex: {valid_ids}"
                )
                return valid_ids
            logger.error(
                "Could not extract ESG document IDs from response using fallback."
            )
            return []
    except Exception as e:
        logger.error(f"Error during LLM ESG document selection: {str(e)}")
        return []


# Define the tool schema for research synthesis
SYNTHESIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "synthesize_research_findings",
        "description": "Synthesizes research findings from provided documents and generates a status summary with page/section references.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_summary": {
                    "type": "string",
                    "description": "Concise status summary (1 sentence) indicating finding relevance (e.g., '✅ Found direct answer.', '📄 No relevant info found.').",
                },
                "detailed_research": {
                    "type": "string",
                    "description": "Detailed, structured markdown report synthesizing information from documents. Include citations on separate lines after each paragraph using: ***Source: Document Name, Page X, Section Name*** in bold italic format. CRITICAL: Extract actual section names/titles from within the document content (look for headers, bold titles, topic names) rather than using generic 'Section X' labels.",
                },
                "page_numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of page numbers referenced in the research findings (extracted from the document sections used).",
                },
                "section_ids_by_page": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "description": "Object mapping page numbers (as string keys) to arrays of section IDs referenced on that page.",
                },
            },
            "required": [
                "status_summary",
                "detailed_research",
                "page_numbers",
                "section_ids_by_page",
            ],
        },
    },
}


# Updated function using Tool Calling (now synchronous)
def synthesize_response_and_status(
    query: str,
    documents: List[Dict[str, Any]],
    token: Optional[str] = None,
    database_name: str = "internal_esg",  # Default to par
    process_monitor=None,  # Added process_monitor
    stage_name: Optional[str] = None,  # Added stage_name
) -> ResearchResponse:  # Return only ResearchResponse
    """
    Use an LLM tool call to synthesize a detailed research response AND status summary for PAR (synchronous).
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
        }  # Removed None return

    formatted_documents = format_documents_for_llm(documents)
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_documents)

    try:
        logger.info(
            f"Initiating ESG Synthesis API call (DB: {database_name})"
        )  # Added contextual log
        # Direct synchronous call - now returns a tuple
        synthesis_response_obj, synthesis_usage = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=2500,
            temperature=0.2,
            token=token,
            database_name=database_name,  # Pass the specific database name
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
            if process_monitor and stage_name:  # Check if monitor and stage_name exist
                process_monitor.add_llm_call_details_to_stage(
                    stage_name, synthesis_usage
                )
                process_monitor.add_stage_details(
                    stage_name, task="research_synthesis"
                )  # Add task detail

        # Check if get_completion returned an error string in the response part
        if isinstance(
            synthesis_response_obj, str
        ) and synthesis_response_obj.startswith("Error:"):
            logger.error(
                f"get_completion failed for {database_name} synthesis: {synthesis_response_obj}"
            )
            error_result["detailed_research"] = synthesis_response_obj
            return error_result  # Return error dict

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
                    required_keys = [
                        "status_summary",
                        "detailed_research",
                        "page_numbers",
                        "section_ids_by_page",
                    ]
                    if all(key in arguments for key in required_keys):
                        logger.info(
                            f"Successfully parsed synthesis tool call for {database_name}."
                        )
                        # Ensure values have correct types, default if not
                        status = arguments.get("status_summary", default_error_status)
                        research = arguments.get("detailed_research", default_research)
                        page_numbers = arguments.get("page_numbers", [])
                        section_ids_by_page = arguments.get("section_ids_by_page", {})

                        # Debug the generated research to check for section names in citations
                        logger.info(
                            f"ESG DEBUG: Generated detailed_research length: {len(research)} characters"
                        )
                        if "***Source:" in research:
                            citation_count = research.count("***Source:")
                            logger.info(
                                f"ESG DEBUG: Found {citation_count} citations in detailed_research"
                            )
                            # Log first few citations for debugging
                            import re

                            citations = re.findall(r"\*\*\*Source:.*?\*\*\*", research)
                            for i, citation in enumerate(
                                citations[:3]
                            ):  # Show first 3 citations
                                logger.info(f"ESG DEBUG: Citation {i+1}: {citation}")
                        else:
                            logger.warning(
                                "ESG DEBUG: No citations found in detailed_research - this may be the issue!"
                            )

                        if not isinstance(status, str):
                            status = default_error_status
                        if not isinstance(research, str):
                            research = default_research
                        if not isinstance(page_numbers, list):
                            page_numbers = []
                        if not isinstance(section_ids_by_page, dict):
                            section_ids_by_page = {}

                        return {
                            "status_summary": status,
                            "detailed_research": research,
                            "page_numbers": page_numbers,
                            "section_ids_by_page": section_ids_by_page,
                        }  # Return result dict
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
    query: str,
    scope: str,
    token: Optional[str] = None,
    process_monitor=None,
    query_stage_name: Optional[str] = None,
) -> SubagentResult:  # Added query_stage_name
    """
    Synchronously query the Internal ESG database based on the specified scope.

    Args:
        query: The user's query to process
        scope: The type of data to return ("metadata" or "research")
        token: Optional OAuth token
        process_monitor: Optional process monitor to track token usage
        query_stage_name (str, optional): The specific stage name for this query instance
                                          provided by the caller (e.g., worker).

    Returns:
        Tuple containing the main database response, a list of selected document IDs (or None),
        a list of file links (or None), page/section references (or None), section content map (or None),
        and reference index (or None).
    """
    logger.error(f"DEBUG PAR START: Function called with query='{query}', scope='{scope}', token={'[SET]' if token else '[NONE]'}")
    logger.info(f"Querying Internal ESG database (sync): '{query}' with scope: {scope}")
    database_name = "internal_esg"  # Set database name
    default_error_status = "❌ Error during query processing."
    selected_doc_ids: Optional[List[str]] = None  # Initialize
    file_links: Optional[List[FileLink]] = None  # Initialize file links
    page_section_refs: Optional[PageSectionRefs] = (
        None  # Initialize page/section references
    )
    section_content_map: Optional[SectionContentMap] = (
        None  # Initialize section content map
    )
    reference_index: Optional[ReferenceIndex] = None  # Initialize reference index
    # Use the passed-in stage name if available, otherwise default
    stage_name = query_stage_name or f"db_query_{database_name}_unknown"
    logger.debug(f"Using process monitor stage name: {stage_name}")
    # REMOVED manual tracking variables and list

    try:
        # Direct synchronous calls
        catalog = fetch_esg_catalog()  # Use par function
        logger.info(f"Retrieved {len(catalog)} total ESG catalog entries")
        if not catalog:
            response: DatabaseResponse
            if scope == "metadata":
                response = []
            else:
                response = {
                    "detailed_research": "No documents found in the Internal ESG database catalog.",
                    "status_summary": "📄 No documents found in catalog.",
                }
            return (
                response,
                selected_doc_ids,
                file_links,
                page_section_refs,
                section_content_map,
                reference_index,
            )  # Return empty response and None IDs/links/page_sections/content/refs

        # Select documents using the updated helper function
        selected_doc_ids = select_relevant_documents(
            query, catalog, token, database_name, process_monitor, stage_name
        )

        logger.info(
            f"LLM selected {len(selected_doc_ids)} relevant ESG document IDs: {selected_doc_ids}"
        )
        if not selected_doc_ids:
            if scope == "metadata":
                response = []
            else:
                response = {
                    "detailed_research": "LLM did not select any relevant documents from the catalog based on the query.",
                    "status_summary": "📄 No relevant documents selected by LLM.",
                }

            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(
                    stage_name, result_count=0, document_ids=selected_doc_ids
                )

            return (
                response,
                selected_doc_ids,
                file_links,
                page_section_refs,
                section_content_map,
                reference_index,
            )  # Return empty response and empty IDs list/links/page_sections/content/refs

        # Process based on scope
        if scope == "metadata":
            selected_items = [
                item for item in catalog if item.get("id") in selected_doc_ids
            ]
            logger.info(f"Returning {len(selected_items)} selected PAR metadata items.")

            # Collect file links from selected items (including blank ones)
            file_links = []
            for item in selected_items:
                file_links.append(
                    {
                        "file_link": item.get(
                            "file_link", ""
                        ),  # Use empty string if None
                        "document_name": item.get("document_name", "Unknown"),
                    }
                )

            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(
                    stage_name,
                    result_count=len(selected_items),
                    document_ids=selected_doc_ids,
                )

            return (
                selected_items,
                selected_doc_ids,
                file_links,
                page_section_refs,
                section_content_map,
                reference_index,
            )  # Return metadata, IDs, file links, and None page_sections/content/refs (metadata scope doesn't need them)

        elif scope == "research":
            # Collect file links from catalog before fetching content (including blank ones)
            file_links = []
            logger.error(f"DEBUG PAR: Building file_links from catalog with {len(catalog)} items")
            for item in catalog:
                if item.get("id") in selected_doc_ids:
                    file_link_value = item.get("file_link", "")
                    doc_name_value = item.get("document_name", "Unknown")
                    logger.error(f"DEBUG PAR: Adding file_link for doc '{doc_name_value}': '{file_link_value}'")
                    file_links.append(
                        {
                            "file_link": file_link_value,  # Use empty string if None
                            "document_name": doc_name_value,
                        }
                    )
            logger.error(f"DEBUG PAR: Final file_links list: {file_links}")

            # Fetch content and synthesize
            documents = fetch_esg_content(selected_doc_ids)  # Use par function
            logger.info(
                f"Retrieved content for {len(documents)} ESG documents for research."
            )

            # Get research synthesis using the updated helper function
            # synthesize_response_and_status now returns only the ResearchResponse dict
            research_result = synthesize_response_and_status(
                query, documents, token, database_name, process_monitor, stage_name
            )

            # Extract page/section references from the tool response
            page_numbers: List[int] = research_result.get("page_numbers", [])
            section_ids_by_page_str: Dict[str, Any] = research_result.get(
                "section_ids_by_page", {}
            )

            logger.info(
                f"ESG DEBUG: Raw research_result keys: {list(research_result.keys())}"
            )
            logger.info(f"ESG DEBUG: Raw page_numbers from tool: {page_numbers}")
            logger.info(
                f"ESG DEBUG: Raw section_ids_by_page from tool: {section_ids_by_page_str}"
            )

            # Convert string keys to integers for page_section_refs
            page_section_refs = {}
            if isinstance(section_ids_by_page_str, dict):
                for page_str, section_list in section_ids_by_page_str.items():
                    try:
                        page_num = int(page_str)
                        page_section_refs[page_num] = (
                            section_list if isinstance(section_list, list) else []
                        )
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Could not convert page key to integer: {page_str}"
                        )
                        continue

            logger.info(
                f"Extracted page/section references from tool response: {page_section_refs}"
            )

            # Build section content map for referenced sections
            section_content_map = {}
            logger.info(
                f"ESG DEBUG: Retrieved {len(documents)} documents from database"
            )
            for doc in documents:
                logger.info(f"ESG DEBUG: Document keys: {list(doc.keys())}")
                page_sections = doc.get("page_sections", [])
                sections = doc.get("sections", [])  # Check old format too
                logger.info(
                    f"ESG DEBUG: Document '{doc.get('document_name', 'Unknown')}' has {len(page_sections)} page_sections and {len(sections)} old sections"
                )
                if page_sections:
                    logger.info(
                        f"ESG DEBUG: First page_section sample: {page_sections[0]}"
                    )
                elif sections:
                    logger.info(f"ESG DEBUG: First old section sample: {sections[0]}")
                else:
                    logger.info(f"ESG DEBUG: Document has no sections at all!")
                for section in page_sections:
                    page_num = section.get("page_number")
                    section_id = section.get("section_id")
                    section_content = section.get("section_content", "")

                    # Check if this section was referenced in the research
                    if (
                        page_num in page_section_refs
                        and section_id in page_section_refs[page_num]
                    ):
                        key = f"{page_num}:{section_id}"
                        section_content_map[key] = section_content

            logger.info(
                f"Built section content map for {len(section_content_map)} referenced sections"
            )
            logger.info(
                f"ESG DEBUG: Final section_content_map keys: {list(section_content_map.keys())}"
            )

            # Build reference index from structured data
            page_numbers = research_result.get("page_numbers", [])
            if page_numbers and section_content_map:
                reference_index = build_structured_reference_index(
                    page_numbers, file_links, section_content_map
                )
                logger.info(
                    f"Built structured reference index with {len(reference_index)} page references"
                )
                logger.error(f"DEBUG PAR: Final reference_index: {reference_index}")
            else:
                reference_index = {}
                logger.warning("No page numbers or section content available for reference index")

            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(
                    stage_name,
                    result_count=len(documents),
                    document_ids=selected_doc_ids,
                    status_summary=research_result.get("status_summary", ""),
                )

            # DEBUG: Log what we're about to return
            logger.error(f"DEBUG PAR: About to return 6-element tuple")
            logger.error(f"DEBUG PAR: research_result type: {type(research_result)}")
            logger.error(f"DEBUG PAR: selected_doc_ids: {selected_doc_ids}")
            logger.error(f"DEBUG PAR: file_links count: {len(file_links) if file_links else 0}")
            logger.error(f"DEBUG PAR: page_section_refs: {page_section_refs}")
            logger.error(f"DEBUG PAR: section_content_map count: {len(section_content_map) if section_content_map else 0}")
            logger.error(f"DEBUG PAR: reference_index count: {len(reference_index) if reference_index else 0}")

            return (
                research_result,
                selected_doc_ids,
                file_links,
                page_section_refs,
                section_content_map,
                reference_index,
            )  # Return research result, IDs, file links, page/section refs, section content, and reference index

        else:
            logger.error(f"Invalid scope provided to internal_esg subagent: {scope}")
            raise ValueError(f"Invalid scope: {scope}")  # Let the error propagate

    except Exception as e:
        error_msg = f"Error querying Internal ESG database (scope: {scope}): {str(e)}"
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            response = []
        else:
            response = {
                "detailed_research": f"**Error processing request for Internal ESG:** {str(e)}",
                "status_summary": default_error_status,
            }

            # Add details to process monitor before returning
        if process_monitor:  # Check if monitor exists before adding error details
            process_monitor.add_stage_details(
                stage_name,
                error=str(e),
                document_ids=selected_doc_ids,  # Keep doc IDs if available
            )

        # Return error response and potentially selected IDs/links/page_sections/content/refs if selection succeeded before error
        return (
            response,
            selected_doc_ids,
            file_links,
            page_section_refs,
            section_content_map,
            reference_index,
        )
