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

from ...chat_model.model_settings import ENVIRONMENT
from ...global_prompts.database_statement import get_available_databases

# Removed old token usage imports
# from ...llm_connectors.rbc_openai import get_token_usage, reset_token_usage

from typing import Any, Dict, Generator, List, Optional, TypeVar, Union, cast, Tuple # Added Tuple

# Define response types for database queries
MetadataResponse = List[Dict[str, Any]]
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]
# Define the type returned by subagents (result + optional doc IDs)
SubagentResult = Tuple[DatabaseResponse, Optional[List[str]]]
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
    database: str, query: str, scope: str, token: Optional[str] = None, process_monitor=None, query_stage_name: Optional[str] = None
) -> SubagentResult: # Updated return type hint, added query_stage_name
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
            
        return error_response, None # Return tuple

    try:
        module_path = f".{database}.subagent"
        subagent_module = importlib.import_module(
            module_path, package="iris.src.agents.database_subagents"
        )
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
        call_args = {'query': query, 'scope': scope, 'token': token}
        if 'process_monitor' in sig.parameters:
            call_args['process_monitor'] = process_monitor
        if 'query_stage_name' in sig.parameters:
            call_args['query_stage_name'] = stage_name # Pass the specific stage name

        # Pass the process monitor and stage name if the function supports them
        result_tuple: SubagentResult = query_func(**call_args)
        # The following line was incorrectly indented after removing the else block
        # result_tuple: SubagentResult = query_func(query, scope, token) # REMOVED - Handled by **call_args

        # End the stage successfully if process monitor is provided
        if process_monitor:
            # If the subagent didn't add document IDs to the stage details, add them now
            if result_tuple[1]:  # If doc_ids is not None
                process_monitor.add_stage_details(stage_name, document_ids=result_tuple[1])
            
            # Add status summary if available in research results
            if scope == "research" and isinstance(result_tuple[0], dict):
                status_summary = result_tuple[0].get("status_summary", "")
                if status_summary:
                    process_monitor.add_stage_details(stage_name, status_summary=status_summary)
            
            # REMOVED: Stage end is now handled by the caller (_execute_query_worker)
            # process_monitor.end_stage(stage_name, status="completed")

        # Return the complete tuple (result, doc_ids)
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
            
        return error_response, None # Return tuple

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
            
        return error_response, None # Return tuple
