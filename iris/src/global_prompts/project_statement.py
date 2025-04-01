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

Our knowledge base includes internal documentation sources such as:
- Corporate Accounting Policy Manuals (CAPMs)
- APG Cheat Sheet Infographics
- APG Wiki Entries
- Internal Accounting Memos

As well as authoritative external sources including:
- IASB Accounting Standards and Interpretations
- EY Technical Guidance
- PWC Accounting Manuals
- KPMG Interpretive Guidance

The system analyzes each inquiry to determine whether to respond based on conversation context or perform targeted research across these documentation sources to provide accurate, policy-compliant guidance."""
        
        return statement
    except Exception as e:
        logger.error(f"Error generating project statement: {str(e)}")
        # Fallback basic statement in case of errors
        return """This project serves RBC's Accounting Policy Group by implementing an intelligent research and response system for accounting policy inquiries using RAG (Retrieval-Augmented Generation)."""