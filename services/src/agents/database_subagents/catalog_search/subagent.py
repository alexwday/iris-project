# services/src/agents/database_subagents/catalog_search/subagent.py
"""
Catalog Search Subagent (Unified Internal Database Handler)

This module handles queries to all internal catalog databases,
including catalog retrieval, document selection, content retrieval,
and response synthesis (generating detailed research and status summary using tool calls).
Processes each selected document individually in parallel then combines results.

Functions:
    query_database_sync: Synchronously query the specified internal database
"""

import asyncio
import json
import logging
import os
import re
import time
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Import for embedding functionality (self-contained in this module)
import psycopg2.extras
from pgvector.psycopg2 import register_vector

# Get module logger
logger = logging.getLogger(__name__)


def _generate_research_statement_embedding(
    research_statement: str, token: Optional[str] = None
) -> Tuple[Optional[List[float]], Optional[Dict[str, Any]]]:
    """
    Self-contained function to generate embedding for research statement.
    
    Args:
        research_statement (str): The research statement to embed
        token (Optional[str]): OAuth token for API authentication
        
    Returns:
        Tuple[Optional[List[float]], Optional[Dict[str, Any]]]: 
            - Embedding vector
            - Usage details dictionary
    """
    logger.info(f"Generating embedding for research statement: '{research_statement[:100]}...'")
    usage_details = None
    
    try:
        model_config = config.get_model_config("embedding")
        model_name = model_config["name"]
        prompt_cost = model_config["prompt_token_cost"]
        completion_cost = model_config.get("completion_token_cost", 0.0)

        call_params = {
            "oauth_token": token or "placeholder_token",
            "prompt_token_cost": prompt_cost,
            "completion_token_cost": completion_cost,
            "model": model_name,
            "input": [research_statement],
            "dimensions": 2000,
            "database_name": "catalog_search_embedding",
            "is_embedding": True,
        }

        # Direct synchronous call - returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the tuple format: (api_response, usage_details)
        response = None
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.debug(f"Research statement embedding usage: {usage_details}")
        else:
            response = result
            logger.debug("call_llm did not return usage_details")

        if (
            response
            and hasattr(response, "data")
            and response.data
            and hasattr(response.data[0], "embedding")
            and response.data[0].embedding
        ):
            logger.info("Research statement embedding generated successfully.")
            return response.data[0].embedding, usage_details
        else:
            logger.error("No embedding data received from API for research statement.")
            return None, usage_details

    except Exception as e:
        logger.error(f"Failed to generate research statement embedding: {e}", exc_info=True)
        return None, usage_details


def fetch_catalog_with_similarity_filter(
    document_source: str, 
    research_statement: Optional[str] = None,
    token: Optional[str] = None,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch catalog with optional similarity filtering based on research statement.
    If research_statement is provided, performs similarity search on document_description_embedding.
    Otherwise, returns all documents for the document_source.
    
    Args:
        document_source: The document source to query
        research_statement: Optional research statement for similarity filtering
        token: OAuth token for embedding generation
        top_k: Number of top similar documents to return (when using similarity)
        
    Returns:
        List of catalog records, either filtered by similarity or all documents
    """
    logger.info(f"Fetching catalog for {document_source} with similarity filter: {research_statement is not None}")
    
    conn = connect_to_db()
    catalog_records: List[Dict[str, Any]] = []
    
    if not conn:
        logger.error(f"Failed to connect to database for {document_source} catalog")
        return catalog_records
        
    try:
        # Register vector type for pgvector operations
        register_vector(conn)
        
        with conn.cursor() as cur:
            if research_statement:
                # Generate embedding for research statement
                query_embedding, usage_details = _generate_research_statement_embedding(
                    research_statement, token
                )
                
                if query_embedding is None:
                    logger.warning("Could not generate embedding, falling back to regular catalog fetch")
                    # Fall back to regular catalog fetch
                    cur.execute(
                        """
                        SELECT id, document_name, document_description, document_usage, 
                               file_link, file_name
                        FROM apg_catalog
                        WHERE document_source = %s
                        ORDER BY document_name
                        """,
                        (document_source,),
                    )
                else:
                    # Perform similarity search
                    logger.info(f"Performing similarity search for top {top_k} documents")
                    cur.execute(
                        """
                        SELECT id, document_name, document_description, document_usage, 
                               file_link, file_name,
                               1 - (document_description_embedding <=> %s::vector) AS similarity_score
                        FROM apg_catalog
                        WHERE document_source = %s 
                        AND document_description_embedding IS NOT NULL
                        ORDER BY similarity_score DESC
                        LIMIT %s
                        """,
                        (query_embedding, document_source, top_k),
                    )
            else:
                # Regular catalog fetch without similarity filtering
                cur.execute(
                    """
                    SELECT id, document_name, document_description, document_usage, 
                           file_link, file_name
                    FROM apg_catalog
                    WHERE document_source = %s
                    ORDER BY document_name
                    """,
                    (document_source,),
                )
            
            # Process results
            for row in cur.fetchall():
                record = {
                    "id": str(row[0]),
                    "document_name": row[1],
                    "document_description": row[2],
                    "document_usage": row[3] if row[3] else "No detailed usage information available",
                    "file_link": row[4] if row[4] else None,
                    "file_name": row[5] if row[5] else None,
                }
                
                # Add similarity score if available (similarity search)
                if research_statement and query_embedding and len(row) > 6:
                    record["similarity_score"] = float(row[6])
                    
                catalog_records.append(record)
        
        logger.info(f"Retrieved {len(catalog_records)} catalog entries for {document_source}")
        if research_statement and catalog_records and "similarity_score" in catalog_records[0]:
            logger.info(f"Similarity scores range: {catalog_records[-1]['similarity_score']:.3f} to {catalog_records[0]['similarity_score']:.3f}")
            
    except Exception as e:
        logger.error(f"Error fetching {document_source} catalog: {str(e)}", exc_info=True)
    finally:
        if conn:
            conn.close()
            
    return catalog_records


def load_catalog_selection_config(scope: str = "research"):
    """
    Load catalog selection configuration from YAML file.

    Args:
        scope: The query scope ('metadata' or 'research')

    Returns:
        dict: Configuration with resolved system prompt and settings
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # NEW: Use different YAML file for metadata scope
        if scope == "metadata":
            yaml_filename = "catalog_selection_prompt_metadata.yaml"
        else:
            yaml_filename = "catalog_selection_prompt.yaml"
        yaml_path = os.path.join(current_dir, yaml_filename)

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Extract system prompt from YAML
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception(
                f"No system_prompt found in catalog selection YAML configuration ({yaml_filename})"
            )

        # No context replacement needed for catalog selection (minimal context)
        return yaml_config

    except Exception as e:
        logger.error(f"Failed to load catalog selection YAML config: {str(e)}")
        raise


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
                "No system_prompt found in content synthesis YAML configuration"
            )

        # No context replacement needed for content synthesis (focused extraction task)
        return yaml_config

    except Exception as e:
        logger.error(f"Failed to load content synthesis YAML config: {str(e)}")
        raise


def get_catalog_selection_prompt(query: str, formatted_catalog: str, scope: str = "research") -> str:
    """
    Generate a prompt for selecting relevant documents from an internal catalog using YAML config.

    Args:
        query (str): The research statement (query)
        formatted_catalog (str): The formatted catalog of internal documents
        scope (str): The query scope ('metadata' or 'research')

    Returns:
        str: The formatted prompt for the LLM
    """
    # NEW: Pass scope to load appropriate configuration
    config = load_catalog_selection_config(scope)
    system_prompt = config.get("system_prompt", "")

    # Replace template variables
    system_prompt = system_prompt.replace("{{query}}", query)
    system_prompt = system_prompt.replace("{{formatted_catalog}}", formatted_catalog)

    return system_prompt


def get_content_synthesis_prompt(user_query: str, formatted_documents: str) -> str:
    """
    Generate a prompt for synthesizing content from retrieved internal documents using YAML config.

    Args:
        user_query (str): The original user query from the research statement
        formatted_documents (str): The formatted content of retrieved internal document sections

    Returns:
        str: The formatted prompt for the LLM
    """
    config = load_content_synthesis_config()
    system_prompt = config.get("system_prompt", "")

    # Replace template variables
    system_prompt = system_prompt.replace("{{user_query}}", user_query)
    system_prompt = system_prompt.replace(
        "{{formatted_documents}}", formatted_documents
    )

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
        raise Exception("No tools found in content synthesis YAML configuration")

    # Return the first tool (should be extract_page_based_research)
    return tools[0]


# Formatting functions remain synchronous as they are CPU-bound
def format_catalog_for_llm(catalog_records: List[Dict[str, Any]], scope: str = "research") -> str:
    """
    Format the catalog records into a string that is optimized for LLM comprehension.
    Uses document_usage for research scope and document_description for metadata scope.
    
    Args:
        catalog_records: List of catalog records
        scope: The scope of the query ("metadata" or "research")
    """
    formatted_catalog = ""
    for record in catalog_records:
        doc_id = record.get("id", "unknown")
        doc_name = record.get("document_name", "Untitled")
        doc_desc = record.get("document_usage" if scope == "research" else "document_description", "No description available")
        formatted_catalog += f"Document ID: {doc_id}\n"
        formatted_catalog += f"Document Name: {doc_name}\n"
        formatted_catalog += f"Document Description: {doc_desc}\n\n"
    return formatted_catalog.strip()


# Note: build_structured_reference_index function removed - no longer needed with new page-based approach
# Reference numbering is now handled at the database_router level after aggregating all subagent results


def format_documents_for_llm(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into a string that is optimized for LLM analysis.
    Reconstructs documents from page records in correct order with clear page markers.
    """
    formatted_docs = ""
    for doc in documents:
        doc_name = doc.get("document_name", "Untitled")
        formatted_docs += f"# {doc_name}\n\n"

        # Get page_sections and sort by page_number
        page_sections = doc.get("page_sections", [])
        if not page_sections:
            formatted_docs += "No content available.\n\n"
            continue

        # Sort pages by page_number for proper document reconstruction
        sorted_pages = sorted(page_sections, key=lambda x: x.get("page_number", 0))

        # Process each page
        for section in sorted_pages:
            page_number = section.get("page_number", 0)
            section_summary = section.get("section_summary", f"Page {page_number}")
            section_content = section.get("section_content", "No content available")

            # Create clear page header for LLM understanding
            formatted_docs += f"## {section_summary}\n\n"
            formatted_docs += f"**PAGE {page_number}**\n\n"
            formatted_docs += f"{section_content}\n\n"
            formatted_docs += "---\n\n"

    return formatted_docs.strip()


# Database interaction functions (now synchronous)
def fetch_catalog(document_source: str) -> List[Dict[str, Any]]:
    """
    Fetch the full catalog from the database for the specified document source.

    Args:
        document_source: The document source to query (e.g., 'internal_capm', 'internal_par', etc.)

    Returns:
        List of catalog records
    """
    logger.info(
        f"Fetching catalog for {document_source} (environment: {config.ENVIRONMENT})"
    )
    conn = connect_to_db()
    catalog_records: List[Dict[str, Any]] = []
    if not conn:
        logger.error(f"Failed to connect to database for {document_source} catalog")
        return catalog_records
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, document_name, document_description, document_usage, file_link, file_name
                FROM apg_catalog
                WHERE document_source = %s
                ORDER BY document_name
            """,
                (document_source,),
            )
            for row in cur.fetchall():
                catalog_records.append(
                    {
                        "id": str(row[0]),
                        "document_name": row[1],
                        "document_description": row[2],
                        "document_usage": row[3] if row[3] else "No detailed usage information available",
                        "file_link": row[4] if row[4] else None,
                        "file_name": row[5] if row[5] else None,
                    }
                )
        logger.info(
            f"Retrieved {len(catalog_records)} catalog entries for {document_source} from database"
        )
        # Debug file_name data
        if catalog_records:
            first_record = catalog_records[0]
            logger.debug(
                f"DEBUG file_name: First record has file_name='{first_record.get('file_name', 'MISSING')}', file_link='{first_record.get('file_link', 'MISSING')[:50]}...'"
            )
    except Exception as e:
        logger.error(
            f"Error fetching {document_source} catalog from database: {str(e)}"
        )
    finally:
        if conn:
            conn.close()
    return catalog_records


def fetch_document_content(
    doc_ids: List[str], document_source: str
) -> List[Dict[str, Any]]:
    """
    Fetch the content of specified documents from the database synchronously.
    Now retrieves all page/section records with page_number, section_id, section_summary fields.

    Args:
        doc_ids: List of document IDs to fetch
        document_source: The document source to query

    Returns:
        List of documents with their page sections
    """
    logger.info(f"Fetching content for {document_source} documents: {doc_ids}")
    if not doc_ids:
        logger.warning(f"No {document_source} document IDs to fetch")
        return []
    conn = connect_to_db()
    result: List[Dict[str, Any]] = []
    if not conn:
        logger.error(f"Failed to connect to database for {document_source} content")
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
                AND document_source = %s
            """,
                doc_ids + [document_source],
            )
            for row in cur.fetchall():
                doc_names[row[0]] = row[1]
            logger.info(
                f"Found {len(doc_names)} {document_source} documents for IDs: {doc_ids}"
            )

        for doc_id, doc_name in doc_names.items():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT section_id, section_name, section_content, page_number, section_summary
                    FROM apg_content
                    WHERE document_source = %s
                    AND document_name = %s
                    ORDER BY page_number, section_id
                """,
                    (document_source, doc_name),
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
        logger.info(
            f"Retrieved content for {len(result)} {document_source} documents from database"
        )
    except Exception as e:
        logger.error(
            f"Error fetching {document_source} document content from database: {str(e)}"
        )
    finally:
        if conn:
            conn.close()
    return result


# LLM interaction helper (Updated for Tool Calling, now synchronous)
def get_completion(
    capability: str,
    prompt: str,
    max_tokens: int = 4000,
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

    # All calls should use the YAML-generated prompt as the system message
    # since get_catalog_selection_prompt() and get_content_synthesis_prompt()
    # both return complete YAML system prompts
    if kwargs.get("tools"):
        # Tool calls need a simple user message to trigger the tool
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "Please complete the requested task using the appropriate tool.",
            },
        ]
    else:
        # Non-tool calls (like document selection) can use prompt as system message with simple user request
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "Please provide your response based on the instructions and context provided.",
            },
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
        logger.debug("Forcing non-streaming mode for tool call.")
    else:
        call_params.setdefault("stream", False)

    try:
        # Direct synchronous call - now returns a tuple (response, usage_details)
        result = call_llm(**call_params)

        # Handle the new tuple format: (api_response, usage_details)
        if isinstance(result, tuple) and len(result) == 2:
            response, usage_details = result
            if usage_details:
                logger.info(f"Usage details for {database_name}: {usage_details}")
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
    database_name: str = "catalog_search",  # Default generic name
    process_monitor=None,  # Added process_monitor
    stage_name: Optional[str] = None,  # Added stage_name
    scope: str = "research"  # Added scope parameter
) -> List[str]:
    """
    Use an LLM to select the most relevant documents from the catalog based on the query.

    Args:
        query (str): The search query
        catalog (List[Dict[str, Any]]): List of available documents with metadata
        token (Optional[str]): OAuth token for API authentication
        database_name (str): Name of the database for logging context
        process_monitor: Optional process monitor for tracking
        stage_name (Optional[str]): Stage name for process monitoring

    Returns:
        List[str]: List of selected document IDs
    """
    logger.info(f"Selecting relevant documents from {database_name} catalog")
    formatted_catalog = format_catalog_for_llm(catalog, scope=scope)
    # NEW: Pass scope parameter to get appropriate prompt for metadata vs research
    selection_prompt = get_catalog_selection_prompt(
        query, formatted_catalog, scope
    )  # Pass scope to get appropriate prompt

    try:
        logger.info(
            f"Initiating Document Selection API call (DB: {database_name})"
        )  # Added contextual log
        # Direct synchronous call - now returns a tuple
        selection_response_str, selection_usage = get_completion(
            capability="small",
            prompt=selection_prompt,
            max_tokens=4096,
            token=token,
            database_name=database_name,  # Pass the specific database name
        )

        # Track token usage from LLM calls
        if selection_usage:
            logger.info(f"Document selection usage: {selection_usage}")
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
                logger.info(
                    f"LLM selected {database_name} document IDs: {selected_ids}"
                )
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
                    f"Extracted {database_name} document IDs using fallback regex: {valid_ids}"
                )
                return valid_ids
            logger.error(
                f"Could not extract {database_name} document IDs from response using fallback."
            )
            return []
    except Exception as e:
        logger.error(f"Error during LLM {database_name} document selection: {str(e)}")
        return []


# Function to process a single document (for parallel processing)
def process_single_document(
    query: str,
    document: Dict[str, Any],
    token: Optional[str] = None,
    database_name: str = "catalog_search",
    process_monitor=None,
    stage_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a single document and return page-based research findings.
    This function is called in parallel for each document.
    """
    doc_name = document.get("document_name", "Unknown Document")
    logger.debug(f"Processing single document from {database_name}: {doc_name}")

    # Get file link and file name from document metadata
    file_link = ""
    file_name = ""
    # Check if document has file_link directly
    if "file_link" in document:
        file_link = document.get("file_link", "")
    # Check if document has file_name directly
    if "file_name" in document:
        file_name = document.get("file_name", "")

    # Format single document for LLM
    formatted_doc = format_documents_for_llm([document])
    synthesis_prompt = get_content_synthesis_prompt(query, formatted_doc)

    try:
        logger.info(
            f"Initiating Single Document Synthesis API call for {doc_name} from {database_name}"
        )
        synthesis_tool_schema = get_synthesis_tool_schema()
        synthesis_response_obj, synthesis_usage = get_completion(
            capability="large",
            prompt=synthesis_prompt,
            max_tokens=4000,  # Allow full response generation
            temperature=0.2,
            token=token,
            database_name=f"{database_name}_{doc_name}",
            tools=[synthesis_tool_schema],
            tool_choice={
                "type": "function",
                "function": {"name": synthesis_tool_schema["function"]["name"]},
            },
        )

        # Track token usage from synthesis
        if synthesis_usage:
            logger.info(
                f"Single document synthesis usage for {doc_name}: {synthesis_usage}"
            )
            if process_monitor and stage_name:
                process_monitor.add_llm_call_details_to_stage(
                    stage_name, synthesis_usage
                )

        # Check if get_completion returned an error string
        if isinstance(
            synthesis_response_obj, str
        ) and synthesis_response_obj.startswith("Error:"):
            logger.error(
                f"get_completion failed for {doc_name}: {synthesis_response_obj}"
            )
            return {
                "document_name": doc_name,
                "file_link": file_link,
                "status_summary": f"❌ Error processing {doc_name}.",
                "page_research": [],
            }

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
            logger.debug(f"Tool call function name: {tool_call.function.name}")
            synthesis_tool_schema = get_synthesis_tool_schema()
            if tool_call.function.name == synthesis_tool_schema["function"]["name"]:
                arguments_str = tool_call.function.arguments
                logger.debug(
                    f"Arguments string type: {type(arguments_str)}, length: {len(arguments_str)}"
                )
                try:
                    # Show JSON sample for debugging (first 200 chars)
                    logger.debug(
                        f"JSON sample for {doc_name}: {arguments_str[:200]}..."
                    )

                    # Parse JSON directly like internal_par does (no aggressive cleaning)
                    arguments = json.loads(arguments_str)
                    required_keys = ["status_summary", "page_research"]
                    if all(key in arguments for key in required_keys):
                        return {
                            "document_name": doc_name,
                            "file_link": file_link,
                            "status_summary": arguments.get("status_summary", ""),
                            "page_research": arguments.get("page_research", []),
                        }
                    else:
                        logger.error(
                            f"Missing required keys in tool arguments for {doc_name}"
                        )
                        logger.error(f"Available keys: {list(arguments.keys())}")
                        return {
                            "document_name": doc_name,
                            "file_link": file_link,
                            "status_summary": f"❌ Missing required keys for {doc_name}.",
                            "page_research": [],
                        }
                except json.JSONDecodeError as json_err:
                    logger.error(
                        f"Failed to parse tool arguments JSON for {doc_name}: {json_err}"
                    )
                    logger.error(
                        f"Raw JSON first 100 chars: {repr(arguments_str[:100])}"
                    )
                    logger.error(
                        f"Raw JSON last 100 chars: {repr(arguments_str[-100:])}"
                    )
                    # Show character at error position
                    error_pos = getattr(json_err, "pos", 0)
                    if error_pos < len(arguments_str):
                        char_at_error = (
                            arguments_str[error_pos]
                            if error_pos < len(arguments_str)
                            else "EOF"
                        )
                        logger.error(
                            f"Character at error position {error_pos}: {repr(char_at_error)}"
                        )
                        # Show context around error
                        start = max(0, error_pos - 20)
                        end = min(len(arguments_str), error_pos + 20)
                        context = arguments_str[start:end]
                        logger.error(f"Context around error: {repr(context)}")
                    return {
                        "document_name": doc_name,
                        "file_link": file_link,
                        "status_summary": f"❌ JSON decode error for {doc_name}.",
                        "page_research": [],
                    }
            else:
                logger.error(
                    f"Unexpected tool called for {doc_name}: {tool_call.function.name}"
                )
                return {
                    "document_name": doc_name,
                    "file_link": file_link,
                    "status_summary": f"❌ Unexpected tool for {doc_name}.",
                    "page_research": [],
                }
        else:
            # Debug what we actually got
            if synthesis_response_obj.choices:
                message = synthesis_response_obj.choices[0].message
                logger.error(
                    f"No tool call for {doc_name}. Message content: {getattr(message, 'content', 'No content')[:100]}"
                )
                logger.error(
                    f"Tool calls present: {hasattr(message, 'tool_calls')} - {getattr(message, 'tool_calls', None)}"
                )
            else:
                logger.error(f"No choices in response for {doc_name}")
            logger.error(f"No tool call received for {doc_name} synthesis")
            return {
                "document_name": doc_name,
                "file_link": file_link,
                "status_summary": f"❌ No tool call for {doc_name}.",
                "page_research": [],
            }

    except Exception as e:
        logger.error(
            f"Exception during synthesis for {doc_name}: {str(e)}", exc_info=True
        )
        return {
            "document_name": doc_name,
            "file_link": file_link,
            "status_summary": f"❌ Exception processing {doc_name}.",
            "page_research": [],
        }


# Updated function using parallel processing then combination
def synthesize_response_and_status(
    query: str,
    documents: List[Dict[str, Any]],
    file_links: List[FileLink],
    token: Optional[str] = None,
    database_name: str = "catalog_search",
    process_monitor=None,
    stage_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process each document in parallel, then return structured page-based research.
    Returns a dictionary with document names as keys, containing page-based research.
    """
    logger.info(
        f"Synthesizing response for {len(documents)} documents from {database_name} using parallel processing"
    )

    if not documents:
        logger.warning(f"No documents provided for {database_name} synthesis.")
        return {}

    # Create file link and file name mapping
    file_link_map = {}
    file_name_map = {}
    for link_info in file_links:
        doc_name = link_info.get("document_name", "")
        file_link = link_info.get("file_link", "")
        file_name = link_info.get("file_name", "")
        if doc_name:
            file_link_map[doc_name] = file_link
            file_name_map[doc_name] = file_name

    # Add file links and file names to documents before processing
    for doc in documents:
        doc_name = doc.get("document_name", "")
        if doc_name in file_link_map:
            doc["file_link"] = file_link_map[doc_name]
            doc["file_name"] = file_name_map[doc_name]

    # Process documents in parallel using ThreadPoolExecutor
    document_results = []
    with ThreadPoolExecutor(max_workers=min(len(documents), 5)) as executor:
        # Submit all document processing jobs
        future_to_doc = {
            executor.submit(
                process_single_document,
                query,
                doc,
                token,
                database_name,
                process_monitor,
                stage_name,
            ): doc
            for doc in documents
        }

        # Collect results as they complete
        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                result = future.result()
                document_results.append(result)
                logger.info(
                    f"Completed processing for document: {result.get('document_name')}"
                )
            except Exception as e:
                doc_name = doc.get("document_name", "Unknown")
                logger.error(f"Exception processing document {doc_name}: {str(e)}")
                document_results.append(
                    {
                        "document_name": doc_name,
                        "file_link": file_link_map.get(doc_name, ""),
                        "status_summary": f"❌ Exception processing {doc_name}.",
                        "page_research": [],
                    }
                )

    # Build structured output: document -> page -> research
    structured_output = {}

    for result in document_results:
        doc_name = result.get("document_name", "Unknown Document")
        file_link = result.get("file_link", "")
        page_research = result.get("page_research", [])

        # Only include documents with actual research findings
        if page_research and not result["status_summary"].startswith("❌"):
            doc_output = {}

            for page_item in page_research:
                page_number = page_item.get("page_number", 0)
                research_content = page_item.get("research_content", "")

                # Create page key (e.g., "page_3")
                page_key = f"page_{page_number}"

                doc_output[page_key] = {
                    "research_content": research_content,
                    "file_link": file_link,
                    "file_name": file_name_map.get(doc_name, ""),
                    "page_number": page_number,
                }

            if doc_output:  # Only add document if it has page research
                structured_output[doc_name] = doc_output

    logger.info(
        f"Structured output contains research from {len(structured_output)} documents"
    )
    return structured_output


def query_database_sync(
    query: str,
    scope: str,
    document_source: str,  # NEW PARAMETER
    token: Optional[str] = None,
    process_monitor=None,
    query_stage_name: Optional[str] = None,
    research_statement: Optional[str] = None,  # NEW PARAMETER for similarity search
) -> SubagentResult:  # Added query_stage_name
    """
    Synchronously query the specified internal database based on the specified scope.

    Args:
        query: The user's query to process
        scope: The type of data to return ("metadata" or "research")
        document_source: The document source to query (e.g., 'internal_capm', 'internal_par')
        token: Optional OAuth token
        process_monitor: Optional process monitor to track token usage
        query_stage_name (str, optional): The specific stage name for this query instance
                                          provided by the caller (e.g., worker).
        research_statement (str, optional): Research statement for similarity-based filtering.
                                          If provided, will perform embedding-based similarity search
                                          to pre-filter documents before LLM selection.

    Returns:
        Tuple containing the main database response, a list of selected document IDs (or None),
        a list of file links (or None), page/section references (or None), section content map (or None),
        and reference index (or None).
    """
    logger.debug(
        f"DEBUG START: Function called with query='{query}', scope='{scope}', document_source='{document_source}', token={'[SET]' if token else '[NONE]'}"
    )
    logger.info(
        f"Querying {document_source} database (sync): '{query}' with scope: {scope}"
    )
    database_name = document_source  # Use the passed document_source
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

    try:
        # Use new similarity filtering function if research_statement provided
        if research_statement:
            logger.info(f"Using similarity filtering with research statement for {document_source}")
            # NEW: Use higher limit for metadata scope to give LLM more choices
            similarity_top_k = 30 if scope == "metadata" else 10
            catalog = fetch_catalog_with_similarity_filter(
                document_source=document_source,
                research_statement=research_statement,
                token=token,
                top_k=similarity_top_k  # More documents for metadata mode
            )
        else:
            logger.info(f"Using standard catalog fetch for {document_source}")
            catalog = fetch_catalog(document_source)
            
        logger.info(f"Retrieved {len(catalog)} {document_source} catalog entries (filtered: {research_statement is not None})")
        if not catalog:
            response: DatabaseResponse
            if scope == "metadata":
                response = []
            else:
                response = {
                    "detailed_research": f"No documents found in the {document_source} database catalog.",
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
            query, catalog, token, database_name, process_monitor, stage_name, scope
        )

        logger.info(
            f"LLM selected {len(selected_doc_ids)} relevant {document_source} document IDs: {selected_doc_ids}"
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
            logger.info(
                f"Returning {len(selected_items)} selected {document_source} metadata items."
            )

            # Collect file links from selected items (including blank ones)
            file_links = []
            for item in selected_items:
                file_links.append(
                    {
                        "file_link": item.get(
                            "file_link", ""
                        ),  # Use empty string if None
                        "file_name": item.get(
                            "file_name", ""
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
            # Collect file links from catalog before fetching content
            file_links = []
            for item in catalog:
                if item.get("id") in selected_doc_ids:
                    file_link_value = item.get("file_link", "")
                    file_name_value = item.get("file_name", "")
                    doc_name_value = item.get("document_name", "Unknown")
                    file_links.append(
                        {
                            "file_link": file_link_value,
                            "file_name": file_name_value,
                            "document_name": doc_name_value,
                        }
                    )

            # Fetch content and synthesize using parallel processing
            documents = fetch_document_content(selected_doc_ids, document_source)
            logger.info(
                f"Retrieved content for {len(documents)} {document_source} documents for research."
            )

            # Get research synthesis using new page-based parallel processing
            # This now returns structured output: {doc_name: {page_x: {research_content, file_link}}}
            research_result = synthesize_response_and_status(
                query,
                documents,
                file_links,
                token,
                database_name,
                process_monitor,
                stage_name,
            )

            # For backward compatibility, we need to create a response in the expected format
            # The new structure will be passed through reference_index for downstream processing

            # Create status summary based on results
            if research_result:
                doc_count = len(research_result)
                total_pages = sum(
                    len(doc_data) for doc_data in research_result.values()
                )
                status_summary = f"✅ Found relevant information in {doc_count} document(s) across {total_pages} page(s)."
            else:
                status_summary = (
                    f"📄 No relevant information found in {document_source} documents."
                )

            # Create a simplified detailed_research for backward compatibility
            detailed_research = f"# {document_source.replace('_', ' ').title()} Research Results\n\n*Query: {query}*\n\n"
            if research_result:
                detailed_research += f"Found relevant information in {len(research_result)} document(s).\n\n"
                for doc_name, doc_data in research_result.items():
                    page_count = len(doc_data)
                    detailed_research += (
                        f"- **{doc_name}**: {page_count} relevant page(s)\n"
                    )
            else:
                detailed_research += (
                    "No relevant information found in the selected documents.\n"
                )

            # Build the response in the expected format
            response = {
                "detailed_research": detailed_research.strip(),
                "status_summary": status_summary,
            }

            # The structured research_result will be passed as reference_index
            # This maintains backward compatibility while providing the new structure
            reference_index = research_result

            # Add details to process monitor before returning
            if process_monitor:
                process_monitor.add_stage_details(
                    stage_name,
                    result_count=len(documents),
                    document_ids=selected_doc_ids,
                    status_summary=status_summary,
                )

            logger.info(
                f"Returning research results with {len(research_result)} documents"
            )

            # Return with new structure in reference_index position
            return (
                response,
                selected_doc_ids,
                file_links,
                None,  # page_section_refs no longer needed
                None,  # section_content_map no longer needed
                reference_index,  # This now contains the structured research output
            )

        else:
            logger.error(
                f"Invalid scope provided to {document_source} subagent: {scope}"
            )
            raise ValueError(f"Invalid scope: {scope}")  # Let the error propagate

    except Exception as e:
        error_msg = (
            f"Error querying {document_source} database (scope: {scope}): {str(e)}"
        )
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            response = []
        else:
            response = {
                "detailed_research": f"**Error processing request for {document_source}:** {str(e)}",
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
