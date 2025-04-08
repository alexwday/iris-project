# internal_capm/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content AND status from retrieved CAPM documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple CAPM documents and providing a status summary.

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
SUBAGENT_ROLE = "an expert research assistant specializing in analyzing internal CAPM (Central Accounting Policy Manual) documents"

# CO-STAR Framework Components
SUBAGENT_OBJECTIVE = """
To analyze provided CAPM document sections against a user query and generate an internal research report optimized for the Summarizer agent.
Your objective is to:
1. Determine the relevance of the provided document content to the user query.
2. Generate a concise status flag summarizing the findings' relevance.
3. Extract key facts and direct quotes relevant to the query from the provided documents, presenting them as a structured list (e.g., bullet points).
4. **CRITICAL:** Include accurate citations (Document Name, Section Name/Number) *inline* within the report body, immediately following the information they support (e.g., `- Key finding text (Source: [Document Name], Section: [Section Name/Number])`). Use the most specific section identifier available (name or number).
5. Ensure the report is highly optimized for efficient parsing and consumption by another AI agent (the Summarizer).
6. Adhere strictly to all compliance restrictions.
"""

SUBAGENT_STYLE = """
Analytical and factual.
Focus on precise extraction and clear, structured presentation of information as key points or quotes.
Avoid narrative prose; prioritize direct information transfer.
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
    Generate a prompt for synthesizing content AND status from retrieved CAPM documents.

    Args:
        user_query (str): The original user query from the research statement
        formatted_documents (str): The formatted content of retrieved CAPM document sections

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
        "You are analyzing sections from the internal CAPM (Central Accounting Policy Manual).",
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
        "1. **Identify Key Context in Query:** First, identify any specific key accounting context mentioned in the User Query (e.g., 'asset', 'liability', 'equity', 'IFRS', 'US GAAP', specific standard numbers). This context is CRITICAL for filtering.",
        "2. **Analyze Relevance within Context:** Carefully read the user query and the provided CAPM document section content. Determine how well the content addresses the query **specifically within the identified key accounting context.**",
        "3. **Generate Status Summary Flag:** Based on your context-aware analysis, provide ONLY the single-line status summary flag indicating relevance and completeness. Choose ONE:",
        "   * `✅ Found information directly addressing the query within the specified context.`",
        "   * `ℹ️ Found related contextual information, but not a direct answer for the specified context.`",
        "   * `📄 Document sections found, but they do not contain relevant information for the specified context.`",
        "   * `⚠️ Conflicting information found across document sections regarding the specified context.` (Explain conflicts in the detailed report)",
        "   * `❓ Query is ambiguous based on document section content regarding the specified context.` (Explain ambiguity in the detailed report)",
        "4. **Generate Focused Detailed Research Report:** Extract key facts and direct quotes relevant to the query **AND strictly pertaining to the identified key accounting context** using *only* information from the provided document sections. Format this as a structured list (e.g., bullet points) optimized for the Summarizer Agent.",
        "   * **CRITICAL FILTERING:** If the query specifies 'assets', ONLY extract information about assets, even if the section also discusses liabilities. If the query specifies 'IFRS', ONLY extract IFRS-related information. Actively ignore and filter out information related to other contexts not mentioned in the query.",
        "   * Present information concisely. Use bullet points for key facts or directly quote relevant sentences/paragraphs that match the query's context.",
        "   * **CRITICAL CITATION: Cite specific documents AND section names/numbers accurately *inline* within the report body, immediately following the information they support. Example: `- The policy states X is required for assets. (Source: CAPM Policy 123 - Revenue Recognition, Section: 4.2 Scope)` Use the most specific section identifier available (name or number).**",
        "   * If information is conflicting within the specified context, present the conflicting points clearly with their respective citations.",
        "   * If relevant information for the specified context is missing from the provided sections, state that clearly (e.g., `- No information found regarding asset treatment under IFRS 15 in the provided sections.`).",
        "   * Do NOT add introductory/concluding sentences or narrative prose. Focus on direct, context-filtered information transfer.",
        "   * Adhere strictly to the <RESTRICTIONS_AND_GUIDELINES> provided in the <CONTEXT>.",
        "5. **Format Output:** Prepare the Status Summary Flag and the context-filtered Detailed Research Report (as a single markdown string with bullet points/quotes and citations) for the tool call.",
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


# --- Keep the individual file synthesis prompt and schema as is for now ---

def get_individual_file_synthesis_prompt(
    user_query: str, formatted_document: str
) -> str:
    """
    Generate a prompt for synthesizing content from a single CAPM document.
    Used when total content exceeds token limits and each file needs individual processing.

    Args:
        user_query (str): The original user query
        formatted_document (str): The formatted content of a single CAPM document

    Returns:
        str: The formatted prompt for the LLM
    """
    # NOTE: This prompt is simpler and doesn't use the full framework or restrictions yet.
    # It might need updating later if it proves problematic or needs the same rigor.
    prompt = f"""# TASK
You are an expert research assistant analyzing a single CAPM (Central Accounting Policy Manual) document section to answer a user query.
Your goal is to extract and summarize the most relevant information from this document section related to the query for later aggregation.

## User Query
{user_query}

## Document Section Content
<document_section>
{formatted_document}
</document_section>

## Instructions
1.  **Identify Key Context in Query:** First, identify any specific key accounting context mentioned in the User Query (e.g., 'asset', 'liability', 'equity', 'IFRS', 'US GAAP', specific standard numbers). This context is CRITICAL for filtering.
2.  **Analyze Relevance within Context:** Carefully read the user query and the provided CAPM document section content. Determine how well the section addresses the query **specifically within the identified key accounting context.**
3.  **Extract Key Information (Filtered):** Extract key facts and direct quotes relevant to the query **AND strictly pertaining to the identified key accounting context** using *only* information from the provided document section. Format this as a structured list (e.g., bullet points) optimized for later aggregation. **Actively ignore and filter out information related to other contexts not mentioned in the query.**
4.  **Cite Accurately:** **CRITICAL: Cite the specific document AND section name/number accurately *inline*, immediately following the information it supports. Example: `- The policy states Y is allowed for liabilities. (Source: CAPM Policy 456 - Expense Reporting, Section: 3.1 Allowable Expenses)` Use the most specific section identifier available (name or number).**
5.  **Output Requirements:** You MUST call the `summarize_individual_document` tool. Provide the context-filtered extracted information (as a markdown string with bullet points/quotes and inline citations) as the `document_summary` argument. Do not include any other text in your response. If the document section does not contain relevant information for the specified context, state that clearly (e.g., `- No relevant information found in this section regarding asset treatment under US GAAP.`).
"""
    return prompt


# Define the tool schema for individual document summarization
INDIVIDUAL_DOCUMENT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "summarize_individual_document",
        "description": "Summarizes findings from an individual document section related to the query.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_summary": {
                    "type": "string",
                    "description": "Concise summary of relevant information from the document section, formatted as markdown.",
                },
            },
            "required": ["document_summary"],
        },
    },
}
