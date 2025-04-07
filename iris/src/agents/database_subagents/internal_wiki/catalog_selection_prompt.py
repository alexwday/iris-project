# internal_wiki/catalog_selection_prompt.py
"""
Prompt templates for selecting relevant wiki documents from the catalog.

This module contains prompts used to guide the LLM in selecting
the most relevant documents from the wiki catalog based on the user query.
"""


def get_catalog_selection_prompt(user_query: str, formatted_catalog: str) -> str:
    """
    Generate a prompt for selecting relevant documents from the wiki catalog.

    Args:
        user_query (str): The original user query
        formatted_catalog (str): The formatted catalog of wiki documents

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are helping to search through a catalog of internal wiki documents to find
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
1. Select documents that directly address aspects of the user query
2. Consider documents that provide background information or context relevant to the query
3. Prioritize documents that appear most specific to the user's question
4. Consider a breadth of documents if the query spans multiple topics
5. **Special Handling for General Listing Queries:** If the user query seems to be asking for a general list, overview, or all available documents (e.g., "list all wiki pages", "what documents are available?", "overview of wiki entries"), select the IDs of **ALL** documents provided in the "Available Documents" section below, up to a maximum of 15 IDs.

# OUTPUT
You must respond with ONLY the IDs of the most relevant documents based on the criteria above.
- For specific queries, return a maximum of 5 document IDs.
- For general listing queries (as described in criteria 5), return ALL available document IDs (up to a maximum of 15).

IMPORTANT: Your entire response must be ONLY a JSON array of document IDs as strings, with no explanation, preamble, or additional text. Examples:
["1", "2", "3"]
or
[]

For clarity, I need to be able to parse your entire output as valid JSON.
"""
    return prompt
