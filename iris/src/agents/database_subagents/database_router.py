# python/iris/src/agents/database_subagents/database_router.py
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
from typing import Any, Dict, Generator, List, Optional, TypeVar, Union, cast

from ...initial_setup.env_config import config
from ...global_prompts.database_statement import get_available_databases

# Removed old token usage imports
# from ...llm_connectors.rbc_openai import get_token_usage, reset_token_usage

from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
    Tuple,
)  # Added Tuple

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

# Get module logger
logger = logging.getLogger(__name__)

# Global variable for database-specific token usage tracking (REMOVED - handled centrally)
# _database_token_usage: Dict[str, Dict[str, Any]] = {}

# Removed old token tracking functions
# def get_database_token_usage() -> Dict[str, Dict[str, Any]]: ...
# def reset_database_token_usage(database=None): ...
# def update_database_token_usage(database: str, token_diff: Dict[str, Any]): ...


def route_query_sync(
    database: str,
    query: str,
    scope: str,
    token: Optional[str] = None,
    process_monitor=None,
    query_stage_name: Optional[str] = None,
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
    # Use the passed-in stage name if available, otherwise default (though it should always be passed now)
    stage_name = query_stage_name or f"db_query_{database}_unknown"
    logger.debug(f"Using process monitor stage name: {stage_name}")

    # REMOVED: Stage start is now handled by the caller (_execute_query_worker)
    # if process_monitor:
    #     process_monitor.start_stage(stage_name)
    #     process_monitor.add_stage_details(stage_name, scope=scope, query=query)

    if database not in AVAILABLE_DATABASES:
        error_msg = f"Unknown database: {database}"
        logger.error(error_msg)
        # Return appropriate error type based on expected scope return type
        error_response: DatabaseResponse
        if scope == "metadata":
            error_response = []
        else:  # research scope
            error_response = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Unknown database '{database}'.",
            }

        # End the stage with error status if process monitor is provided
        # Use the specific stage_name passed from the worker
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)
            # REMOVED: Stage end (even for errors) is now handled by the caller (_execute_query_worker)
            # process_monitor.end_stage(stage_name, status="error")

        return (
            error_response,
            None,
            None,
            None,
            None,
            None,
        )  # Return tuple with None for file_links, page_refs, section_content, reference_index

    try:
        module_path = f"services.src.agents.database_subagents.{database}.subagent"
        subagent_module = importlib.import_module(module_path)
        logger.debug(f"Successfully imported module: {module_path}")

        if not hasattr(subagent_module, "query_database_sync"):
            error_msg = f"Subagent module for '{database}' missing 'query_database_sync' function."
            logger.error(error_msg)  # Log the error

            # End stage with error if process monitor is provided
            # Use the specific stage_name passed from the worker
            if process_monitor:
                process_monitor.add_stage_details(stage_name, error=error_msg)
                # REMOVED: Stage end (even for errors) is now handled by the caller (_execute_query_worker)
                # process_monitor.end_stage(stage_name, status="error")

            # Raise attribute error as it's a code structure issue and sync is expected
            raise AttributeError(error_msg)

        # Use the synchronous version directly - it now returns a tuple
        query_func = subagent_module.query_database_sync
        logger.debug(f"Calling query_database_sync for {database}")

        # Check if the function can accept process_monitor and query_stage_name parameters
        sig = inspect.signature(query_func)
        call_args = {"query": query, "scope": scope, "token": token}
        if "process_monitor" in sig.parameters:
            call_args["process_monitor"] = process_monitor
        if "query_stage_name" in sig.parameters:
            call_args["query_stage_name"] = stage_name  # Pass the specific stage name

        # Pass the process monitor and stage name if the function supports them
        result_tuple = query_func(**call_args)

        # DEBUG: Log what we got back from the subagent
        logger.error(f"DEBUG ROUTER: {database} subagent returned type: {type(result_tuple)}")
        logger.error(f"DEBUG ROUTER: {database} subagent returned length: {len(result_tuple) if hasattr(result_tuple, '__len__') else 'No length'}")
        logger.error(f"DEBUG ROUTER: {database} subagent returned content: {result_tuple}")

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
            error_msg = f"Unexpected tuple length {len(result_tuple)} from subagent {database}"
            logger.error(error_msg)
            if process_monitor:
                process_monitor.add_stage_details(stage_name, error=error_msg)
            # Create error response tuple
            if scope == "metadata":
                error_response = []
            else:
                error_response = {
                    "detailed_research": f"Error: Unexpected response format from {database}",
                    "status_summary": f"❌ Error: Invalid response format from '{database}'.",
                }
            result_tuple = (error_response, None, None, None, None, None)

        # Now result_tuple is guaranteed to have 6 elements
        # The following line was incorrectly indented after removing the else block
        # result_tuple: SubagentResult = query_func(query, scope, token) # REMOVED - Handled by **call_args

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

            # REMOVED: Stage end is now handled by the caller (_execute_query_worker)
            # process_monitor.end_stage(stage_name, status="completed")

        # Return the complete tuple (result, doc_ids, file_links, page_section_refs, section_content_map, reference_index)
        return result_tuple

    except (ImportError, AttributeError) as e:
        # Handle errors related to module loading or function signature
        error_msg = f"Error loading/calling subagent for {database}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        error_response: DatabaseResponse
        if scope == "metadata":
            error_response = []
        else:  # research scope
            error_response = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Could not execute query for '{database}' due to internal configuration.",
            }

        # End the stage with error status if process monitor is provided
        # Use the specific stage_name passed from the worker
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)
            # REMOVED: Stage end (even for errors) is now handled by the caller (_execute_query_worker)
            # process_monitor.end_stage(stage_name, status="error")

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
        error_response: DatabaseResponse
        if scope == "metadata":
            error_response = []
        else:  # research scope
            error_response = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Failed during query execution for '{database}'.",
            }

        # End the stage with error status if process monitor is provided
        # Use the specific stage_name passed from the worker
        if process_monitor:
            process_monitor.add_stage_details(stage_name, error=error_msg)
            # REMOVED: Stage end (even for errors) is now handled by the caller (_execute_query_worker)
            # process_monitor.end_stage(stage_name, status="error")

        return (
            error_response,
            None,
            None,
            None,
            None,
            None,
        )  # Return tuple with None for file_links, page_refs, section_content, reference_index
