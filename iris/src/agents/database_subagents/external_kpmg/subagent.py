# python/iris/src/agents/database_subagents/external_kpmg/subagent.py
"""
External KPMG Subagent

This module provides the interface for querying the External KPMG database.
Currently, it uses a placeholder implementation but is structured for future
integration with the actual KPMG data source.

Functions:
    query_database_sync: Synchronously queries the External KPMG database.
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
    Synchronously query the External KPMG database.

    Args:
        query (str): Search query for the database.
        scope (str): The scope of the query ('metadata' or 'research').
        token (str, optional): Authentication token (unused in stub).

    Returns:
        DatabaseResponse: Empty list [] for 'metadata', or a placeholder
                          Dict[str, str] for 'research'.
    """
    logger.info(f"Querying External KPMG: '{query}' with scope: {scope}.")
    database_name = "external_kpmg" # Keep this as kpmg

    # Removed asyncio.sleep for synchronous stub

    if scope == "metadata":
        # Return empty list for metadata scope
        logger.info(f"Returning empty metadata list for {database_name} stub.")
        return []
    elif scope == "research":
        # Return placeholder dictionary for research scope - TODO: Implement actual query
        # For now, we return a fixed response indicating it's KPMG data
        kpmg_doc_id = "kpmg_insights_into_ifrs_20th_edition" # Use the specified doc ID
        placeholder_research = f"Placeholder research from External KPMG ({kpmg_doc_id}) for query: '{query}'. Actual implementation pending."
        placeholder_status = f"ℹ️ Data retrieved from {database_name} ({kpmg_doc_id})."
        logger.info(f"Returning placeholder research dict for {database_name}.")
        return {
            "detailed_research": placeholder_research, # Use the specific doc ID here
            "status_summary": placeholder_status, # And here
        }
    else:
        # Handle invalid scope
        logger.error(
            f"Invalid scope provided to {database_name} subagent: {scope}"
        )
        # Return research-style error dict as a fallback
        return {
            "detailed_research": f"Error: Invalid scope '{scope}' provided to {database_name}.",
            "status_summary": f"❌ Error: Invalid scope '{scope}'.",
        }
