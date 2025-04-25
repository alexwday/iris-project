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
    "internal_compliance": {
        "name": "RBC Compliance Policy - Auditor Independence",
        "description": "RBC policy (FIN-ACC-214-EN) on employing individuals in accounting/financial reporting roles to ensure auditor independence (PwC). Covers hiring restrictions, cooling-off periods, disclosures.",
        "query_type": "semantic search", # Assuming semantic search is appropriate
        "content_type": "compliance policy / internal controls",
        "use_when": "Tier 1 (Domain Specific): Auditor independence rules, hiring ex-auditors, family member employment, disclosure requirements. **Strategy:** Query for specific compliance questions related to auditor independence and hiring. **Query:** Use terms like 'auditor independence', 'cooling-off period', 'PwC employment', 'FIN-ACC-214-EN'.",
    },
    "internal_esg": {
        "name": "RBC Internal ESG Guidance",
        "description": "Internal RBC guidance documents on ESG disclosures. Includes guidance on evaluating prior period changes and the ESG Materiality Framework.",
        "query_type": "semantic search", # Assuming semantic search
        "content_type": "ESG policy / disclosure guidance",
        "use_when": "Tier 1 (Domain Specific): ESG reporting, materiality assessment, prior period ESG changes, alignment with ISSB/CSRD. **Strategy:** Query for specific ESG disclosure questions, materiality framework, or handling prior period adjustments. **Query:** Use terms like 'ESG materiality', 'prior period ESG', 'ISSB alignment', 'CSRD', 'ESG metrics'.",
    },
    "internal_ext_reporting_and_disclosure": {
        "name": "RBC External Reporting and Disclosure Policies",
        "description": "Internal RBC policies covering material information disclosure (LAW-8), subsidiary reporting (FIN-ACC-217), trading revenue reporting (FRTB/OSFI), and engagement/relationships with public accounting firms (FIN-ACC-212, FIN-ACC-213) focusing on auditor independence.",
        "query_type": "semantic search", # Assuming semantic search
        "content_type": "policies and procedures / disclosure guidance / compliance",
        "use_when": "Tier 1 (Domain Specific): Questions about material information disclosure, subsidiary reporting rules, trading revenue classification, engaging external auditors, auditor independence (business/financial relationships). **Strategy:** Query for specific policy numbers (LAW-8, FIN-ACC-217, FIN-ACC-212, FIN-ACC-213), disclosure requirements, trading activity reporting, or auditor engagement/independence rules. **Query:** Use terms like 'material information', 'disclosure policy', 'subsidiary reporting', 'trading revenue', 'FRTB', 'auditor engagement', 'auditor independence', 'FIN-ACC-217', 'FIN-ACC-212', 'FIN-ACC-213'.",
    },
    "internal_global_finance_standards": {
        "name": "RBC Global Finance Standards",
        "description": "Internal RBC standards covering currency reporting, resident/non-resident reporting, foreign currency position accounts (FIN-ACC-14), Global Chart of Accounts minimum standards, and Global FX Rates policy (FIN-ACC-10).",
        "query_type": "semantic search", # Assuming semantic search
        "content_type": "financial standards / reporting requirements / policies",
        "use_when": "Tier 1 (Domain Specific): Questions about currency reporting, resident/non-resident splits, FX position accounts, Global Chart of Accounts structure, or required FX rates for reporting. **Strategy:** Query for specific standard topics or policy numbers (FIN-ACC-14, FIN-ACC-10). **Query:** Use terms like 'currency reporting', 'resident reporting', 'FX position account', 'chart of accounts', 'global FX rates', 'FIN-ACC-14', 'FIN-ACC-10'.",
    },
    "internal_management_reporting": {
        "name": "RBC Management Reporting Policies & Guidance",
        "description": "Internal RBC policies and guidelines for management reporting, covering financial systems, performance metrics (ROE, RORC), intra-group transactions, funds transfer pricing, tax allocation, and average balance reporting (SEC Regulation S-K).",
        "query_type": "semantic search", # Assuming semantic search
        "content_type": "management reporting policies / performance metrics / internal controls",
        "use_when": "Tier 1 (Domain Specific): Questions about management reporting framework, performance metrics (ROE/RORC), intra-group transactions, funds transfer pricing, tax allocation, or average balance reporting requirements. **Strategy:** Query for specific management reporting topics or average balance rules. **Query:** Use terms like 'management reporting', 'performance metrics', 'ROE', 'RORC', 'intra-group', 'funds transfer pricing', 'tax allocation', 'average balance reporting', 'SEC Regulation S-K'.",
    },
    "internal_process_and_controls": {
        "name": "RBC Internal Process and Controls Policies",
        "description": "Internal RBC policies covering Standard GL Naming Convention (FIN-ACC-22), Intra-group Accounts procedures (FIN-ACC-201), Internal Control over Financial Reporting (ICFR - NI 52-109/SOX), and the Enterprise Internal Control Management Policy (ICMP - COSO Framework).",
        "query_type": "semantic search", # Assuming semantic search
        "content_type": "policies and procedures / internal controls / compliance",
        "use_when": "Tier 1 (Domain Specific): Questions about GL naming, intra-group account reconciliation, ICFR requirements (SOX/NI 52-109), or the overall ICMP framework (COSO). **Strategy:** Query for specific policy numbers (FIN-ACC-22, FIN-ACC-201), control frameworks, or process details. **Query:** Use terms like 'GL naming convention', 'intra-group accounts', 'ICFR', 'SOX', 'NI 52-109', 'ICMP', 'COSO framework', 'FIN-ACC-22', 'FIN-ACC-201'.",
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
