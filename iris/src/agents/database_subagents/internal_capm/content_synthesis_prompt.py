# internal_capm/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content AND status from retrieved CAPM documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple CAPM documents and providing a status summary.
"""


def get_content_synthesis_prompt(user_query: str, formatted_documents: str) -> str:
    """
    Generate a prompt for synthesizing content AND status from retrieved CAPM documents.

    Args:
        user_query (str): The original user query
        formatted_documents (str): The formatted content of retrieved CAPM documents

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are an expert research assistant analyzing internal CAPM (Central Accounting Policy Manual) documents to answer a user query.
Your goal is to provide BOTH a concise status summary of the findings AND a detailed, structured research report based *only* on the provided documents.

## User Query
{user_query}

## Document Content
<documents>
{formatted_documents}
</documents>

## Instructions
1.  **Analyze Relevance:** Carefully read the user query and the provided CAPM document content. Determine how well the documents address the query.
2.  **Generate Status Summary:** Based on your analysis, provide a concise status summary (1 sentence) indicating the relevance and completeness of the findings. Use one of the following formats:
    *   `✅ Found information directly addressing the query.`
    *   `ℹ️ Found related contextual information, but not a direct answer.`
    *   `📄 Documents found, but they do not contain relevant information for this query.`
    *   `⚠️ Conflicting information found across documents.` (Use this if applicable, then explain in detail below)
    *   `❓ Query is ambiguous based on document content.` (Use if documents make query interpretation unclear)
3.  **Generate Detailed Research Report:** Synthesize a comprehensive report using *only* information from the provided CAPM documents. Structure the report clearly using markdown with appropriate headings (e.g., `## Answer Summary`, `## Detailed Analysis`, `## Missing Information / Conflicts`, `## References`). **Cite specific documents AND section names accurately (e.g., "Source: [Document Name], Section: [Section Name]").** If information is conflicting, present all sides. If information is missing, state that clearly. Optimize this report for another AI agent to read and understand easily.
4.  **Output Requirements:** You MUST call the `synthesize_research_findings` tool. Provide the generated status summary and the full detailed research report (as a markdown string) as arguments to the tool. Do not include any other text in your response. If no relevant documents were provided or found, the status summary should reflect that, and the detailed research argument should state that no analysis is possible.
"""
    return prompt


def get_individual_file_synthesis_prompt(user_query: str, formatted_document: str) -> str:
    """
    Generate a prompt for synthesizing content from a single CAPM document.
    Used when total content exceeds token limits and each file needs individual processing.

    Args:
        user_query (str): The original user query
        formatted_document (str): The formatted content of a single CAPM document

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are an expert research assistant analyzing a single CAPM (Central Accounting Policy Manual) document to answer a user query.
Your goal is to extract and summarize the most relevant information from this document related to the query.

## User Query
{user_query}

## Document Content
<document>
{formatted_document}
</document>

## Instructions
1.  **Analyze Relevance:** Carefully read the user query and the provided CAPM document content. Determine how well the document addresses the query.
2.  **Generate Research Summary:** Create a concise but comprehensive summary of the relevant information from this document. Structure the summary clearly using markdown with appropriate headings. **Cite specific section names accurately (e.g., "Section: [Section Name]").** Focus only on information directly relevant to the query.
3.  **Output Requirements:** You MUST call the `summarize_individual_document` tool. Provide the document summary as a markdown string argument to the tool. Do not include any other text in your response. If the document does not contain relevant information, state that clearly in your summary.
"""
    return prompt


# Define the tool schema for individual document summarization
INDIVIDUAL_DOCUMENT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "summarize_individual_document",
        "description": "Summarizes findings from an individual document related to the query.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_summary": {
                    "type": "string",
                    "description": "Concise summary of relevant information from the document, formatted as markdown.",
                },
            },
            "required": ["document_summary"],
        },
    },
}
