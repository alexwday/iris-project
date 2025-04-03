# internal_icfr/catalog_selection_prompt.py
"""
Prompt templates for selecting relevant ICFR documents from the catalog.

This module contains prompts used to guide the LLM in selecting
the most relevant documents from the ICFR catalog based on the user query.
"""


def get_catalog_selection_prompt(user_query: str, formatted_catalog: str) -> str:
    """
    Generate a prompt for selecting relevant documents from the ICFR catalog.
    
    Args:
        user_query (str): The original user query
        formatted_catalog (str): The formatted catalog of ICFR documents
        
    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are helping to search through a catalog of internal ICFR (Internal Control over Financial Reporting) documents to find
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

# OUTPUT
You must respond with ONLY the IDs of the most relevant documents. 
Return a maximum of 5 document IDs.
Your response must be formatted as a JSON array of document IDs as strings, for example:
["1", "2", "3"]

If no documents seem relevant, return an empty array: []
"""
    return prompt
