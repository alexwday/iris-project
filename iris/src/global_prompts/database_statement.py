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
        "name": "Central Accounting Policy Manual",
        "description": "Central Accounting Policy Manual - Contains formal accounting policies",
        "query_type": "semantic search",
        "content_type": "policies and procedures",
        "use_when": "Needing official policy statements, procedures, or authoritative guidance"
    },
    "internal_wiki": {
        "name": "Internal Wiki",
        "description": "Internal wiki with practical examples and implementation guides",
        "query_type": "semantic search",
        "content_type": "practical guides",
        "use_when": "Seeking practical implementation guidance, examples, or informal advice"
    },
    "internal_cheatsheet": {
        "name": "Accounting Cheatsheets",
        "description": "Quick reference guides and cheatsheets for accounting concepts",
        "query_type": "keyword search",
        "content_type": "quick references",
        "use_when": "Looking for quick summaries or reference material"
    },
    "internal_memos": {
        "name": "Technical Memos",
        "description": "Technical memoranda on complex accounting issues",
        "query_type": "semantic search",
        "content_type": "technical analysis",
        "use_when": "Researching complex or nuanced accounting interpretations"
    },
    "internal_par": {
        "name": "Process and Review Documentation",
        "description": "Process and review documentation for accounting workflows",
        "query_type": "semantic search",
        "content_type": "workflow documentation",
        "use_when": "Understanding accounting process workflows and review requirements"
    },
    "internal_icfr": {
        "name": "Internal Controls Framework",
        "description": "Documentation on internal controls over financial reporting",
        "query_type": "semantic search",
        "content_type": "control documentation",
        "use_when": "Researching internal controls, compliance requirements, or audit procedures"
    },
    "external_ey": {
        "name": "EY Accounting Resources",
        "description": "EY accounting resources, guides, and publications",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Seeking external auditor perspective or accounting firm guidance"
    },
    "external_kpmg": {
        "name": "KPMG Accounting Resources",
        "description": "KPMG accounting resources, guides, and publications",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Seeking external auditor perspective or accounting firm guidance"
    },
    "external_pwc": {
        "name": "PwC Accounting Resources",
        "description": "PwC accounting resources, guides, and publications",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Seeking external auditor perspective or accounting firm guidance"
    },
    "external_iasb": {
        "name": "IASB Publications",
        "description": "Official IASB publications, standards, and interpretations",
        "query_type": "semantic search",
        "content_type": "standards and interpretations",
        "use_when": "Researching official accounting standards, interpretations, or basis for conclusions"
    },
    "internal_infographic": {
        "name": "Accounting Infographics",
        "description": "Visual infographics and diagrams explaining accounting concepts",
        "query_type": "keyword search",
        "content_type": "visual explanations",
        "use_when": "Looking for visual explanations of processes or concepts"
    }
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