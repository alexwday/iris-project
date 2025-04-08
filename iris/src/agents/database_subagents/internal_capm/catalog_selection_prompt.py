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
1. **Critically evaluate the Document Description** for each document. Select ONLY those documents whose descriptions indicate they are highly relevant and directly address the core aspects of the user query.
2. Prioritize documents with descriptions that promise specific, detailed information pertinent to the query over those with generic descriptions.
3. **Be highly selective.** It is better to return fewer, highly relevant documents than a larger number of tangentially related ones.
4. Only consider documents for background or context if their descriptions explicitly state they provide foundational information directly relevant to the query's specific topic.

# OUTPUT
You must respond with ONLY the IDs of the **most relevant and highest quality** documents based on their descriptions.
Return a maximum of **3** document IDs. Aim for fewer if only 1 or 2 documents are truly excellent matches.
Your response must be formatted as a JSON array of document IDs as strings, for example:
["1", "2"]

If no documents seem relevant, return an empty array: []
"""
    return prompt
