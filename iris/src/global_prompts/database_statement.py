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
        "description": "Internal RBC accounting policies (CAPMs) from APG. Notes IFRS/US GAAP differences.",
        "query_type": "semantic search",
        "content_type": "policies and procedures",
        "use_when": "Tier 1: Official RBC policy statements. **Strategy:** Always check first. Check US GAAP flags. Corroborate IFRS w/ IASB. **Query:** Use RBC terms, policy areas; check US GAAP flags.",
    },
    "internal_cheatsheet": {  # Replaces internal_infographic based on user feedback
        "name": "APG Cheat Sheet Infographics",
        "description": "1-2 page summaries/infographics on specific accounting topics (Internal RBC).",
        "query_type": "keyword search",  # Assuming keyword based on previous value for cheatsheet/infographic
        "content_type": "summarized guidance / infographics",
        "use_when": "Tier 2: Quick visual summaries on specific topics. **Strategy:** Consider early for definitions/overviews. **Query:** Use concise, keyword-focused queries.",
    },
    "internal_wiki": {
        "name": "APG Wiki Entries",
        "description": "Accounting conclusions for specific RBC transactions (Internal RBC).",
        "query_type": "semantic search",
        "content_type": "RBC-specific conclusions / guides",
        "use_when": "Tier 2: RBC-specific transaction conclusions. **Strategy:** Query after `internal_capm` or for highly specific transaction types. **Query:** Focus on application, specific conclusions, industry/scenario terms.",
    },
    "internal_memos": {  # Renamed from internal_memo to match existing key
        "name": "Internal Accounting Memos",
        "description": "Internal memos on accounting topics, written by finance, approved by APG.",
        "query_type": "semantic search",
        "content_type": "technical analysis",
        "use_when": "Tier 2: Approved analysis on complex issues. **Strategy:** Query after `internal_capm` or for complex issues where analysis might exist. **Query:** Focus on application, specific conclusions, industry/scenario terms.",
    },
    "internal_par": {
        "name": "Project Approval Request Guidance",
        "description": "RBC internal policy guidance/interpretations for Project Approval Requests (PAR).",
        "query_type": "semantic search",
        "content_type": "policy guidance / interpretations",
        "use_when": "Tier 1 (Domain Specific): Project Approval Requests Policy questions. **Strategy:** Query if statement relates to PAR; treat as primary within domain. **Query:** Use RBC terms, reference PAR processes/workflows.",
    },
    "internal_icfr": {
        "name": "Internal Control over Financial Reporting Policy",
        "description": "RBC guidelines for financial reporting controls (ICFR): identification, evaluation, documentation, responsibilities.",
        "query_type": "semantic search",
        "content_type": "control documentation",
        "use_when": "Tier 1 (Domain Specific): Financial control requirements, compliance, data integrity. **Strategy:** Query if statement relates to ICFR; treat as primary within domain. **Query:** Use RBC terms, reference ICFR processes/workflows.",
    },
    "external_ey": {
        "name": "EY IFRS Guidance",
        "description": "External IFRS guidance and interpretations from EY. Includes disclosure checklist.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Tier 1: External firm perspective on IFRS; disclosure checklists. **Strategy:** Query after internal/IASB for context, interpretation, disclosure. **Query:** Use standard numbers (IFRS 15, IAS 38), technical terms, specific paragraphs.",
    },
    "external_kpmg": {
        "name": "KPMG IFRS Guidance",
        "description": "External IFRS accounting guidance and interpretations from KPMG.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Tier 1: External firm perspective on IFRS. **Strategy:** Query after internal/IASB for context, interpretation. **Query:** Use standard numbers (IFRS 15, IAS 38), technical terms, specific paragraphs.",
    },
    "external_pwc": {
        "name": "PwC IFRS Guidance",
        "description": "External IFRS accounting guidance and interpretations from PwC.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "Tier 1: External firm perspective on IFRS. **Strategy:** Query after internal/IASB for context, interpretation. **Query:** Use standard numbers (IFRS 15, IAS 38), technical terms, specific paragraphs.",
    },
    "external_iasb": {
        "name": "IASB Standards and Interpretations",
        "description": "Official IFRS standards & interpretations (IFRICs/SICs) from IASB. Includes guidance, examples, basis for conclusions.",
        "query_type": "semantic search",
        "content_type": "standards and interpretations",
        "use_when": "Tier 1: Official IFRS standard text, interpretations, basis for conclusions. **Strategy:** Query after relevant internal sources, for official text, or if internal unclear. **Query:** Use standard numbers (IFRS 15, IAS 38), interpretations (IFRIC/SIC), technical terms, specific paragraphs.",
    },
    # Removed internal_infographic as it's covered by internal_cheatsheet
}


def get_database_statement() -> str:
    """
    Returns a formatted statement about available databases for use in agent prompts.
    Uses XML-style delimiters for better sectioning.

    Returns:
        str: Formatted statement describing available databases
    """
    statement = """<AVAILABLE_DATABASES>
The following databases are available for research:

"""

    # Group databases by type for better organization
    internal_dbs = {
        k: v for k, v in AVAILABLE_DATABASES.items() if k.startswith("internal_")
    }
    external_dbs = {
        k: v for k, v in AVAILABLE_DATABASES.items() if k.startswith("external_")
    }

    # Add internal databases section
    statement += "<INTERNAL_DATABASES>\n"
    for db_name, db_info in internal_dbs.items():
        statement += f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
  <CONTENT_TYPE>{db_info['content_type']}</CONTENT_TYPE>
  <QUERY_TYPE>{db_info['query_type']}</QUERY_TYPE>
  <USAGE>{db_info['use_when']}</USAGE>
</DATABASE>

"""
    statement += "</INTERNAL_DATABASES>\n\n"

    # Add external databases section
    statement += "<EXTERNAL_DATABASES>\n"
    for db_name, db_info in external_dbs.items():
        statement += f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
  <CONTENT_TYPE>{db_info['content_type']}</CONTENT_TYPE>
  <QUERY_TYPE>{db_info['query_type']}</QUERY_TYPE>
  <USAGE>{db_info['use_when']}</USAGE>
</DATABASE>

"""
    statement += "</EXTERNAL_DATABASES>\n"
    statement += "</AVAILABLE_DATABASES>"

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
