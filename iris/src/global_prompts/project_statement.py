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
    Generate the project context statement with XML-style delimiters.

    Returns:
        str: Formatted project statement
    """
    try:
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        statement = f"""<PROJECT_CONTEXT timestamp="{current_time}">
This project serves RBC's Accounting Policy Group by implementing an intelligent research and response system for accounting policy inquiries. The system combines comprehensive internal and external accounting policy documentation with an autonomous agent-based RAG (Retrieval-Augmented Generation) process. Users can engage in natural conversations about accounting policies, and the system will independently research and generate responses as needed.

<KNOWLEDGE_SOURCES>
<INTERNAL_SOURCES>
- Corporate Accounting Policy Manuals (`internal_capm`)
- APG Cheat Sheet Infographics (`internal_cheatsheet`)
- APG Wiki Entries (`internal_wiki`)
- Internal Accounting Memos (`internal_memos`)
- Project Approval Request Guidance (`internal_par`)
- Internal Control over Financial Reporting Policy (`internal_icfr`)
</INTERNAL_SOURCES>

<EXTERNAL_SOURCES>
- IASB Standards and Interpretations (`external_iasb`)
- EY IFRS Guidance (`external_ey`)
- KPMG IFRS Guidance (`external_kpmg`)
- PwC IFRS Guidance (`external_pwc`)
</EXTERNAL_SOURCES>
</KNOWLEDGE_SOURCES>

<SYSTEM_PURPOSE>
The system analyzes each inquiry to determine whether to respond based on conversation context or perform targeted research across these specific documentation sources to provide accurate, policy-compliant guidance.
</SYSTEM_PURPOSE>
</PROJECT_CONTEXT>"""

        return statement
    except Exception as e:
        logger.error(f"Error generating project statement: {str(e)}")
        # Fallback basic statement in case of errors
        return """<PROJECT_CONTEXT>This project serves RBC's Accounting Policy Group by implementing an intelligent research and response system for accounting policy inquiries using RAG (Retrieval-Augmented Generation).</PROJECT_CONTEXT>"""
