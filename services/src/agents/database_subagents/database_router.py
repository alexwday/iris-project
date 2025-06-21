# services/src/agents/database_subagents/database_router.py
"""
Database Router Module

This module handles routing database queries to the appropriate
subagent modules. It serves as a central point for all database query routing.

Functions:
    route_query: Asynchronously routes a database query to the appropriate subagent
    route_query_sync: Synchronously routes a database query to the appropriate subagent

Dependencies:
    - asyncio (for async version)
    - logging
    - database subagent modules
    - typing (for type hints)
"""

import asyncio
import importlib
import inspect
import logging
from typing import Any, Dict, Generator, List, Optional, TypeVar, Union, cast, Tuple

from ...initial_setup.env_config import config
from ...global_prompts.database_statement import get_available_databases

# Define response types for database queries
MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
# Define the type returned by subagents (result + optional doc IDs + optional file links + optional page/section refs + optional section content + optional reference index)
FileLink = Dict[str, str]  # Contains 'file_link' and 'document_name'
PageSectionRefs = Dict[int, List[int]]  # Maps page numbers to lists of section IDs
SectionContentMap = Dict[str, str]  # Maps "page_num:section_id" to section content
ReferenceIndex = Dict[str, Dict[str, Any]]  # Maps reference ID to reference details
SubagentResult = Tuple[
    DatabaseResponse,
    Optional[List[str]],
    Optional[List[FileLink]],
    Optional[PageSectionRefs],
    Optional[SectionContentMap],
    Optional[ReferenceIndex],
]
T = TypeVar("T")

# Get available databases from the central configuration
AVAILABLE_DATABASES = get_available_databases()

# Define mapping of internal databases to their document sources
INTERNAL_DATABASES = {
    "internal_par": "internal_par",
    "internal_esg": "internal_esg",
    "internal_capm": "internal_capm",
    "internal_aio": "internal_aio",
    "internal_cheatsheets": "internal_cheatsheets",
    "internal_ext_reporting_and_disclosure": "internal_ext_reporting_and_disclosure",
    "internal_global_finance_standards": "internal_global_finance_standards",
    "internal_management_reporting": "internal_management_reporting",
    "internal_memos": "internal_memos",
    "internal_process_and_controls": "internal_process_and_controls",
    "internal_wiki": "internal_wiki",
}

# Define mapping of external databases to their document configurations
EXTERNAL_DATABASES = {
    "external_ey": {
        "query_type": "single_document",
        "documents": {"ey_international_gaap_2024": 20},
    },
    "external_iasb": {
        "query_type": "multi_document",
        "documents": {
            "iasb_ias": 20,
            "iasb_ifrs": 20,
            "iasb_ifrics": 10,
            "iasb_sic": 10,
        },
    },
}

# Get module logger
logger = logging.getLogger(__name__)


def route_query_sync(
    database: str,
    query: str,
    scope: str,
    token: Optional[str] = None,
    process_monitor=None,
    query_stage_name: Optional[str] = None,
    research_statement: Optional[str] = None,  # NEW PARAMETER for similarity search
) -> SubagentResult:  # Updated return type hint, added query_stage_name
    """
    Synchronously routes a database query to the appropriate subagent module.

    Args:
        database (str): The database identifier.
        query (str): The search query to execute.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token for API access.
        process_monitor (optional): Process monitor instance for tracking token usage.
        query_stage_name (str, optional): The specific stage name for this query instance
                                          provided by the caller (e.g., worker).
        research_statement (str, optional): Research statement for similarity-based filtering.
                                          If provided, will be passed to subagents for embedding-based
                                          document pre-filtering before LLM selection.

    Returns:
        SubagentResult: A tuple containing:
            - Query results (List[Dict] for 'metadata', Dict[str, str] for 'research').
            - Optional list of selected document/chunk IDs used by the subagent.
            - Optional list of file links with document names.

    Raises:
        ValueError: If the database is not recognized or subagent is invalid.
        AttributeError: If the subagent module lacks 'query_database_sync'.
    """
    logger.info(f"Routing query (sync) to database: {database} with scope: {scope}")
    stage_name = query_stage_name or f"db_query_{database}_unknown"

    if database not in AVAILABLE_DATABASES:
        error_msg = f"Unknown database: {database}"
        logger.error(error_msg)
        # Return appropriate error type based on expected scope return type
        if scope == "metadata":
            error_response: DatabaseResponse = []
        else:  # research scope
            error_response: DatabaseResponse = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Unknown database '{database}'.",
            }

        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)

        return (
            error_response,
            None,
            None,
            None,
            None,
            None,
        )  # Return tuple with None for file_links, page_refs, section_content, reference_index

    try:
        # Check if this is an internal database that should use catalog_search
        if database in INTERNAL_DATABASES:
            # Use the unified catalog_search subagent for all internal databases
            from .catalog_search.subagent import query_database_sync

            document_source = INTERNAL_DATABASES[database]
            logger.info(
                f"Using catalog_search subagent for {database} with document_source: {document_source}"
            )

            # Call the catalog_search subagent with the appropriate document_source
            result_tuple = query_database_sync(
                query=query,
                scope=scope,
                document_source=document_source,
                token=token,
                process_monitor=process_monitor,
                query_stage_name=stage_name,
                research_statement=research_statement,  # Pass research statement for similarity filtering
            )
        elif database in EXTERNAL_DATABASES:
            # Use the unified semantic_search subagent for external databases
            from .semantic_search.subagent import query_database_sync

            document_config = EXTERNAL_DATABASES[database]
            logger.info(
                f"Using semantic_search subagent for {database} with config: {document_config}"
            )

            # Call the semantic_search subagent with the appropriate document configuration
            result_tuple = query_database_sync(
                query=query,
                scope=scope,
                document_config=document_config,
                token=token,
                process_monitor=process_monitor,
                query_stage_name=stage_name,
                research_statement=research_statement,  # Pass research statement for context
            )
        else:
            # For non-unified databases, use the original dynamic import logic
            module_path = f"services.src.agents.database_subagents.{database}.subagent"
            subagent_module = importlib.import_module(module_path)
            logger.debug(f"Successfully imported module: {module_path}")

            if not hasattr(subagent_module, "query_database_sync"):
                error_msg = f"Subagent module for '{database}' missing 'query_database_sync' function."
                logger.error(error_msg)  # Log the error

                if process_monitor:
                    process_monitor.add_stage_details(stage_name, error=error_msg)

                # Raise attribute error as it's a code structure issue and sync is expected
                raise AttributeError(error_msg)

            # Use the synchronous version directly - it now returns a tuple
            query_func = subagent_module.query_database_sync
            logger.info(f"Calling query_database_sync for {database}")

            # Check if the function can accept process_monitor and query_stage_name parameters
            sig = inspect.signature(query_func)
            call_args = {"query": query, "scope": scope, "token": token}
            if "process_monitor" in sig.parameters:
                call_args["process_monitor"] = process_monitor
            if "query_stage_name" in sig.parameters:
                call_args["query_stage_name"] = (
                    stage_name  # Pass the specific stage name
                )

            # Pass the process monitor and stage name if the function supports them
            result_tuple = query_func(**call_args)

        logger.info(
            f"Subagent {database} returned tuple with {len(result_tuple) if hasattr(result_tuple, '__len__') else 'unknown'} elements"
        )

        # Handle different tuple lengths for backward compatibility
        if len(result_tuple) == 2:
            # Old format: (result, doc_ids)
            result_tuple = (result_tuple[0], result_tuple[1], None, None, None, None)
        elif len(result_tuple) == 3:
            # Format with file_links: (result, doc_ids, file_links)
            result_tuple = (
                result_tuple[0],
                result_tuple[1],
                result_tuple[2],
                None,
                None,
                None,
            )
        elif len(result_tuple) == 4:
            # Format with page_refs: (result, doc_ids, file_links, page_refs)
            result_tuple = (
                result_tuple[0],
                result_tuple[1],
                result_tuple[2],
                result_tuple[3],
                None,
                None,
            )
        elif len(result_tuple) == 5:
            # Format with section_content: (result, doc_ids, file_links, page_refs, section_content)
            result_tuple = (
                result_tuple[0],
                result_tuple[1],
                result_tuple[2],
                result_tuple[3],
                result_tuple[4],
                None,
            )
        elif len(result_tuple) == 6:
            # Current format: (result, doc_ids, file_links, page_refs, section_content, reference_index)
            # No modification needed - already 6 elements
            pass
        else:
            # Unexpected tuple length - log error and create safe 6-element tuple
            error_msg = (
                f"Unexpected tuple length {len(result_tuple)} from subagent {database}"
            )
            logger.error(error_msg)
            if process_monitor:
                process_monitor.add_stage_details(stage_name, error=error_msg)
            # Create error response tuple
            if scope == "metadata":
                error_response: DatabaseResponse = []
            else:
                error_response: DatabaseResponse = {
                    "detailed_research": f"Error: Unexpected response format from {database}",
                    "status_summary": f"❌ Error: Invalid response format from '{database}'.",
                }
            result_tuple = (error_response, None, None, None, None, None)

        # Now result_tuple is guaranteed to have 6 elements
        # The following line was incorrectly indented after removing the else block

        # End the stage successfully if process monitor is provided
        if process_monitor:
            # If the subagent didn't add document IDs to the stage details, add them now
            if len(result_tuple) > 1 and result_tuple[1]:  # If doc_ids is not None
                process_monitor.add_stage_details(
                    stage_name, document_ids=result_tuple[1]
                )
            # Add file links if available
            if len(result_tuple) > 2 and result_tuple[2]:  # If file_links is not None
                process_monitor.add_stage_details(
                    stage_name, file_links=result_tuple[2]
                )
            # Add page/section refs if available
            if (
                len(result_tuple) > 3 and result_tuple[3]
            ):  # If page_section_refs is not None
                process_monitor.add_stage_details(
                    stage_name, page_section_refs=result_tuple[3]
                )
            # Add section content if available
            if (
                len(result_tuple) > 4 and result_tuple[4]
            ):  # If section_content_map is not None
                process_monitor.add_stage_details(
                    stage_name, section_content_map=result_tuple[4]
                )
            # Add reference index if available
            if (
                len(result_tuple) > 5 and result_tuple[5]
            ):  # If reference_index is not None
                process_monitor.add_stage_details(
                    stage_name, reference_index=result_tuple[5]
                )

            # Add status summary if available in research results
            if scope == "research" and isinstance(result_tuple[0], dict):
                status_summary = result_tuple[0].get("status_summary", "")
                if status_summary:
                    process_monitor.add_stage_details(
                        stage_name, status_summary=status_summary
                    )

        # Return the complete tuple (result, doc_ids, file_links, page_section_refs, section_content_map, reference_index)
        return result_tuple

    except (ImportError, AttributeError) as e:
        # Handle errors related to module loading or function signature
        error_msg = f"Error loading/calling subagent for {database}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            error_response: DatabaseResponse = []
        else:  # research scope
            error_response: DatabaseResponse = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Could not execute query for '{database}' due to internal configuration.",
            }

        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)

        return (
            error_response,
            None,
            None,
            None,
            None,
            None,
        )  # Return tuple with None for file_links, page_refs, section_content, reference_index

    except Exception as e:
        # Catch other potential exceptions during subagent execution
        error_msg = (
            f"Error during query execution for {database} (scope: {scope}): {str(e)}"
        )
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            error_response: DatabaseResponse = []
        else:  # research scope
            error_response: DatabaseResponse = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Failed during query execution for '{database}'.",
            }

        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)

        return (
            error_response,
            None,
            None,
            None,
            None,
            None,
        )  # Return tuple with None for file_links, page_refs, section_content, reference_index
