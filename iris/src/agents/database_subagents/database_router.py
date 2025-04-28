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
    database: str, query: str, scope: str, token: Optional[str] = None
) -> SubagentResult: # Updated return type hint
    """
    Synchronously routes a database query to the appropriate subagent module.

    Args:
        database (str): The database identifier.
        query (str): The search query to execute.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token for API access.

    Returns:
        SubagentResult: A tuple containing:
            - Query results (List[Dict] for 'metadata', Dict[str, str] for 'research').
            - Optional list of selected document/chunk IDs used by the subagent.

    Raises:
        ValueError: If the database is not recognized or subagent is invalid.
        AttributeError: If the subagent module lacks 'query_database_sync'.
    """
    logger.info(f"Routing query (sync) to database: {database} with scope: {scope}")

    if database not in AVAILABLE_DATABASES:
        error_msg = f"Unknown database: {database}"
        logger.error(error_msg)
        # Return appropriate error type based on expected scope return type
        # Return appropriate error type based on expected scope return type, plus None for doc_ids
        error_response: DatabaseResponse
        if scope == "metadata":
            error_response = []
        else:  # research scope
            error_response = {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Unknown database '{database}'.",
            }
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
            # Raise attribute error as it's a code structure issue and sync is expected
            raise AttributeError(error_msg)

        # Use the synchronous version directly - it now returns a tuple
        query_func = subagent_module.query_database_sync
        logger.debug(f"Calling query_database_sync for {database}")
        # result: DatabaseResponse = query_func(query, scope, token) # Old call
        result_tuple: SubagentResult = query_func(query, scope, token) # New call returns tuple

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
        return error_response, None # Return tuple
