# internal_wiki/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content from retrieved wiki documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple wiki documents to form a comprehensive response.
"""


def get_content_synthesis_prompt(user_query: str, formatted_documents: str) -> str:
    """
    Generate a prompt for synthesizing content from retrieved wiki documents.
    
    Args:
        user_query (str): The original user query
        formatted_documents (str): The formatted content of retrieved wiki documents
        
    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are helping to synthesize information from multiple internal wiki documents
to provide a comprehensive answer to a user query.

## User Query
{user_query}

## Document Content
{formatted_documents}

## Synthesis Guidelines
1. Directly address the user's query using the provided document content
2. Cite specific documents and sections when presenting information
3. Organize your response logically with clear headings and structure
4. Present information in order of relevance to the query
5. If documents contain conflicting information, acknowledge this and explain the
   different perspectives
6. If the documents do not fully address the query, clearly state what information
   is missing

# OUTPUT FORMAT
Your response should be formatted as follows:

## Answer Summary
[Brief 2-3 sentence summary of key findings]

## Detailed Analysis
[Main content organized by topic or document, with specific citations to documents
and sections]

## References
[List the document names you referenced, in order of relevance]

If the documents do not contain relevant information, explain why and what
information would be needed to answer the query.
"""
    return prompt
