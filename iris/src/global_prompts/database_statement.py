# global_prompts/database_statement.py
"""
Database Statement Utility

Provides centralized descriptions of available databases to be included in agent prompts.
This module serves as the single source of truth for database information across the system.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Complete database configuration for all available databases
AVAILABLE_DATABASES = {
    "internal_capm": {
        "name": "Corporate Accounting Policy Manuals",
        "description": "Corporate Accounting Policy Manuals. Contains internal accounting policies published by the Accounting Policy Group in RBC. Flags IFRS/US GAAP differences.",
        "query_type": "semantic search",
        "content_type": "policies and procedures",
        "use_when": "Tier 1 (Official RBC Policy). Primary source for official policy statements. Check US GAAP flags. Corroborate with IASB for IFRS."
    },
     "internal_cheatsheet": { # Replaces internal_infographic based on user feedback
        "name": "APG Cheat Sheet Infographics",
        "description": "Summarized accounting guidance in one to two pages on specific limited topics. Internal RBC documentation.",
        "query_type": "keyword search", # Assuming keyword based on previous value for cheatsheet/infographic
        "content_type": "summarized guidance / infographics",
        "use_when": "Tier 2 (Implementation Guidance). Use for quick visual summaries on limited topics."
    },
    "internal_wiki": {
        "name": "APG Wiki Entries",
        "description": "Contains accounting treatment conclusions for specific RBC transactions. Internal RBC documentation.",
        "query_type": "semantic search",
        "content_type": "RBC-specific conclusions / guides",
        "use_when": "Tier 2 (Implementation Guidance). Use for RBC-specific issue conclusions."
    },
    "internal_memos": { # Renamed from internal_memo to match existing key
        "name": "Internal Accounting Memos",
        "description": "Internal accounting memos written by finance and approved by APG. Internal RBC documentation.",
        "query_type": "semantic search",
        "content_type": "technical analysis",
        "use_when": "Tier 2 (Implementation Guidance). Use for approved analysis on complex issues."
    },
    "internal_par": {
        "name": "Project Approval Request Guidance",
        "description": "RBC internal Project Approval Requests Policy guidance and interpretations.",
        "query_type": "semantic search",
        "content_type": "policy guidance / interpretations",
        "use_when": "Tier 1 (Primary for its specific domain). Use for Project Approval Requests Policy questions."
    },
    "internal_icfr": {
        "name": "Internal Control over Financial Reporting Policy",
        "description": "Comprehensive guidelines for maintaining reliable financial reporting controls. Outlines approach for identifying, evaluating, documenting controls and management responsibilities.",
        "query_type": "semantic search",
        "content_type": "control documentation",
        "use_when": "Tier 1 (Primary for its specific domain). Use for researching financial control requirements, compliance, and data integrity."
    },
    "external_ey": {
        "name": "EY IFRS Guidance",
        "description": "IFRS accounting guidance and interpretations published by EY. Includes IFRS disclosure requirement checklist.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Tier 1 (External IFRS Guidance). Use for external firm perspective and disclosure checklists."
    },
    "external_kpmg": {
        "name": "KPMG IFRS Guidance",
        "description": "IFRS accounting guidance and interpretations published by KPMG.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Tier 1 (External IFRS Guidance). Use for external firm perspective."
    },
    "external_pwc": {
        "name": "PwC IFRS Guidance",
        "description": "IFRS accounting guidance and interpretations published by PwC.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Tier 1 (External IFRS Guidance). Use for external firm perspective."
    },
    "external_iasb": {
        "name": "IASB Standards and Interpretations",
        "description": "Official IFRS standards and IFRICs/SICs interpretations published by the International Accounting Standards Board. Includes main guidance, examples, and basis for conclusions.",
        "query_type": "semantic search",
        "content_type": "standards and interpretations",
        "use_when": "Tier 1 (Official IFRS Standards). Use for official standard text, interpretations (IFRICs/SICs), and basis for conclusions."
    }
    # Removed internal_infographic as it's covered by internal_cheatsheet
}

def get_database_statement() -> str:
    """
    Returns a formatted statement about available databases for use in agent prompts.
    
    Returns:
        str: Formatted statement describing available databases
    """
    statement = """
# AVAILABLE DATABASES

The following databases are available for research:

"""
    
    # Add each database with description
    for db_name, db_info in AVAILABLE_DATABASES.items():
        statement += f"## {db_info['name']} (`{db_name}`)\n"
        statement += f"{db_info['description']}\n"
        statement += f"- Content type: {db_info['content_type']}\n"
        statement += f"- Search method: {db_info['query_type']}\n"
        statement += f"- Use when: {db_info['use_when']}\n\n"
    
    return statement

# Export database configuration for other modules
def get_available_databases():
    """
    Returns the dictionary of available databases.
    
    Returns:
        dict: Dictionary of available database configurations
    """
    return AVAILABLE_DATABASES

logger.debug("Database statement module initialized")
