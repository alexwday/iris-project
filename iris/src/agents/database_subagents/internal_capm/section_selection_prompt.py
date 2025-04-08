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
1. Select sections that directly address aspects of the user query
2. Consider sections that provide necessary background information or context
3. Prioritize sections that appear most specific to the user's question
4. Avoid selecting generic sections like table of contents, appendices, etc. unless they contain unique information
5. Be selective - only choose sections that are truly relevant to minimize token usage

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
