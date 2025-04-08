# python/iris/src/agents/agent_summarizer/summarizer.py
"""
Summarizer Agent Module (Async Version)

This module is responsible for generating the final research summary based on
the aggregated detailed research findings from various databases.

Functions:
    generate_streaming_summary: Asynchronously generates a streaming summary.

Dependencies:
    - logging
    - OpenAI connector for LLM calls
    - Typing for annotations
"""

import logging
import json
from typing import Any, Dict, List, Optional, Union, Generator

from ...chat_model.model_settings import get_model_config

from ...llm_connectors.rbc_openai import call_llm, log_usage_statistics
from .summarizer_settings import (
    AVAILABLE_DATABASES,
    MAX_TOKENS,
    MODEL_CAPABILITY,
    SYSTEM_PROMPT,
    TEMPERATURE,
)

# Get module logger
logger = logging.getLogger(__name__)


class SummarizerError(Exception):
    """Base exception class for summarizer-related errors."""

    pass


# --- Main Synchronous Summarizer Function ---
def generate_streaming_summary(
    aggregated_detailed_research: Dict[
        str, str
    ],  # Input is now Dict[db_name, detailed_research_string]
    scope: str,  # Keep scope for potential future variations
    token: Optional[str],
    original_query_plan: Optional[Dict] = None,  # Keep for context if needed
) -> Generator[str, None, None]:
    """
    Generate the final response based on aggregated detailed research (synchronous version).

    Currently focuses on 'research' scope, generating a streaming summary using an LLM.
    The 'metadata' scope handling is simplified as metadata is now handled
    differently in the main model flow.

    Args:
        aggregated_detailed_research (dict): Dictionary keyed by database name (str),
                                             containing the detailed research string for each.
        scope (str): The scope of the original request ('research' primarily).
        token (str): Authentication token for API access.
        original_query_plan (dict, optional): The original query plan (might be useful for context).

    Returns:
        Generator[str, None, None]: A generator yielding response chunks from the LLM stream.

    Raises:
        SummarizerError: If there is an error generating the response.
    """
    logger.info(f"Generating final summary for scope: {scope}")

    # --- Research Scope ---
    if scope == "research":
        try:
            # Get model configuration dynamically
            model_config = get_model_config(MODEL_CAPABILITY)
            model_name = model_config["name"]
            prompt_token_cost = model_config["prompt_token_cost"]
            completion_token_cost = model_config["completion_token_cost"]
        except Exception as config_err:
            logger.error(
                f"Failed to get model configuration: {config_err}", exc_info=True
            )
            yield f"\n\n**Internal Error:** Failed to load summarizer configuration.\n"
            raise SummarizerError(f"Configuration error: {config_err}")

        try:
            # Prepare system message with summary prompt
            system_message = {"role": "system", "content": SYSTEM_PROMPT}

            # Prepare messages for the API call
            messages = [system_message]

            # Format the aggregated detailed research for the prompt
            research_context = "Aggregated Detailed Research Findings:\n\n"
            if not aggregated_detailed_research:
                research_context += (
                    "No detailed research findings were provided or generated.\n"
                )
            else:
                for db_name, research_text in aggregated_detailed_research.items():
                    db_display_name = AVAILABLE_DATABASES.get(db_name, {}).get(
                        "name", db_name
                    )
                    research_context += f"=== Findings from: {db_display_name} ===\n"
                    research_context += f"{research_text}\n\n"

            context_message = {"role": "system", "content": research_context.strip()}
            messages.append(context_message)

            # Add original query plan details if available
            if original_query_plan and original_query_plan.get("queries"):
                plan_context = "Original Query Plan:\n"
                for i, q in enumerate(original_query_plan["queries"]):
                    db_identifier = q.get("database")
                    db_display_name = AVAILABLE_DATABASES.get(db_identifier, {}).get(
                        "name", db_identifier
                    )
                    plan_context += f"{i+1}. {db_display_name}: {q.get('query')}\n"
                messages.append({"role": "system", "content": plan_context.strip()})

            # User message requesting summary
            user_message = {
                "role": "user",
                "content": "Please generate the comprehensive research summary based on the provided context and requirements. Synthesize the findings from all sources into a single, coherent response.",
            }
            messages.append(user_message)

            logger.info(
                f"Generating streaming research summary using model: {model_name}"
            )
            logger.info(
                f"Summarizing detailed research from {len(aggregated_detailed_research)} databases."
            )
            logger.info("Initiating Summarizer stream API call")  # Added contextual log

            # --- Synchronous LLM Call ---
            # Directly call the synchronous call_llm function
            llm_stream = call_llm(
                oauth_token=token,
                model=model_name,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True,  # Keep streaming enabled
                prompt_token_cost=prompt_token_cost,
                completion_token_cost=completion_token_cost,
                # No database_name needed here
            )

            # Yield chunks from the synchronous LLM stream
            for chunk in llm_stream:
                # Usage logging is handled by call_llm when stream_options include_usage=True
                # (which it does by default in rbc_openai.py for streaming)

                # Yield content
                if (
                    hasattr(chunk, "choices")
                    and chunk.choices
                    and hasattr(chunk.choices[0], "delta")
                    and hasattr(chunk.choices[0].delta, "content")
                    and chunk.choices[0].delta.content is not None
                ):
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(
                f"Error generating streaming research summary: {str(e)}", exc_info=True
            )
            yield f"\n\n**Error generating research summary:** {str(e)}\n"
            raise SummarizerError(f"Failed to generate streaming summary: {str(e)}")

    # --- Metadata Scope (Simplified) ---
    elif scope == "metadata":
        logger.warning(
            "Summarizer called with 'metadata' scope, which is not actively handled here anymore."
        )
        yield "Metadata processing complete (no summary generated by this agent)."

    # --- Invalid Scope ---
    else:
        error_msg = f"Invalid scope '{scope}' provided to summarizer."
        logger.error(error_msg)
        yield f"\n\n**Internal Error:** {error_msg}\n"
        raise SummarizerError(error_msg)
