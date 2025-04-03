# python/iris/src/agents/database_subagents/database_router.py
"""
Database Router Module

This module handles routing database queries to the appropriate subagent modules.
It serves as a central point for all database query routing.

Functions:
    route_database_query: Routes a database query to the appropriate subagent

Dependencies:
    - logging
    - database subagent modules
    - typing (for type hints)
"""

import logging
import importlib
import inspect
from typing import Union, Generator, Any, TypeVar, cast, Optional
from ...global_prompts.database_statement import get_available_databases

# Define a response type for database queries
DatabaseResponse = Union[str, Generator[str, None, None]]
T = TypeVar('T')

# Get available databases from the central configuration
AVAILABLE_DATABASES = get_available_databases()

# Get module logger
logger = logging.getLogger(__name__)

def route_database_query(database: str, query: str, token: Optional[str] = None) -> DatabaseResponse:
    """
    Routes a database query to the appropriate subagent module.
    
    Args:
        database (str): The database identifier
        query (str): The search query to execute
        token (str, optional): Authentication token for API access
            
    Returns:
        DatabaseResponse: Query results from the selected database
        either as a full string or a streaming generator that yields chunks
        
    Raises:
        ValueError: If the database is not recognized
    """
    logger.info(f"Routing query to database: {database}")
    
    # Validate database exists
    if database not in AVAILABLE_DATABASES:
        error_msg = f"Unknown database: {database}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Dynamically import the subagent module
        module_path = f".{database}.subagent"
        
        # Import the specific database module
        subagent_module = importlib.import_module(module_path, package="iris.src.agents.database_subagents")
        logger.debug(f"Successfully imported module: {module_path}")
        
        # Call the query_database function from the module
        result = subagent_module.query_database(query, token)
        
        # Check if result is a generator (for streaming)
        if inspect.isgenerator(result):
            # For streaming results (like from internal_wiki), return the generator
            return result
        else:
            # For non-streaming results (legacy subagents), return the string directly
            return result
    
    except Exception as e:
        logger.error(f"Error routing database query: {str(e)}")
        raise

