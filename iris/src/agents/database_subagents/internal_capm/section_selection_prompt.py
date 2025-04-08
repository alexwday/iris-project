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
1. **Identify Key Context in Query:** First, identify any specific key accounting context mentioned in the User Query (e.g., 'asset', 'liability', 'equity', 'IFRS', 'US GAAP', specific standard numbers).
2. **Prioritize Matching Summaries:** Critically evaluate the Section Summary for each section. Give **highest priority** to sections whose summaries explicitly mention or directly relate to the key accounting context identified in the query. For example, if the query is about 'asset impairment under IFRS', prioritize sections whose summaries mention 'asset impairment' or 'IFRS'.
3. **Assess Direct Relevance:** Select ONLY those sections whose summaries indicate they **directly and substantially** address the core aspects of the user query, particularly concerning the identified key accounting context.
4. **Be Extremely Selective:** Only choose sections whose summaries strongly suggest they are essential for answering the query *within the specified context*. It is crucial to minimize token usage by avoiding sections that are only tangentially related or discuss different accounting types/standards than requested. **Aim to select no more than 2-3 absolutely essential sections per document, and fewer if possible.**
5. Avoid selecting generic sections (e.g., table of contents, revision history, standard appendices) unless their summaries explicitly state they contain unique, critical information directly relevant to the *specific* user query and its key context.
6. If multiple sections seem relevant after applying the above criteria, prioritize those whose summaries indicate they contain the most substantive or core information related to the query's specific context.

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
