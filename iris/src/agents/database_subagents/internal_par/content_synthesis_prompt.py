# internal_par/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content AND status from retrieved PAR documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple PAR documents and providing a status summary.

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
SUBAGENT_ROLE = "an expert research assistant specializing in analyzing internal PAR (Project Approval Request Guidance) documents"

# CO-STAR Framework Components
SUBAGENT_OBJECTIVE = """
To analyze provided PAR document sections against a user query and generate an internal research report for the Summarizer agent.
Your objective is to:
1. Determine the relevance of the provided document content to the user query.
2. Generate a concise status flag summarizing the findings' relevance.
3. Synthesize a detailed, structured research report in Markdown format using ONLY information from the provided documents.
4. Include accurate citations (Document Name, Section Name/Number) *inline* within the report body, immediately following the information they support. Use the most specific section identifier available (name or number).
5. Ensure the report is optimized for consumption by another AI agent (the Summarizer).
6. Adhere strictly to all compliance restrictions.
"""

SUBAGENT_STYLE = """
Analytical and factual.
Focus on precise extraction and clear presentation of information from the source documents.
Structure the report logically with clear headings.
"""

SUBAGENT_TONE = """
Objective and neutral.
Report findings accurately, including any limitations or conflicts in the source material.
"""

SUBAGENT_AUDIENCE = """
The internal Summarizer Agent, which will use your report to construct the final user-facing response.
"""

SUBAGENT_RESPONSE_FORMAT = """
A mandatory tool call to `synthesize_research_findings` containing:
1. `status_summary`: A single-line status flag (e.g., ✅, ℹ️, 📄, ⚠️, ❓).
2. `detailed_research_report`: A comprehensive Markdown string containing the synthesized findings with citations.
"""


def get_content_synthesis_prompt(user_query: str, formatted_documents: str) -> str:
    """
    Generate a prompt for synthesizing content AND status from retrieved PAR documents.

    Args:
        user_query (str): The original user query from the research statement
        formatted_documents (str): The formatted content of retrieved PAR document sections

    Returns:
        str: The formatted prompt for the LLM
    """
    # Fetch all global context statements
    project_statement = get_project_statement()
    database_statement = get_database_statement()
    fiscal_statement = get_fiscal_statement()
    restrictions_statement = get_restrictions_statement()

    prompt_parts = [
        f"You are {SUBAGENT_ROLE}.",

        "<CONTEXT>",
        "You are analyzing sections from the internal PAR (Project Approval Request Guidance) database.",
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
        "Your goal is to provide BOTH a concise status summary flag AND a detailed, structured internal research report based *only* on the provided document sections, formatted for the Summarizer Agent.",

        "<INPUT_DOCUMENTS>",
        f"<USER_QUERY>{user_query}</USER_QUERY>",
        f"<DOCUMENT_SECTIONS>{formatted_documents}</DOCUMENT_SECTIONS>",
        "</INPUT_DOCUMENTS>",

        "<INSTRUCTIONS>",
        "1. **Analyze Relevance:** Carefully read the user query and the provided PAR document section content. Determine how well the content addresses the query.",
        "2. **Generate Status Summary Flag:** Based on your analysis, provide ONLY the single-line status summary flag indicating relevance and completeness. Choose ONE:",
        "   * `✅ Found information directly addressing the query.`",
        "   * `ℹ️ Found related contextual information, but not a direct answer.`",
        "   * `📄 Documents sections found, but they do not contain relevant information for this query.`",
        "   * `⚠️ Conflicting information found across document sections.` (Explain conflicts in the detailed report)",
        "   * `❓ Query is ambiguous based on document section content.` (Explain ambiguity in the detailed report)",
        "3. **Generate Detailed Research Report:** Synthesize a comprehensive internal report using *only* information from the provided document sections.",
        "   * Structure the report clearly using Markdown (e.g., `## Key Findings`, `## Detailed Analysis`, `## Supporting Details`, `## Conflicts/Gaps`).",
        "   * **CRITICAL: Cite specific documents AND section names/numbers accurately *inline* within the report body, immediately following the information they support (e.g., \"... policy requires X (Source: [Document Name], Section: [Section Name/Number])\"). Use the most specific section identifier available (name or number).**",
        "   * If information is conflicting, present all sides clearly.",
        "   * If relevant information is missing from the provided sections, state that clearly.",
        "   * Optimize this report for the Summarizer Agent (another AI) to read and understand easily.",
        "   * Adhere strictly to the <RESTRICTIONS_AND_GUIDELINES> provided in the <CONTEXT>.",
        "4. **Format Output:** Prepare the Status Summary Flag and the Detailed Research Report for the tool call.",
        "</INSTRUCTIONS>",

        "<OUTPUT_SPECIFICATION>",
        "You MUST call the `synthesize_research_findings` tool.",
        "Provide the generated status summary flag (as a single string) and the full detailed research report (as a markdown string) as arguments.",
        "Do not include any other text, preamble, or explanation in your response outside the tool call.",
        "If no relevant document sections were provided or found, the status summary flag should reflect that (`📄`), and the detailed research report argument should state that no analysis is possible based on the provided sections.",
        SUBAGENT_RESPONSE_FORMAT, # Reinforce the expected output format
        "</OUTPUT_SPECIFICATION>",
        "</TASK>",
    ]

    return "\n\n".join(prompt_parts)

# Note: Internal PAR doesn't seem to have an 'individual file synthesis' prompt.
