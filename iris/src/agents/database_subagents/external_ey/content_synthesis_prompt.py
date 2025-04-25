# external_ey/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content AND status from retrieved EY guidance documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple EY guidance context cards and providing a status summary.

This version implements advanced prompt engineering techniques:
1. CO-STAR framework (Context, Objective, Style, Tone, Audience, Response Format)
2. Sectioning with XML-style delimiters
3. Inclusion of global context (Project, Database, Fiscal, Restrictions)
"""

from ....global_prompts.project_statement import get_project_statement
from ....global_prompts.database_statement import get_database_statement
from ....global_prompts.fiscal_calendar import get_fiscal_statement
from ....global_prompts.restrictions_statement import get_restrictions_statement

# Define the subagent role
SUBAGENT_ROLE = "an expert research assistant specializing in analyzing external EY accounting guidance documents"

# CO-STAR Framework Components
SUBAGENT_OBJECTIVE = """
To analyze provided EY guidance context cards against a user query and generate an internal research report optimized for the Summarizer agent.
Your objective is to:
1. Determine the relevance of the provided context card content to the user query.
2. Generate a concise status flag summarizing the findings' relevance.
3. Synthesize a detailed, structured research report in Markdown format using ONLY information from the provided context cards.
4. **CRITICAL:** Include accurate citations *inline* within the report body, immediately following the information they support. Use the specific fields from the context cards: `Chapter`, `Section Title`, `Section Hierarchy`, `Standard`, `Standard Codes`. Format citations like: `(Source: EY Guidance, Chapter: [Chapter Name], Section: [Section Title/Hierarchy], Standard: [Standard], Code: [Standard Codes])`. Use the most specific location identifier available (Section Title or Hierarchy). Include Standard/Code if relevant to the cited point.
5. Ensure the report is optimized for consumption by another AI agent (the Summarizer).
6. Adhere strictly to all compliance restrictions.
"""

SUBAGENT_STYLE = """
Analytical and factual.
Focus on precise extraction and clear presentation of information from the source context cards.
Structure the report logically with clear headings (e.g., ## Key Findings, ## Detailed Analysis).
"""

SUBAGENT_TONE = """
Objective and neutral.
Report findings accurately, including any limitations or conflicts in the source material.
"""

SUBAGENT_AUDIENCE = """
The internal Summarizer Agent, which will use your report to construct the final user-facing response.
"""

# This variable defines the structure the LLM should aim for in its tool call arguments.
SUBAGENT_RESPONSE_FORMAT = """
Use the `synthesize_research_findings` tool with the following arguments:
- `status_summary`: A single-line status flag string (e.g., "✅ Found information directly addressing the query in the EY cards.").
- `detailed_research_report`: A comprehensive Markdown string containing the synthesized findings with inline citations, based ONLY on the provided context cards.
"""

# Define the tool schema for research synthesis
SYNTHESIS_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "synthesize_research_findings", # Use generic name expected by calling code
        "description": "Synthesizes research findings from provided EY guidance context cards and generates a status summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_summary": {
                    "type": "string",
                    "description": "Concise status summary flag (✅, ℹ️, 📄, ⚠️, ❓) indicating finding relevance based *only* on the provided EY guidance context cards.",
                },
                "detailed_research_report": { # Renamed from detailed_research
                    "type": "string",
                    "description": "Detailed, structured markdown report synthesizing information *only* from EY guidance context cards, including mandatory inline citations (Chapter, Section Title/Hierarchy, Standard, Standard Codes). Optimized for the Summarizer Agent.",
                },
            },
            "required": ["status_summary", "detailed_research_report"],
        },
    },
}


def get_content_synthesis_prompt(query: str, formatted_cards: str) -> str:
    """
    Generates the user prompt for the final content synthesis LLM call,
    instructing it to use the provided cards, cite sources inline, and generate a status flag.

    Args:
        query: The user's original query.
        formatted_cards: The string containing all context cards formatted for the LLM.

    Returns:
        The user prompt string.
    """
    # Fetch all global context statements
    project_statement = get_project_statement()
    database_statement = get_database_statement()
    fiscal_statement = get_fiscal_statement()
    restrictions_statement = get_restrictions_statement()

    prompt_parts = [
        f"You are {SUBAGENT_ROLE}.",
        "<CONTEXT>",
        "You are analyzing context cards derived from external EY accounting guidance documents.",
        "Each card represents a relevant piece of text from the source EY guidance document.",
        "Context Card Fields Available:",
        "- Chapter: The name of the chapter the text belongs to.",
        "- Section Title: The title of the specific section.",
        "- Section Hierarchy: The structural path to the section (e.g., 'Chapter 1 > Part A > Section 1.1').",
        "- Standard: The primary accounting standard discussed (e.g., IFRS 16, ASC 842).",
        "- Standard Codes: Specific codes or paragraph references within the standard.",
        "- Chapter Tags: Relevant tags associated with the chapter.",
        "- Content: The actual text content from the source document.",
        "Below is essential context about the project, available data, current fiscal period, and restrictions:",
        project_statement,
        database_statement,
        fiscal_statement,
        restrictions_statement,
        "</CONTEXT>",
        "<OBJECTIVE>",
        SUBAGENT_OBJECTIVE,
        "</OBJECTIVE>",
        "<STYLE>",
        SUBAGENT_STYLE,
        "</STYLE>",
        "<TONE>",
        SUBAGENT_TONE,
        "</TONE>",
        "<AUDIENCE>",
        SUBAGENT_AUDIENCE,
        "</AUDIENCE>",
        "<TASK>",
        "Your goal is to provide BOTH a concise status summary flag AND a detailed, structured internal research report based *only* on the provided EY guidance context cards, formatted for the Summarizer Agent.",
        "<INPUT_DOCUMENTS>",
        f"<USER_QUERY>{query}</USER_QUERY>",
        f"<CONTEXT_CARDS>{formatted_cards}</CONTEXT_CARDS>",
        "</INPUT_DOCUMENTS>",
        "<INSTRUCTIONS>",
        "1. **Analyze Relevance:** Carefully read the user query and the 'Content' field within the provided EY guidance context cards. Determine how well the content addresses the query.",
        "2. **Generate Status Summary Flag:** Based on your analysis, provide ONLY the single-line status summary flag indicating relevance and completeness. Choose ONE:",
        "   * `✅ Found information directly addressing the query in the EY cards.`",
        "   * `ℹ️ Found related contextual information in the EY cards, but not a direct answer.`",
        "   * `📄 EY cards found, but they do not contain relevant information for this query.`",
        "   * `⚠️ Conflicting information found across EY cards.` (Explain conflicts in the detailed report)",
        "   * `❓ Query is ambiguous based on EY card content.` (Explain ambiguity in the detailed report)",
        "   **Strict Adherence to Data Sourcing:** Remember to strictly follow the `<CRITICAL_DATA_SOURCING>` rules defined in the global `<RESTRICTIONS_AND_GUIDELINES>`. Your report MUST be derived *exclusively* from the text within the 'Content' field of the `<CONTEXT_CARDS>`. Do NOT introduce any facts, concepts, standard names/numbers, definitions, interpretations, or any external knowledge not explicitly present *within* the provided card content.",
        "3. **Generate Detailed Research Report:** Synthesize a comprehensive internal report using *only* information from the 'Content' field of the provided context cards.",
        "   * Structure the report clearly using Markdown (e.g., `## Key Findings`, `## Detailed Analysis`, `## Supporting Details`, `## Conflicts/Gaps`).",
        '   * **CRITICAL CITATION: Cite sources accurately *inline* within the report body, immediately following the information they support. Use the most specific document identifier available (e.g., Document Name, Filename if provided in context) and the full hierarchical path (e.g., Chapter > Section > Subsection Title/Hierarchy). Include Standard and Standard Codes if relevant and available in the context card. Format citations clearly like: `(Source: [Document Identifier], Path: [Full Hierarchy Path], Standard: [Standard], Code: [Standard Code])`. If a specific field (like Hierarchy, Standard, or Code) is not available for a source, omit that field from the citation for that source.**',
        "   * **CRITICAL STANDARD FILTERING:** Focus your synthesis *only* on information relevant to the accounting standard specified or implied in the <USER_QUERY> (Defaulting to IFRS if none is specified). Actively filter out and ignore information related to other standards (e.g., US GAAP) unless that standard was explicitly requested in the query.**",
        "   * **CRITICAL TYPE FILTERING:** Similarly, if the <USER_QUERY> specifies a particular accounting type (e.g., 'financial assets', 'liabilities'), focus your synthesis *only* on information directly relevant to that type. Actively filter out and ignore information related to other types unless the query explicitly asks for comparison or broader context.**",
        "   * If multiple cards support a point, synthesize the information and cite all relevant sources clearly.",
        "   * If information is conflicting, present all sides clearly with their respective citations.",
        "   * If relevant information is missing from the provided cards, state that clearly.",
        "   * Optimize this report for the Summarizer Agent (another AI) to read and understand easily.",
        "   * Furthermore, pay special attention to any logical tests or criteria described in the content (e.g., conditions connected by 'and'/'or', multi-part tests, 'if...then' statements). Reproduce the full structure and wording of these tests accurately in your report, using formatting like bullet points or nested lists if needed for clarity.",
        "   * Adhere strictly to the <RESTRICTIONS_AND_GUIDELINES> provided in the <CONTEXT>.",
        "4. **Format Output:** Prepare the Status Summary Flag and the Detailed Research Report for the tool call.",
        "</INSTRUCTIONS>",
        "<OUTPUT_SPECIFICATION>",
        "You MUST call the `synthesize_research_findings` tool.",
        "The tool call arguments MUST contain exactly two keys: `status_summary` (string) and `detailed_research_report` (markdown string).", # Explicitly state required keys
        "Provide the generated status summary flag as the value for `status_summary`.",
        "Provide the full detailed research report (with inline citations) as the value for `detailed_research_report`.",
        "Do not include any other text, preamble, or explanation in your response outside the tool call's JSON arguments.",
        "If no relevant context cards were provided or found, the `status_summary` argument should reflect that (e.g., '📄 ...'), and the `detailed_research_report` argument should state that no analysis is possible based on the provided cards.",
        # SUBAGENT_RESPONSE_FORMAT, # No longer needed here as instructions are explicit
        "</OUTPUT_SPECIFICATION>",
        "</TASK>",
    ]

    return "\n\n".join(prompt_parts)
