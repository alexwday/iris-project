# global_prompts/project_statement.py
"""
Project Statement Utility

Generates a project context statement that can be prefixed to any system prompt.
Provides essential context about the project's purpose and scope.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_project_statement() -> str:
    """
    Generate the project context statement.

    Returns:
        str: Formatted project statement
    """
    try:
        statement = """This project serves RBC's Accounting Policy Group by implementing an intelligent research and response system for accounting policy inquiries. The system combines comprehensive internal and external accounting policy documentation with an autonomous agent-based RAG (Retrieval-Augmented Generation) process. Users can engage in natural conversations about accounting policies, and the system will independently research and generate responses as needed.

Our knowledge base includes internal RBC documentation sources:
- Corporate Accounting Policy Manuals (`internal_capm`)
- APG Cheat Sheet Infographics (`internal_cheatsheet`)
- APG Wiki Entries (`internal_wiki`)
- Internal Accounting Memos (`internal_memos`)
- Project Approval Request Guidance (`internal_par`)
- Internal Control over Financial Reporting Policy (`internal_icfr`)

As well as authoritative external sources:
- IASB Standards and Interpretations (`external_iasb`)
- EY IFRS Guidance (`external_ey`)
- KPMG IFRS Guidance (`external_kpmg`)
- PwC IFRS Guidance (`external_pwc`)

The system analyzes each inquiry to determine whether to respond based on conversation context or perform targeted research across these specific documentation sources to provide accurate, policy-compliant guidance."""

        return statement
    except Exception as e:
        logger.error(f"Error generating project statement: {str(e)}")
        # Fallback basic statement in case of errors
        return """This project serves RBC's Accounting Policy Group by implementing an intelligent research and response system for accounting policy inquiries using RAG (Retrieval-Augmented Generation)."""
