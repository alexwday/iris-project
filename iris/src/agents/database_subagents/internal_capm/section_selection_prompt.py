# internal_capm/section_selection_prompt.py
"""
Prompt templates for selecting relevant sections from CAPM documents.

This module contains prompts used to guide the LLM in selecting
the most relevant sections from CAPM documents based on section summaries.
"""


def get_section_selection_prompt(
    user_query: str, formatted_sections_and_summaries: str
) -> str:
    """
    Generate a prompt for selecting relevant sections from CAPM documents.

    Args:
        user_query (str): The original user query
        formatted_sections_and_summaries (str): The formatted sections and summaries of CAPM documents

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are helping to identify the most relevant sections from CAPM (Central Accounting Policy Manual) documents to answer a user query.
The CAPM documents are typically long and contain many sections, including scope, summary, definitions, table of contents, appendices, etc.
Your task is to select only the most relevant sections based on their summaries to reduce token usage while ensuring all necessary information is included.

## User Query
{user_query}

## Document Sections and Summaries
The following contains document names, section names, and section summaries (but not the full content):

{formatted_sections_and_summaries}

## Selection Criteria
1. **Critically evaluate the Section Summary** for each section. Select ONLY those sections whose summaries indicate they directly address the core aspects of the user query with relevant detail.
2. Prioritize sections with summaries that promise specific answers, analysis, or key definitions pertinent to the query over those with generic or vague summaries.
3. **Be highly selective.** Only choose sections whose summaries strongly suggest they are essential for answering the query. It is crucial to minimize token usage by avoiding sections that are only tangentially related.
4. Avoid selecting generic sections (e.g., table of contents, revision history, standard appendices) unless their summaries explicitly state they contain unique, critical information directly relevant to the *specific* user query.
5. If multiple sections seem relevant, prioritize those whose summaries indicate they contain the most substantive or core information related to the query.

# OUTPUT
You must respond with ONLY a JSON object containing the document names and their relevant section names.
Format your response as follows:
{{
  "document_name1": ["Section Name 1", "Section Name 2"],
  "document_name2": ["Section Name 1"]
}}

If no sections seem relevant, return an empty object: {{}}
"""
    return prompt
