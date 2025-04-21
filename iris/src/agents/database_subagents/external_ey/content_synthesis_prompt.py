# external_ey/content_synthesis_prompt.py
"""
Prompts and tool schemas for the External EY Guidance subagent's
content synthesis step.
"""

# Define the tool schema for research synthesis, similar to other subagents
SYNTHESIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "synthesize_ey_guidance_findings",
        "description": "Synthesizes research findings from provided EY guidance context cards and generates a status summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_summary": {
                    "type": "string",
                    "description": "Concise status summary (1 sentence) indicating finding relevance (e.g., '✅ Found direct answer in EY Guidance.', '📄 No relevant info found in EY Guidance.').",
                },
                "detailed_research": {
                    "type": "string",
                    "description": "Detailed, structured markdown report synthesizing information from EY guidance context cards, including citations (Chapter and Section Title/Hierarchy).",
                },
            },
            "required": ["status_summary", "detailed_research"],
        },
    },
}


def get_content_synthesis_prompt(query: str, formatted_cards: str) -> str:
    """
    Generates the user prompt for the final content synthesis LLM call,
    instructing it to use the provided cards and cite sources.

    Args:
        query: The user's original query.
        formatted_cards: The string containing all context cards formatted for the LLM.

    Returns:
        The user prompt string.
    """

    # System Message (Implicitly handled by call_llm structure, but defined here for clarity)
    # Note: The actual system message might be set globally or within call_llm.
    # This prompt focuses on the user message content.
    _system_message_guide = """You are a specialized accounting research assistant with expertise in IFRS and US GAAP standards, specifically analyzing EY guidance materials.
Your task is to answer accounting questions based ONLY on the information provided in the context cards below.
Each card represents a relevant piece of text from the source EY guidance document. Some cards might represent a reconstructed section containing multiple original text chunks.

Context Card Fields:
- Chapter: The name of the chapter the text belongs to.
- Section Title: The title of the specific section.
- Section Hierarchy: The structural path to the section (e.g., "Chapter 1 > Part A > Section 1.1").
- Standard: The primary accounting standard discussed (e.g., IFRS 16, ASC 842).
- Standard Codes: Specific codes or paragraph references within the standard.
- Chapter Tags: Relevant tags associated with the chapter.
- Content: The actual text content from the source document.

Instructions for Answering:
1. Rely EXCLUSIVELY on the "Content" provided in the cards. DO NOT use your external knowledge or training data.
2. Synthesize the information from the relevant cards to provide a comprehensive answer to the user's question.
3. You MUST cite your sources for every significant point or piece of information. Use the "Chapter" and "Section Title" or "Section Hierarchy" from the card(s) you used. Format citations clearly, e.g., [Source: Chapter Name, Section Title] or [Source: Section Hierarchy].
4. If multiple cards support a point, cite all relevant sources.
5. If the provided cards do not contain sufficient information to fully answer the question, clearly state what information is missing or cannot be determined from the context. Do not speculate or fabricate.
6. Structure your response logically, using headings or bullet points if helpful.
7. Provide a concise summary (2-3 sentences) at the end of the detailed research.

Remember: Accuracy and strict adherence to the provided context with proper citations are paramount. Use the provided tool to structure your response."""

    # User Message
    user_message = f"""User Question: {query}

Context Cards from EY Guidance:
{formatted_cards}
---
Based ONLY on the context cards provided above, please answer the user's question using the 'synthesize_ey_guidance_findings' tool. Ensure your detailed research includes clear citations for each point, referencing the Chapter, Section Title, or Section Hierarchy as appropriate."""

    return user_message
