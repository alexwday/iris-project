# internal_aio/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content AND status from retrieved AIO documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple AIO documents and providing a status summary.

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
SUBAGENT_ROLE = "an expert research assistant specializing in analyzing internal PAR (Project Approval Request Guidance) documents"

# CO-STAR Framework Components
SUBAGENT_OBJECTIVE = """
To analyze provided AIO document sections against a user query and generate an internal research report for the Summarizer agent.
Your objective is to:
1. Determine the relevance of the provided document content to the user query.
2. Generate a concise status flag summarizing the findings' relevance.
3. Synthesize a detailed, structured research report in Markdown format using ONLY information from the provided documents.
4. Include accurate citations on separate lines after each paragraph or key point using the format: ***Source: Document Name, Page X, Section Name*** in bold italic. 
   - **CRITICAL:** Look for actual section titles/headers in the document content (e.g., "Introduction", "Methodology", "Key Requirements", "Background", "Analysis") 
   - If the section header shows "Section X" but the content contains a descriptive title or heading, use that descriptive title
   - Extract section names from markdown headers (##, ###), bold text at the start of sections, or any clear section titles within the content
   - Only use the generic "Section X" format as a last resort when no descriptive name can be found in the content
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
2. `detailed_research`: A comprehensive Markdown string containing the synthesized findings with citations.
3. `page_numbers`: Array of page numbers referenced in the research.
4. `section_ids_by_page`: Object mapping page numbers to arrays of section IDs used from that page.
"""


def get_content_synthesis_prompt(user_query: str, formatted_documents: str) -> str:
    """
    Generate a prompt for synthesizing content AND status from retrieved AIO documents.

    Args:
        user_query (str): The original user query from the research statement
        formatted_documents (str): The formatted content of retrieved AIO document sections

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
        "1. **Analyze Relevance:** Carefully read the user query and the provided AIO document section content. Determine how well the content addresses the query.",
        "2. **Generate Status Summary Flag:** Based on your analysis, provide ONLY the single-line status summary flag indicating relevance and completeness. Choose ONE:",
        "   * `✅ Found information directly addressing the query.`",
        "   * `ℹ️ Found related contextual information, but not a direct answer.`",
        "   * `📄 Documents sections found, but they do not contain relevant information for this query.`",
        "   * `⚠️ Conflicting information found across document sections.` (Explain conflicts in the detailed report)",
        "   * `❓ Query is ambiguous based on document section content.` (Explain ambiguity in the detailed report)",
        "   **Strict Adherence to Data Sourcing:** Remember to strictly follow the `<CRITICAL_DATA_SOURCING>` rules defined in the global `<RESTRICTIONS_AND_GUIDELINES>`. Your report MUST be derived *exclusively* from the text within the `<DOCUMENT_SECTIONS>`. Do NOT introduce any facts, concepts, standard names/numbers, definitions, interpretations, or any external knowledge not explicitly present *within* the provided sections.",
        "3. **Generate Detailed Research Report:** Synthesize a comprehensive internal report using *only* information from the provided document sections.",
        "   * Structure the report clearly using Markdown (e.g., `## Key Findings`, `## Detailed Analysis`, `## Supporting Details`, `## Conflicts/Gaps`).",
        "   * **Extract Section Names:** For each section you reference, look within the section content for descriptive titles, headers, or topic names. Use these descriptive names in your citations instead of generic section numbers.",
        "     - Example: If you see '### [PAGE: 15, SECTION: 3] Section 3' but the content starts with '## Background and Methodology', use 'Background and Methodology' in your citation",
        "     - Example: If content has headers like '**Risk Assessment Procedures**' or '## Key Compliance Requirements', use those exact titles",
        '   * **CRITICAL PAGE/SECTION TRACKING: Each section in the document content is marked with [PAGE: X, SECTION: Y] headers. You MUST track which specific page numbers and section IDs you reference in your research. For every piece of information you use, note the PAGE and SECTION numbers from the headers. Then provide this tracking data in your tool call: `page_numbers` should list all unique page numbers you referenced, and `section_ids_by_page` should map each page number to the list of section IDs you used from that page. For example, if you reference [PAGE: 15, SECTION: 3] and [PAGE: 15, SECTION: 5], your tool call should include `page_numbers: [15]` and `section_ids_by_page: {"15": [3, 5]}`.**',
        "   * **CRITICAL STANDARD FILTERING:** Focus your synthesis *only* on information relevant to the accounting standard specified or implied in the <USER_QUERY> (Defaulting to IFRS if none is specified). Actively filter out and ignore information related to other standards (e.g., US GAAP) unless that standard was explicitly requested in the query.**",
        "   * **CRITICAL TYPE FILTERING:** Similarly, if the <USER_QUERY> specifies a particular accounting type (e.g., 'financial assets', 'liabilities'), focus your synthesis *only* on information directly relevant to that type. Actively filter out and ignore information related to other types unless the query explicitly asks for comparison or broader context.**",
        "   * If information is conflicting, present all sides clearly.",
        "   * If relevant information is missing from the provided sections, state that clearly.",
        "   * Optimize this report for the Summarizer Agent (another AI) to read and understand easily.",
        "   * Furthermore, pay special attention to any logical tests or criteria described in the content (e.g., conditions connected by 'and'/'or', multi-part tests, 'if...then' statements). Reproduce the full structure and wording of these tests accurately in your report, using formatting like bullet points or nested lists if needed for clarity.",
        "   * Adhere strictly to the <RESTRICTIONS_AND_GUIDELINES> provided in the <CONTEXT>.",
        "4. **Format Output:** Prepare the Status Summary Flag, Detailed Research Report, Page Numbers array, and Section IDs by Page object for the tool call.",
        "</INSTRUCTIONS>",
        "<OUTPUT_SPECIFICATION>",
        "You MUST call the `synthesize_research_findings` tool.",
        "Provide the generated status summary flag, detailed research report, page numbers array, and section IDs by page object as arguments.",
        "IMPORTANT: The `page_numbers` and `section_ids_by_page` fields are REQUIRED. Extract page/section numbers from the [PAGE: X, SECTION: Y] headers in the document content you actually reference.",
        "Do not include any other text, preamble, or explanation in your response outside the tool call.",
        "If no relevant document sections were provided or found, the status summary flag should reflect that (`📄`), and the detailed research report argument should state that no analysis is possible based on the provided sections.",
        SUBAGENT_RESPONSE_FORMAT,  # Reinforce the expected output format
        "</OUTPUT_SPECIFICATION>",
        "</TASK>",
    ]

    return "\n\n".join(prompt_parts)


# Note: Internal AIO doesn't seem to have an 'individual file synthesis' prompt.
