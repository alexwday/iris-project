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
"""

import logging
import importlib
from ...global_prompts.database_statement import get_available_databases

# Get available databases from the central configuration
AVAILABLE_DATABASES = get_available_databases()

# Get module logger
logger = logging.getLogger(__name__)

def route_database_query(database, query, token=None):
    """
    Routes a database query to the appropriate subagent module.
    
    Args:
        database (str): The database identifier
        query (str): The search query to execute
        token (str, optional): Authentication token for API access
            
    Returns:
        str: Query results from the selected database
        
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
        return subagent_module.query_database(query, token)
    
    except Exception as e:
        logger.error(f"Error routing database query: {str(e)}")
        raise

