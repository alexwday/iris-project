# services/src/global_prompts/database_statement.py
"""
Database Statement Utility

Provides centralized descriptions of available databases to be included in agent prompts.
This module serves as the single source of truth for database information across the system.
"""
from config.config import Config
import logging
app_config = Config()


logger = logging.getLogger(__name__)

# Complete database configuration for all available databases
AVAILABLE_DATABASES = {
    "internal_capm": {
        "name": "Corporate Accounting Policy Manuals",
        "description": "RBC's comprehensive accounting policies, detailing recognition, measurement, disclosure, and compliance requirements under IFRS and U.S. GAAP frameworks.",
        "query_type": "semantic search",
        "content_type": "policies and procedures",
        "use_when": "Accounting Primary Source: Official RBC policy statements. **Strategy:** The primary source for RBC accounting policy. Always consult first for accounting questions. Check US GAAP flags. **Query:** Use RBC terms, policy areas; check US GAAP flags.",
    },
    "internal_cheatsheets": {  # Renamed from internal_cheatsheet
        "name": "APG Cheatsheets",
        "description": "Concise, 1-2 page summaries and infographics on specific accounting topics, offering quick, visual guidance for key concepts and policies.",
        "query_type": "semantic search",  # Aligned with internal_par process
        "content_type": "summarized guidance / infographics",
        "use_when": "Accounting Core Context: Quick visual summaries. **Strategy:** Always included alongside CAPM for accounting queries to provide definitions/overviews. **Query:** Use concise, topic-focused queries suitable for semantic search.",
    },
    "internal_wiki": {
        "name": "APG Wiki",
        "description": "RBC-specific accounting compilations and guidance for unique transactions, providing detailed interpretations and applications of accounting standards tailored to RBC's business scenarios.",
        "query_type": "semantic search",
        "content_type": "RBC-specific conclusions / guides",
        "use_when": "Accounting Core Context: RBC-specific transaction conclusions. **Strategy:** Always included alongside CAPM for accounting queries, especially for specific transaction types or application examples. **Query:** Focus on application, specific conclusions, industry/scenario terms.",
    },
    "internal_memos": {  # Renamed from internal_memo to match existing key
        "name": "APG Internal Accounting Memos",
        "description": "Detailed technical analyses on complex accounting topics, written by RBC finance teams and approved by the Accounting Policy Group (APG), offering in-depth guidance on specific issues.",
        "query_type": "semantic search",
        "content_type": "technical analysis",
        "use_when": "Accounting Supportive Material: Approved analysis on complex issues. **Strategy:** Consult after CAPM/Wiki/Cheatsheet for deeper analysis on specific complex topics where a memo might exist. **Query:** Focus on application, specific conclusions, industry/scenario terms.",
    },
    "internal_par": {
        "name": "Project Approval Request Guidance",
        "description": "RBC's internal policies and interpretations specifically related to Project Approval Requests (PAR), including workflow, processes, and compliance requirements.",
        "query_type": "semantic search",
        "content_type": "policy guidance / interpretations",
        "use_when": "Tier 1 (Domain Specific): Project Approval Requests Policy questions. **Strategy:** Query if statement relates to PAR; treat as primary within domain. **Query:** Use RBC terms, reference PAR processes/workflows.",
    },
    "internal_aio": {
        "name": "Auditor Independence Office Policy Documents",
        "description": "RBC's internal policies, procedures, and FAQs focused on maintaining auditor independence, including guidelines for business and financial relationships with external auditors.",
        "query_type": "semantic search",
        "content_type": "policy documents / procedures / FAQs",
        "use_when": "Tier 1 (Domain Specific): Auditor Independence Office questions. **Strategy:** Query if statement relates to AIO policies, procedures, or FAQs; treat as primary within domain. **Query:** Use RBC terms, reference AIO processes/workflows.",
    },
    "internal_esg": {
        "name": "Internal ESG Guidance",
        "description": "RBC's policies and frameworks for ESG disclosures, including the ESG Materiality Framework and guidance on evaluating changes to prior period ESG information, aligned with global standards like ISSB and CSRD.",
        "query_type": "semantic search",  # Assuming semantic search
        "content_type": "ESG policy / disclosure guidance",
        "use_when": "Tier 1 (Domain Specific): ESG reporting, materiality assessment, prior period ESG changes, alignment with ISSB/CSRD. **Strategy:** Query for specific ESG disclosure questions, materiality framework, or handling prior period adjustments. **Query:** Use terms like 'ESG materiality', 'prior period ESG', 'ISSB alignment', 'CSRD', 'ESG metrics'.",
    },
    "internal_ext_reporting_and_disclosure": {
        "name": "External Reporting and Disclosure Policies",
        "description": "RBC's guidelines on material information disclosure, subsidiary reporting, trading revenue classification, and auditor independence, ensuring compliance with regulatory frameworks like OSFI, FRTB, and SEC standards.",
        "query_type": "semantic search",  # Assuming semantic search
        "content_type": "policies and procedures / disclosure guidance / compliance",
        "use_when": "Tier 1 (Domain Specific): Questions about material information disclosure, subsidiary reporting rules, trading revenue classification, engaging external auditors, auditor independence (business/financial relationships). **Strategy:** Query for specific policy numbers (LAW-8, FIN-ACC-217, FIN-ACC-212, FIN-ACC-213), disclosure requirements, trading activity reporting, or auditor engagement/independence rules. **Query:** Use terms like 'material information', 'disclosure policy', 'subsidiary reporting', 'trading revenue', 'FRTB', 'auditor engagement', 'auditor independence', 'FIN-ACC-217', 'FIN-ACC-212', 'FIN-ACC-213'.",
    },
    "internal_global_finance_standards": {
        "name": "Global Financial Standards",
        "description": "RBC's policies on currency reporting, resident/non-resident splits, foreign exchange (FX) position accounts, the Global Chart of Accounts structure, and the Global Rates policy, ensuring consistency and compliance in financial reporting across the organization.",
        "query_type": "semantic search",  # Assuming semantic search
        "content_type": "financial standards / reporting requirements / policies",
        "use_when": "Tier 1 (Domain Specific): Questions about currency reporting, resident/non-resident splits, FX position accounts, Global Chart of Accounts structure, or required FX rates for reporting. **Strategy:** Query for specific standard topics or policy numbers (FIN-ACC-14, FIN-ACC-10). **Query:** Use terms like 'currency reporting', 'resident reporting', 'FX position account', 'chart of accounts', 'global FX rates', 'FIN-ACC-14', 'FIN-ACC-10'.",
    },
    "internal_management_reporting": {
        "name": "Management Reporting Policies & Guidance",
        "description": "RBC's policies and guidelines on management reporting frameworks, including performance metrics (ROE, RORC), intra-group transactions, funds transfer pricing, tax allocation, and average balance reporting in compliance with SEC Regulation S-K.",
        "query_type": "semantic search",  # Assuming semantic search
        "content_type": "management reporting policies / performance metrics / internal controls",
        "use_when": "Tier 1 (Domain Specific): Questions about management reporting framework, performance metrics (ROE/RORC), intra-group transactions, funds transfer pricing, tax allocation, or average balance reporting requirements. **Strategy:** Query for specific management reporting topics or average balance rules. **Query:** Use terms like 'management reporting', 'performance metrics', 'ROE', 'RORC', 'intra-group', 'funds transfer pricing', 'tax allocation', 'average balance reporting', 'SEC Regulation S-K'.",
    },
    "internal_process_and_controls": {
        "name": "Internal Process and Controls Policies",
        "description": "RBC's policies on general ledger naming conventions, intra-group account procedures, internal controls over financial reporting (ICFR), and the Enterprise Internal Control Management Policy (ICMP) aligned with frameworks like COSO, SOX, and NI 52-109.",
        "query_type": "semantic search",  # Assuming semantic search
        "content_type": "policies and procedures / internal controls / compliance",
        "use_when": "Tier 1 (Domain Specific): Questions about GL naming, intra-group account reconciliation, ICFR requirements (SOX/NI 52-109), or the overall ICMP framework (COSO). **Strategy:** Query for specific policy numbers (FIN-ACC-22, FIN-ACC-201), control frameworks, or process details. **Query:** Use terms like 'GL naming convention', 'intra-group accounts', 'ICFR', 'SOX', 'NI 52-109', 'ICMP', 'COSO framework', 'FIN-ACC-22', 'FIN-ACC-201'.",
    },
    "external_ey": {
        "name": "EY IFRS Guidance",
        "description": "External accounting guidance and interpretations from EY, including insights, disclosure checklists, and clarifications on the application of IFRS standards.",
        "query_type": "semantic search",
        "content_type": "external guidance",
        "use_when": "External Supplementary: External firm perspective on IFRS; disclosure checklists. **Strategy:** Consult *only if requested by user* or if internal sources are insufficient. Use to supplement internal knowledge, fill gaps, or get external interpretation. Useful for disclosure examples. **Query:** Use standard numbers (IFRS 15, IAS 38), technical terms, specific paragraphs.",
    },
    "external_iasb": {
        "name": "International Accounting Standards Board (IASB)",
        "description": "The official IFRS standards, interpretations (IFRICs/SICs), guidance, illustrative examples, and the basis for conclusions, serving as an authoritative source for IFRS-related queries.",
        "query_type": "semantic search",
        "content_type": "standards and interpretations",
        "use_when": "External Authoritative: Official IFRS standard text, interpretations, basis for conclusions. **Strategy:** Consult *only if requested by user* or if internal sources are insufficient/unclear. Use for official standard text or interpretations. **Query:** Use standard numbers (IFRS 15, IAS 38), interpretations (IFRIC/SIC), technical terms, specific paragraphs.",
    },
    "internal_sab_99": {
        "name": "SAB 99 Materiality Assessment Memos",
        "description": "Internal documents justifying the materiality assessment of financial statement errors, as guided by SEC Staff Accounting Bulletin No. 99. These memos are completed when financial statement errors exceed $120MM and include root cause analysis, control assessment, qualitative factor analysis, and remediation plans.",
        "query_type": "semantic search",
        "content_type": "materiality assessment memos / error analysis / remediation documentation",
        "use_when": "Tier 1 (Domain Specific): Questions about materiality assessments for financial statement errors, SAB 99 compliance, errors exceeding $120MM threshold, qualitative materiality factors, or error remediation. **Strategy:** Query when statement relates to materiality determinations, quantitative/qualitative assessment factors, error evaluation, control deficiencies related to material errors, or corrective action plans. **Query:** Use terms like 'SAB 99', 'materiality assessment', 'financial statement error', '$120MM threshold', 'quantitative materiality', 'qualitative factors', 'root cause analysis', 'control deficiency', 'remediation plan', 'error correction', 'restatement assessment', 'immaterial misstatement', 'intentional misstatement', 'earnings management'.",
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
# def get_available_databases():
#     """
#     Returns the dictionary of available databases.

#     Returns:
#         dict: Dictionary of available database configurations
#     """

#     return AVAILABLE_DATABASES


# logger.debug("Database statement module initialized")

# Mapping dictionary for document_source to name
DOCUMENT_SOURCE_MAPPING = {
    "internal_capm": {
        "name": "Corporate Accounting Policy Manuals",
    },
    "internal_cheatsheets": {
        "name": "APG Cheatsheets",
    },
    "internal_wiki": {
        "name": "APG Wiki",
    },
    "internal_memos": {
        "name": "APG Internal Accounting Memos",
    },
    "internal_par": {
        "name": "Project Approval Request Guidance",
    },
    "internal_aio": {
        "name": "Auditor Independence Office Policy Documents",
    },
    "internal_esg": {
        "name": "Internal ESG Guidance",
    },
    "internal_ext_reporting_and_disclosure": {
        "name": "External Reporting and Disclosure Policies",
    },
    "internal_global_finance_standards": {
        "name": "Global Financial Standards",
    },
    "internal_management_reporting": {
        "name": "Management Reporting Policies & Guidance",
    },
    "internal_process_and_controls": {
        "name": "Internal Process and Controls Policies",
    },
    "external_ey": {
        "name": "EY IFRS Guidance",
    },
    "external_iasb": {
        "name": "International Accounting Standards Board (IASB)",
    },
    "internal_sab_99": {
        "name": "SAB 99 Materiality Assessment Memos",
    }
}

def get_available_databases(filtered=False):
    """
    Returns the dictionary of available databases, each with an 'ad_group' key added.
    """
    # Your existing AVAILABLE_DATABASES dict
    # (Assume it's defined above this function)

    # AD group mapping
    ad_group_to_db_mapping = app_config.get_ad_group_to_db_mapping()

    questions_mapping = {
        "external_ey": [],
        "external_iasb": [
            "Under IFRS, what are examples of temporary differences that lead to a deferred tax liability?",
            "Under IFRS, what are the presentation requirements for compound financial instruments? Please specify the relevant standard and sections."
        ],
        "internal_cheatsheets": [],
        "internal_wiki": [],
        "internal_memos": [],
        "internal_capm": [
            "What is the IFRS and U.S. GAAP difference on firm commitment related to hedging?",
            "Is a call option in a finanical instrument an embedded derivative?",
            "What threshold is considered to be probable under IFRS?",
            "What are the main criteria to derecognize a financial asset under IFRS?"
        ],
        "internal_par": [
            "What would the approval level be if i had a Contract PAR greater than $200MM?",
            "Who is responsible for the fulfillment of all monitoring, reporting, and follow up of the PAR?",
            "According to RBC PAR when is an addendum required?",
            "How do I know if my PAR requires a GE or GOCx meeting?"
        ],
        "internal_aio": [
            "What type of business relationships are acceptable with an external auditor?",
            "What types of financial information are required to be disclosed to external parties?",
            "What arrangements are prohibited under joint marketing and co-branding with external auditors?",
            "What are examples of external parties?"
        ],
        "internal_esg": [
            "If something isn't material should it still go into the Sustainability Report?",
            "Is there a threshold for materiality?",
            "How to treat measurement uncertainty in the ESG framework?",
            "What are the ESG guidelines for revising materiality from prior reporting periods?"
        ],
        "internal_ext_reporting_and_disclosure": [
            "According to the disclosure policy: Who are authorized spokespersons?",
            "What guidelines should be followed for announcements that are not material?",
            "Can an RBC employee speak at a conference during quiet period?",
            "Which teams must review forward-looking information before it's disclosed?"
        ],
        "internal_global_finance_standards": [
            "What are the minimum standards for Non-Interest Expenses in COA reporting?",
            "What is RBC's global FX rate policy?",
            "What are examples of regulatory reports RBC provides OSFI?",
            "What are requirements for resident and non-resident transactions?"
        ],
        "internal_management_reporting": [
            "What are the major performance measurements for management reporting at RBC?",
            "What are the processes for funds transfer pricing?",
            "How are FTE numbers calculated?",
            "How does RBC do rounding for management reporting purposes?"
        ],
        "internal_process_and_controls": [
            "What are the requirements of RBC's internal controls policy?",
            "What is the top down risk based approach in the ICFR policy?",
            "What are the standardized abbreviations for the Chart of Accounts?",
            "How does RBC apply it's ICMP policy for Control Activities?"
        ],
        "internal_sab_99": [
            "What is the most common root cause?",
            "How many errors impacted Deposits?",
            "How many have EUDA related issues?"
        ],
    }

    db_to_ad_group = {}
    for ad_group, db_list in ad_group_to_db_mapping.items():
        for db_name in db_list:
            db_to_ad_group[db_name] = ad_group.strip()
    logger.info(f"Database to AD group mapping: {db_to_ad_group}")

    enriched_databases = {}
    for db_name, db_info in AVAILABLE_DATABASES.items():
        db_info_api = db_info.copy()
        if filtered:
            for key in ["query_type", "content_type", "use_when"]:
                db_info_api.pop(key, None)
        db_info_api["ad_group"] = db_to_ad_group.get(db_name, None)
        db_info_api["questions"] = questions_mapping.get(db_name, [])
        enriched_databases[db_name] = db_info_api

    return enriched_databases
