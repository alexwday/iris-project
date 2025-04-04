# python/iris/src/agents/agent_summarizer/summarizer.py
"""
Summarizer Agent Module

This module is responsible for generating the final research summary based on
the completed database queries and the original research statement.

Functions:
    generate_streaming_summary: Generates a streaming summary of research results.

Dependencies:
    - logging
    - OpenAI connector for LLM calls
"""

import logging

from ...chat_model.model_settings import get_model_config
from ...llm_connectors.rbc_openai import call_llm, log_usage_statistics
from .summarizer_settings import (
    AVAILABLE_DATABASES,
    MAX_TOKENS,
    MODEL_CAPABILITY,
    SYSTEM_PROMPT,
    TEMPERATURE,
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Get model configuration based on capability
model_config = get_model_config(MODEL_CAPABILITY)
MODEL_NAME = model_config["name"]
PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
COMPLETION_TOKEN_COST = model_config["completion_token_cost"]


class SummarizerError(Exception):
    """Base exception class for summarizer-related errors."""

    pass


def generate_streaming_summary(research_statement, completed_queries, token):
    """
    Generate a streaming research summary based on completed queries.

    This function produces a streaming response that can be yielded directly
    to the user.

    Args:
        research_statement (str): The original research statement
        completed_queries (list): List of completed queries with their results
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key

    Returns:
        generator: A generator that yields response chunks as strings

    Raises:
        SummarizerError: If there is an error generating the summary
    """
    try:
        # Prepare system message with summary prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare messages for the API call
        messages = [system_message]

        # Add research statement
        research_message = {
            "role": "system",
            "content": f"Research Statement: {research_statement}",
        }
        messages.append(research_message)

        # Add completed queries
        completed_content = "Completed Queries and Results:\n"
        for i, query in enumerate(completed_queries):
            # Include query number for referencing in the summary
            completed_content += f"\n=== QUERY {i+1} ===\n"
            completed_content += f"Database: {query.get('database', 'Unknown')}\n"
            completed_content += f"Query: {query.get('query', 'Unknown')}\n"
            # Ensure results are strings, handle potential generators/errors stored earlier
            results_text = query.get("results", "No results")
            if not isinstance(results_text, str):
                results_text = str(results_text)  # Convert non-strings
            completed_content += f"Results: {results_text}\n"

        completed_message = {"role": "system", "content": completed_content}
        messages.append(completed_message)

        # Database information is included in the SYSTEM_PROMPT via get_full_system_prompt

        # User message requesting summary
        user_message = {
            "role": "user",
            "content": "Please generate the comprehensive research summary based on the provided context and requirements.",
        }
        messages.append(user_message)

        logger.info(f"Generating streaming research summary using model: {MODEL_NAME}")
        logger.info(f"Summarizing {len(completed_queries)} completed queries")

        # Make the API call with streaming enabled
        stream = call_llm(
            oauth_token=token,
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True,
            prompt_token_cost=PROMPT_TOKEN_COST,
            completion_token_cost=COMPLETION_TOKEN_COST,
        )

        # Return the streaming generator
        for chunk in stream:
            # If chunk has usage data, capture it in logs but don't display it
            if hasattr(chunk, "usage") and chunk.usage:
                log_usage_statistics(chunk, PROMPT_TOKEN_COST, COMPLETION_TOKEN_COST)

            # Yield content from the chunk
            if (
                hasattr(chunk, "choices")
                and chunk.choices
                and chunk.choices[0].delta.content
            ):
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"Error generating streaming summary: {str(e)}")
        # Yield an error message within the generator stream
        yield f"\n\n**Error generating research summary:** {str(e)}\n"
        # Raise an exception as well to signal failure if needed by the caller
        raise SummarizerError(f"Failed to generate streaming summary: {str(e)}")
