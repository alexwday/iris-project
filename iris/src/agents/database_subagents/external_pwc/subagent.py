# python/iris/src/agents/database_subagents/external_pwc/subagent.py
"""
External PwC Subagent (Async Stub)

This module provides a placeholder asynchronous interface for the External PwC database.
It returns placeholder data according to the expected async structure.

Functions:
    query_database: Asynchronously returns placeholder data for External PwC.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union

# Define response types consistent with database_router
MetadataResponse = List[Dict[str, Any]]
# ResearchResponse is now a dictionary containing detailed research and status
ResearchResponse = Dict[str, str]
DatabaseResponse = Union[MetadataResponse, ResearchResponse]

# Get module logger
logger = logging.getLogger(__name__)


def query_database_sync(
    query: str, scope: str, token: Optional[str] = None
) -> DatabaseResponse:
    """
    Synchronously query the External PwC database (Placeholder Stub).

    Args:
        query (str): Search query for the database.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token (unused in stub).

    Returns:
        DatabaseResponse: Empty list [] for 'metadata', or a placeholder
                          Dict[str, str] for 'research'.
    """
    logger.warning(f"Querying External PwC STUB: '{query}' with scope: {scope}. Returning placeholder data.")
    database_name = "external_pwc"

    # Removed asyncio.sleep for synchronous stub

    if scope == "metadata":
        # Return empty list for metadata scope
        logger.info(f"Returning empty metadata list for {database_name} stub.")
        return []
    elif scope == "research":
        # Return placeholder dictionary for research scope
        placeholder_research = f"Placeholder detailed research for External PwC query: '{query}'. Implementation pending (requires external API integration)."
        placeholder_status = f"ℹ️ Placeholder status for {database_name}."
        logger.info(f"Returning placeholder research dict for {database_name} stub.")
        return {
            "detailed_research": placeholder_research,
            "status_summary": placeholder_status
        }
    else:
        # Handle invalid scope
        logger.error(f"Invalid scope provided to {database_name} subagent stub: {scope}")
        # Return research-style error dict as a fallback
        return {
             "detailed_research": f"Error: Invalid scope '{scope}' provided to {database_name} stub.",
             "status_summary": f"❌ Error: Invalid scope '{scope}'."
        }
