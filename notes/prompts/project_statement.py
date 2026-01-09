# services/src/global_prompts/project_statement.py
"""
Project Statement Utility

Generates a project context statement that can be prefixed to any system prompt.
Provides essential context about the project's purpose and scope.
"""

import logging

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
This project serves RBC Finance by implementing an intelligent research and response system for finance policy inquiries. The system combines comprehensive internal and external finance policy documentation with an autonomous agent-based RAG (Retrieval-Augmented Generation) process. Users can engage in natural conversations about finance policies, and the system will independently research and generate responses as needed.

<KNOWLEDGE_SOURCES>
<INTERNAL_SOURCES>
The system may access internal knowledge sources, which may include policy manuals, 
reference documents, guidelines, and other internal documentation.
</INTERNAL_SOURCES>

<EXTERNAL_SOURCES>
The system may access external knowledge sources, which may include accounting standards, 
professional guidance, and interpretations from standard-setting bodies and professional firms.
</EXTERNAL_SOURCES>
</KNOWLEDGE_SOURCES>

<SYSTEM_PURPOSE>
The system analyzes each inquiry to determine whether to respond based on conversation context 
or perform targeted research across available documentation sources to provide accurate, 
policy-compliant guidance. The specific sources available depend on your access permissions.
</SYSTEM_PURPOSE>
</PROJECT_CONTEXT>"""

        return statement
    except Exception as e:
        logger.debug(f"Error generating project statement: {str(e)}")
        # Fallback basic statement in case of errors
        return """<PROJECT_CONTEXT>This project serves RBC Finance by implementing an intelligent research and response system for finance policy inquiries using RAG (Retrieval-Augmented Generation).</PROJECT_CONTEXT>"""
