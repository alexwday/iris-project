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
from typing import Union, Generator, Any, TypeVar, cast, Optional, Dict
from ...global_prompts.database_statement import get_available_databases
from ...chat_model.model_settings import ENVIRONMENT
from ...llm_connectors.rbc_openai import get_token_usage, reset_token_usage

# Define a response type for database queries
DatabaseResponse = Union[str, Generator[str, None, None]]
T = TypeVar('T')

# Get available databases from the central configuration
AVAILABLE_DATABASES = get_available_databases()

# Get module logger
logger = logging.getLogger(__name__)

# Global variable for database-specific token usage tracking
_database_token_usage: Dict[str, Dict[str, Any]] = {}

def get_database_token_usage() -> Dict[str, Dict[str, Any]]:
    """
    Get the current database token usage statistics.
    
    Returns:
        Dict[str, Dict[str, Any]]: Token usage statistics per database
    """
    global _database_token_usage
    return _database_token_usage.copy()

def reset_database_token_usage(database=None):
    """
    Reset the database token usage statistics.
    
    Args:
        database (str, optional): Database identifier to reset. 
            If None, resets all databases. Defaults to None.
    """
    global _database_token_usage
    if database:
        if database in _database_token_usage:
            _database_token_usage[database] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0
            }
    else:
        _database_token_usage = {}

def update_database_token_usage(database: str, token_diff: Dict[str, Any]):
    """
    Update token usage for a specific database.
    
    Args:
        database (str): Database identifier
        token_diff (Dict[str, Any]): Token usage difference to add
    """
    global _database_token_usage
    if database not in _database_token_usage:
        _database_token_usage[database] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0
        }
    
    _database_token_usage[database]["prompt_tokens"] += token_diff["prompt_tokens"]
    _database_token_usage[database]["completion_tokens"] += token_diff["completion_tokens"]
    _database_token_usage[database]["total_tokens"] += token_diff["total_tokens"]
    _database_token_usage[database]["cost"] += token_diff["cost"]

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
    
    # Token usage is now handled centrally by log_usage_statistics in rbc_openai.py
    # No need for before/after comparison here.
    
    try:
        # Dynamically import the subagent module
        module_path = f".{database}.subagent"
        
        # Import the specific database module
        subagent_module = importlib.import_module(module_path, package="iris.src.agents.database_subagents")
        logger.debug(f"Successfully imported module: {module_path}")
        
        # Call the query_database function from the module
        result = subagent_module.query_database(query, token)
        
        # Token usage is now handled centrally by log_usage_statistics in rbc_openai.py
        # which is called by the subagent's get_completion helper.
        
        # Always return the result directly
        # The model.py file now handles all types of results appropriately
        return result
    
    except Exception as e:
        # Log the error and re-raise
        # Token usage during the failed call should have been logged by log_usage_statistics if possible
        logger.error(f"Error routing database query to {database}: {str(e)}")
        raise
