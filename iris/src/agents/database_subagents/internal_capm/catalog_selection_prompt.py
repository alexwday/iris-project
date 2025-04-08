# internal_capm/catalog_selection_prompt.py
"""
Prompt templates for selecting relevant CAPM documents from the catalog.

This module contains prompts used to guide the LLM in selecting
the most relevant documents from the CAPM catalog based on the user query.
"""


def get_catalog_selection_prompt(user_query: str, formatted_catalog: str) -> str:
    """
    Generate a prompt for selecting relevant documents from the CAPM catalog.

    Args:
        user_query (str): The original user query
        formatted_catalog (str): The formatted catalog of CAPM documents

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are helping to search through a catalog of internal CAPM (Central Accounting Policy Manual) documents to find
the most relevant ones for answering a user query.

## User Query
{user_query}

## Catalog Format
Each catalog entry contains:
- Document ID: A unique identifier for the document
- Document Name: The title of the document
- Document Description: A summary of what the document contains

## Available Documents
{formatted_catalog}

## Selection Criteria
1. **Evaluate the Document Description** for each document. Select documents whose descriptions suggest they are likely relevant to the user query. The next step will refine the selection based on section summaries, so you can be slightly more inclusive here if a document seems potentially relevant.
2. Prioritize documents with descriptions that promise specific, detailed information pertinent to the query over those with generic descriptions.
3. Consider documents that might provide useful context if their descriptions indicate relevance to the query's topic.
4. Aim for a balance between relevance and potential usefulness for the subsequent section review step.

# OUTPUT
You must respond with ONLY the IDs of the potentially relevant documents based on their descriptions.
Return a maximum of **5** document IDs.
Your response must be formatted as a JSON array of document IDs as strings, for example:
["1", "2", "5"]

If no documents seem relevant, return an empty array: []
"""
    return prompt
