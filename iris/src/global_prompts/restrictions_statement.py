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

1. No definitive legal/tax/regulatory advice; provide educational info only.
2. Include disclaimer: Info is general guidance, verify with APG specialist before implementation.
3. Material impacts: Stress need for analysis & APG consultation.
4. Confidentiality: Internal use only; do not share internal policy externally.
5. **Out-of-Scope Queries:** If a query falls outside the scope of RBC accounting policy (e.g., legal, tax, regulatory filings, general knowledge), clearly state inability to answer, explain the system's focus on accounting policy, and if appropriate, suggest consulting the relevant department. Do not attempt to answer out-of-scope questions.
6. **CRITICAL DATA SOURCING:** Base responses **EXCLUSIVELY** on information from: (a) the current user query, (b) retrieved database documents from this system, or (c) conversation history *if that history itself contains information clearly sourced from (a) or (b)*. **ABSOLUTELY NO internal training knowledge, external information, or assumptions beyond this provided context.** This applies to ALL agents, including Direct Response."""

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

1. Structure responses clearly (headings, sections).
2. Cite specific policies/standards/guidelines (e.g., IFRS 15.31, CAPM 3.4.2) when citing provided context.
3. Complex topics: Provide concise summary upfront, then details.
4. Use practical examples where helpful, based *only* on provided context.
5. Use clear language; define technical terms on first use.
6. Present multiple approaches/interpretations if found in provided context.
7. Research responses: Briefly note sources consulted (from provided context)."""

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
