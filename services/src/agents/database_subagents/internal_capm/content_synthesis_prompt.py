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
from ....global_prompts.fiscal_statement import get_fiscal_statement
from ....global_prompts.restrictions_statement import get_restrictions_statement

# Define the subagent role
SUBAGENT_ROLE = "an expert research assistant specializing in analyzing internal CAPM (Central Accounting Policy Manual) documents"

# CO-STAR Framework Components
SUBAGENT_OBJECTIVE = """
To analyze provided CAPM document pages against a user query and generate page-based research findings.
Your objective is to:
1. Determine the relevance of each page of the document to the user query.
2. Generate a concise status flag summarizing the overall document relevance.
3. Extract research findings from EACH RELEVANT PAGE individually, using ONLY information from that specific page.
4. Organize findings by page number to preserve page-level granularity for downstream citation.
5. Ensure the research is optimized for consumption by another AI agent (the Summarizer).
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
A mandatory tool call to `extract_page_based_research` containing:
1. `status_summary`: A single-line status flag indicating overall document relevance (e.g., "✅ Found relevant info on 3 pages.", "📄 No relevant info found.").
2. `page_research`: An array of objects, each containing:
   - `page_number`: The page number (integer)
   - `research_content`: The research findings extracted from that specific page (Markdown string)
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
        "You are analyzing sections from the internal CAPM (Central Accounting Policy Manual) database.",
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
        "Your goal is to extract research findings from EACH RELEVANT PAGE of the provided document, organizing findings by page number.",
        "<INPUT_DOCUMENTS>",
        f"<USER_QUERY>{user_query}</USER_QUERY>",
        f"<DOCUMENT_PAGES>{formatted_documents}</DOCUMENT_PAGES>",
        "</INPUT_DOCUMENTS>",
        "<INSTRUCTIONS>",
        "1. **Analyze Each Page:** Carefully read the user query and examine EACH page of the provided CAPM document. The document is formatted with clear page markers (e.g., '## Page X of filename.pdf' followed by '**PAGE X**').",
        "2. **Identify Relevant Pages:** Determine which pages contain information relevant to the user query. Skip pages with no relevant content.",
        "3. **Extract Page-Specific Research:** For EACH relevant page:",
        "   * Extract ONLY the information from that specific page that addresses the query",
        "   * Create a research summary for that page in Markdown format",
        "   * Do NOT combine information across pages - keep each page's findings separate",
        "   * Include key facts, figures, policies, or procedures found on that page",
        "   **Strict Adherence to Data Sourcing:** Your research MUST be derived *exclusively* from the text within each page. Do NOT introduce any external knowledge.",
        "4. **Apply Filters:**",
        "   * **CRITICAL STANDARD FILTERING:** Focus *only* on information relevant to the accounting standard specified in the query (defaulting to IFRS if none specified). Ignore other standards unless explicitly requested.",
        "   * **CRITICAL TYPE FILTERING:** If the query specifies a particular accounting type (e.g., 'financial assets'), focus *only* on that type.",
        "5. **Generate Status Summary:** Based on your analysis of ALL pages, provide a concise status summary:",
        "   * If relevant information found: `✅ Found relevant information on X page(s).`",
        "   * If no relevant information: `📄 No relevant information found in document.`",
        "   * Include the count of pages with relevant information",
        "6. **Format Output:** Create the page_research array with one entry per relevant page, containing:",
        "   * page_number: The integer page number",
        "   * research_content: The Markdown-formatted research extracted from that page only",
        "</INSTRUCTIONS>",
        "<OUTPUT_SPECIFICATION>",
        "You MUST call the `extract_page_based_research` tool.",
        "Provide the status summary and page_research array as arguments.",
        "The page_research array should contain one object per relevant page, with page_number and research_content.",
        "Do not include any other text, preamble, or explanation in your response outside the tool call.",
        "If no relevant pages were found, the status summary should reflect that, and the page_research array should be empty.",
        SUBAGENT_RESPONSE_FORMAT,  # Reinforce the expected output format
        "</OUTPUT_SPECIFICATION>",
        "</TASK>",
    ]

    return "\n\n".join(prompt_parts)


# Note: Internal CAPM doesn't need the individual file synthesis function anymore since we're using parallel processing