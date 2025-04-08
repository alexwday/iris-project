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

# Define response types for database queries (ResearchResponse is now Dict)
MetadataResponse = List[Dict[str, Any]]  # List of catalog items
ResearchResponse = Dict[
    str, str
]  # Dictionary with detailed_research and status_summary
DatabaseResponse = Union[MetadataResponse, ResearchResponse]  # Combined type
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
) -> DatabaseResponse:
    """
    Synchronously routes a database query to the appropriate subagent module.

    Args:
        database (str): The database identifier.
        query (str): The search query to execute.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token for API access.

    Returns:
        DatabaseResponse: Query results, either a List[Dict] for 'metadata' scope
                          or a Dict[str, str] for 'research' scope.

    Raises:
        ValueError: If the database is not recognized or subagent is invalid.
        AttributeError: If the subagent module lacks 'query_database_sync'.
    """
    logger.info(f"Routing query (sync) to database: {database} with scope: {scope}")

    if database not in AVAILABLE_DATABASES:
        error_msg = f"Unknown database: {database}"
        logger.error(error_msg)
        # Return appropriate error type based on expected scope return type
        if scope == "metadata":
            return []
        else:  # research scope
            return {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Unknown database '{database}'.",
            }

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

        # Use the synchronous version directly
        query_func = subagent_module.query_database_sync
        logger.debug(f"Calling query_database_sync for {database}")
        result: DatabaseResponse = query_func(query, scope, token)

        # Return the result (List[Dict] for metadata, Dict[str, str] for research)
        return result

    except (ImportError, AttributeError) as e:
        # Handle errors related to module loading or function signature
        error_msg = f"Error loading/calling subagent for {database}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            return []
        else:  # research scope
            return {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Could not execute query for '{database}' due to internal configuration.",
            }
    except Exception as e:
        # Catch other potential exceptions during subagent execution
        error_msg = (
            f"Error during query execution for {database} (scope: {scope}): {str(e)}"
        )
        logger.error(error_msg, exc_info=True)
        if scope == "metadata":
            return []
        else:  # research scope
            return {
                "detailed_research": f"Error: {error_msg}",
                "status_summary": f"❌ Error: Failed during query execution for '{database}'.",
            }
