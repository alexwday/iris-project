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
    Uses XML-style delimiters for better sectioning.

    Returns:
        str: Formatted compliance restrictions statement
    """
    try:
        statement = """<COMPLIANCE_RESTRICTIONS>
<LEGAL_DISCLAIMER>No definitive legal/tax/regulatory advice; provide educational info only.</LEGAL_DISCLAIMER>

<VERIFICATION_REQUIREMENT>Include disclaimer: Info is general guidance, verify with APG specialist before implementation.</VERIFICATION_REQUIREMENT>

<MATERIAL_IMPACTS>Stress need for analysis & APG consultation.</MATERIAL_IMPACTS>

<CONFIDENTIALITY>Internal use only; do not share internal policy externally.</CONFIDENTIALITY>

<OUT_OF_SCOPE>
If a query falls outside the scope of RBC accounting policy (e.g., legal, tax, regulatory filings, general knowledge):
- Clearly state inability to answer
- Explain the system's focus on accounting policy
- If appropriate, suggest consulting the relevant department
- Do not attempt to answer out-of-scope questions
</OUT_OF_SCOPE>

<CRITICAL_DATA_SOURCING>
Base responses **EXCLUSIVELY** on information from:
- The current user query
- Retrieved database documents from this system
- Conversation history *if that history itself contains information clearly sourced from the above*

**ABSOLUTELY NO internal training knowledge, external information, or assumptions beyond this provided context.**

This applies to ALL agents, including Direct Response.
</CRITICAL_DATA_SOURCING>
</COMPLIANCE_RESTRICTIONS>"""

        return statement
    except Exception as e:
        logger.error(f"Error generating compliance restrictions: {str(e)}")
        # Fallback statement in case of errors
        return "Responses must include a disclaimer and should not provide definitive legal, tax, or regulatory advice."


def get_quality_guidelines() -> str:
    """
    Generate a statement about output quality guidelines.
    Uses XML-style delimiters for better sectioning.

    Returns:
        str: Formatted quality guidelines statement
    """
    try:
        statement = """<QUALITY_GUIDELINES>
<STRUCTURE>Structure responses clearly (headings, sections).</STRUCTURE>

<CITATIONS>Cite specific policies/standards/guidelines (e.g., IFRS 15.31, CAPM 3.4.2) when citing provided context.</CITATIONS>

<COMPLEX_TOPICS>For complex topics: Provide concise summary upfront, then details.</COMPLEX_TOPICS>

<EXAMPLES>Use practical examples where helpful, based *only* on provided context.</EXAMPLES>

<LANGUAGE>Use clear language; define technical terms on first use.</LANGUAGE>

<MULTIPLE_APPROACHES>Present multiple approaches/interpretations if found in provided context.</MULTIPLE_APPROACHES>

<SOURCE_ATTRIBUTION>For research responses: Briefly note sources consulted (from provided context).</SOURCE_ATTRIBUTION>
</QUALITY_GUIDELINES>"""

        return statement
    except Exception as e:
        logger.error(f"Error generating quality guidelines: {str(e)}")
        # Fallback statement in case of errors
        return "Responses should be well-structured, include references, and use clear language."


def get_confidence_signaling() -> str:
    """
    Generate guidelines for confidence signaling in responses.
    
    Returns:
        str: Formatted confidence signaling guidelines
    """
    try:
        statement = """<CONFIDENCE_SIGNALING>
When presenting information, indicate your level of confidence based on the sources and context:

<HIGH_CONFIDENCE>
Use when: Multiple authoritative sources agree or when citing direct quotes from official standards
Signal with: Direct, unqualified statements
Example: "IFRS 15 requires revenue to be recognized when performance obligations are satisfied."
</HIGH_CONFIDENCE>

<MEDIUM_CONFIDENCE>
Use when: Sources provide consistent but not identical information, or when interpretation is involved
Signal with: Measured language with mild qualifiers
Example: "Based on the guidance in CAPM and EY materials, it appears that..."
</MEDIUM_CONFIDENCE>

<LOW_CONFIDENCE>
Use when: Sources conflict, information is sparse, or significant interpretation is required
Signal with: Explicit uncertainty markers
Example: "The available sources provide limited guidance on this specific scenario, but suggest..."
</LOW_CONFIDENCE>

<NO_CONFIDENCE>
Use when: No relevant information is found or the question falls outside the scope of the research
Signal with: Clear statements of limitation
Example: "The available sources do not address this specific scenario. This would require consultation with APG."
</NO_CONFIDENCE>
</CONFIDENCE_SIGNALING>"""

        return statement
    except Exception as e:
        logger.error(f"Error generating confidence signaling guidelines: {str(e)}")
        # Fallback statement in case of errors
        return "<CONFIDENCE_SIGNALING>Indicate your level of confidence in responses based on the sources and context.</CONFIDENCE_SIGNALING>"


def get_restrictions_statement() -> str:
    """
    Generate a combined restrictions and guidelines statement for use in prompts.
    Includes confidence signaling guidelines.

    Returns:
        str: Formatted restrictions statement combining compliance, quality, and confidence guidelines
    """
    try:
        compliance = get_compliance_restrictions()
        quality = get_quality_guidelines()
        confidence = get_confidence_signaling()

        combined_statement = f"""<RESTRICTIONS_AND_GUIDELINES>
{compliance}

{quality}

{confidence}
</RESTRICTIONS_AND_GUIDELINES>"""
        return combined_statement
    except Exception as e:
        logger.error(f"Error generating combined restrictions statement: {str(e)}")
        # Fallback combined statement
        return """<RESTRICTIONS_AND_GUIDELINES>
Responses must include appropriate disclaimers and should not provide definitive legal advice. 
All outputs should be well-structured, reference relevant policies, and use clear language.
</RESTRICTIONS_AND_GUIDELINES>"""
