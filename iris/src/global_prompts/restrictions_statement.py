# global_prompts/restrictions_statement.py
"""
Restrictions Statement Utility

Provides statements about output restrictions and guidelines that should
be applied across all agent responses for compliance and quality control.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_compliance_restrictions() -> str:
    """
    Generate a statement about compliance restrictions for outputs.
    
    Returns:
        str: Formatted compliance restrictions statement
    """
    try:
        statement = """IMPORTANT COMPLIANCE RESTRICTIONS:

1. Do not provide definitive legal, tax, or regulatory advice. Always frame responses as educational information rather than specific professional advice.

2. All responses must include a disclaimer that the information provided is general guidance and should be verified with the appropriate accounting policy specialist before implementation.

3. When discussing accounting treatments that could have material financial impacts, emphasize the importance of thorough analysis and consultation with the Accounting Policy Group.

4. Never share internal policy information with unauthorized parties. All responses must be treated as confidential and for internal use only.

5. If a query touches on areas outside the scope of accounting policy (such as legal interpretation or regulatory filings), clearly state the limitations of your response and direct the user to the appropriate department.

6. CRITICAL DATA SOURCING RULE: Base all analysis and responses *exclusively* on the provided context (user query, conversation history, or retrieved database documents). NEVER use internal training knowledge, assumptions beyond the provided context, or access external information sources."""
        
        return statement
    except Exception as e:
        logger.error(f"Error generating compliance restrictions: {str(e)}")
        # Fallback statement in case of errors
        return "Responses must include a disclaimer and should not provide definitive legal, tax, or regulatory advice."

def get_quality_guidelines() -> str:
    """
    Generate a statement about output quality guidelines.
    
    Returns:
        str: Formatted quality guidelines statement
    """
    try:
        statement = """OUTPUT QUALITY GUIDELINES:

1. Structure all responses with clear headings and organized sections for readability.

2. Include specific references to relevant accounting policies, standards, or guidelines when applicable (e.g., "According to IFRS 15.31" or "As per CAPM Section 3.4.2").

3. For complex topics, provide both a concise summary at the beginning and detailed explanation in the body of the response.

4. When appropriate, include practical examples to illustrate the application of accounting concepts.

5. Use clear, straightforward language while maintaining technical accuracy. Define specialized accounting terms when they first appear.

6. Where multiple accounting approaches or interpretations exist, clearly present the options and their implications rather than presenting only one view.

7. For research-based responses, include a brief note about the sources consulted to add credibility and transparency."""
        
        return statement
    except Exception as e:
        logger.error(f"Error generating quality guidelines: {str(e)}")
        # Fallback statement in case of errors
        return "Responses should be well-structured, include references, and use clear language."

def get_restrictions_statement() -> str:
    """
    Generate a combined restrictions and guidelines statement for use in prompts.
    
    Returns:
        str: Formatted restrictions statement combining compliance and quality guidelines
    """
    try:
        compliance = get_compliance_restrictions()
        quality = get_quality_guidelines()
        
        combined_statement = f"{compliance}\n\n{quality}"
        return combined_statement
    except Exception as e:
        logger.error(f"Error generating combined restrictions statement: {str(e)}")
        # Fallback combined statement
        return """Responses must include appropriate disclaimers and should not provide definitive legal advice. 
All outputs should be well-structured, reference relevant policies, and use clear language."""
