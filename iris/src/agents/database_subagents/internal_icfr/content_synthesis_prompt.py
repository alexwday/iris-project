# internal_icfr/content_synthesis_prompt.py
"""
Prompt templates for synthesizing content AND status from retrieved ICFR documents.

This module contains prompts used to guide the LLM in synthesizing
content from multiple ICFR documents and providing a status summary.
"""


def get_content_synthesis_prompt(user_query: str, formatted_documents: str) -> str:
    """
    Generate a prompt for synthesizing content AND status from retrieved ICFR documents.

    Args:
        user_query (str): The original user query
        formatted_documents (str): The formatted content of retrieved ICFR documents

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are an expert research assistant analyzing internal ICFR (Internal Control over Financial Reporting) documents to answer a user query.
Your goal is to provide BOTH a concise status summary of the findings AND a detailed, structured research report based *only* on the provided documents.

## User Query
{user_query}

## Document Content
<documents>
{formatted_documents}
</documents>

## Instructions
1.  **Analyze Relevance:** Carefully read the user query and the provided ICFR document content. Determine how well the documents address the query.
2.  **Generate Status Summary:** Based on your analysis, provide a concise status summary (1 sentence) indicating the relevance and completeness of the findings. Use one of the following formats:
    *   `✅ Found information directly addressing the query.`
    *   `ℹ️ Found related contextual information, but not a direct answer.`
    *   `📄 Documents found, but they do not contain relevant information for this query.`
    *   `⚠️ Conflicting information found across documents.` (Use this if applicable, then explain in detail below)
    *   `❓ Query is ambiguous based on document content.` (Use if documents make query interpretation unclear)
3.  **Generate Detailed Research Report:** Synthesize a comprehensive report using *only* information from the provided ICFR documents. Structure the report clearly using markdown with appropriate headings (e.g., `## Answer Summary`, `## Detailed Analysis`, `## Missing Information / Conflicts`, `## References`). **Cite specific documents AND section names accurately (e.g., "Source: [Document Name], Section: [Section Name]").** If information is conflicting, present all sides. If information is missing, state that clearly. Optimize this report for another AI agent to read and understand easily.
4.  **Output Requirements:** You MUST call the `synthesize_research_findings` tool. Provide the generated status summary and the full detailed research report (as a markdown string) as arguments to the tool. Do not include any other text in your response. If no relevant documents were provided or found, the status summary should reflect that, and the detailed research argument should state that no analysis is possible.
"""
    return prompt
