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
1. **Identify Key Context in Query:** First, identify any specific key accounting context mentioned in the User Query (e.g., 'asset', 'liability', 'equity', 'IFRS', 'US GAAP', specific standard numbers). This context is your primary filter.
2. **Prioritize Matching Summaries:** Critically evaluate the Section Summary for each section. Give **highest priority** to sections whose summaries explicitly mention or directly relate to the key accounting context identified in the query. For example, if the query is about 'asset impairment under IFRS', prioritize sections whose summaries mention 'asset impairment' or 'IFRS'.
3. **Assess Relevance to Context:** Select sections whose summaries indicate they are **highly relevant** to the core aspects of the user query, **specifically concerning the identified key accounting context.** The summary should strongly suggest the section contains pertinent details for that context.
4. **Be Selective, Not Overly Restrictive:** While avoiding irrelevant sections is important for token efficiency, ensure you select sections whose summaries show a strong likelihood of containing useful information for the specific context. If a summary clearly addresses the key context and topic, select it. Avoid sections discussing different accounting types/standards than requested or those only tangentially related.
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
