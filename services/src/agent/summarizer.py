"""
Summarizer Agent Module.

Generates the final research summary based on aggregated detailed research
findings from various databases. Part of the IRIS cascading retrieval
architecture.

Functions:
    generate_streaming_summary: Generate a streaming summary from research findings

Classes:
    SummarizerError: Exception for summarizer-related errors
"""

import logging
from typing import Any, Dict, Generator, Optional

from ..connections.llm import call_llm
from ..utils.env_config import config
from ..utils.prompt_loader import get_composed_prompt

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 16384
MODEL_TEMPERATURE = 0.0

logger = logging.getLogger(__name__)


class SummarizerError(Exception):
    """Exception raised for summarizer-related errors."""


def _get_model_settings() -> Dict[str, Any]:
    """
    Get model settings from config based on capability tier.

    Returns:
        Dictionary containing model name and token costs.
    """
    model_config = config.get_model_config(MODEL_CAPABILITY)
    return {
        "name": model_config["name"],
        "prompt_token_cost": model_config["prompt_token_cost"],
        "completion_token_cost": model_config["completion_token_cost"],
    }


def _format_research_context(
    aggregated_detailed_research: Dict[str, str],
    available_databases: Dict[str, Any],
) -> str:
    """
    Format the aggregated research findings into context string.

    Args:
        aggregated_detailed_research: Dictionary of research text keyed by database.
        available_databases: Database configurations for display name lookup.

    Returns:
        Formatted research context string.
    """
    research_context = "Aggregated Detailed Research Findings:\n\n"

    if not aggregated_detailed_research:
        research_context += (
            "No detailed research findings were provided or generated.\n"
        )
        return research_context

    for db_name, research_text in aggregated_detailed_research.items():
        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
        research_context += f"=== Findings from: {db_display_name} ===\n"
        research_context += f"{research_text}\n\n"

    return research_context.strip()


def _format_reference_context(reference_index: Dict[str, Dict[str, Any]]) -> str:
    """
    Format the reference index into context string.

    Args:
        reference_index: Mapping of reference IDs to document details.

    Returns:
        Formatted reference context string.
    """
    ref_context = "Available References:\n"

    for ref_id, ref_data in reference_index.items():
        doc_name = ref_data.get("doc_name", "Unknown")
        page = ref_data.get("page", 1)
        ref_context += f"[REF:{ref_id}] = {doc_name} - Page {page}\n"

    return ref_context.strip()


def _build_user_message(
    user_prompt_template: str,
    research_statement: Optional[str],
) -> str:
    """
    Build the user message content for the summary request.

    Args:
        user_prompt_template: Template from database with placeholders.
        research_statement: Optional research query for context.

    Returns:
        Formatted user message string.

    Raises:
        SummarizerError: If user_prompt_template is not provided from database.
    """
    if not user_prompt_template:
        raise SummarizerError(
            "user_prompt not found in database for agent/summarizer. "
            "Please ensure the prompt is configured in the prompts table."
        )

    user_content = user_prompt_template.replace(
        "{{research_statement}}", research_statement or "No specific research query"
    )

    return user_content


def _build_messages(
    system_prompt: str,
    user_prompt_template: str,
    aggregated_detailed_research: Dict[str, str],
    available_databases: Dict[str, Any],
    summary_context: Optional[Dict[str, Any]],
) -> list:
    """
    Build the complete messages list for the LLM call.

    Args:
        system_prompt: The system prompt content.
        user_prompt_template: Template from database with placeholders.
        aggregated_detailed_research: Dictionary of research text keyed by database.
        available_databases: Database configurations for display name lookup.
        summary_context: Optional dict with 'research_statement' and 'reference_index'.

    Returns:
        List of message dictionaries for the LLM.
    """
    messages = [{"role": "system", "content": system_prompt}]

    research_context = _format_research_context(
        aggregated_detailed_research, available_databases
    )
    messages.append({"role": "system", "content": research_context})

    if summary_context:
        reference_index = summary_context.get("reference_index")
        if reference_index:
            ref_context = _format_reference_context(reference_index)
            messages.append({"role": "system", "content": ref_context})

        research_statement = summary_context.get("research_statement")
    else:
        research_statement = None

    user_content = _build_user_message(user_prompt_template, research_statement)
    messages.append({"role": "user", "content": user_content})

    return messages


def generate_streaming_summary(
    aggregated_detailed_research: Dict[str, str],
    token: Optional[str],
    available_databases: Dict[str, Any],
    summary_context: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """
    Generate the final response based on aggregated detailed research.

    Streams content chunks to the caller, with usage details yielded as
    the final item.

    Args:
        aggregated_detailed_research: Dictionary keyed by database name,
            containing the detailed research string for each.
        token: Authentication token for API access (OAuth token in RBC,
            API key in local environment).
        available_databases: Available database configurations.
        summary_context: Optional dict containing:
            - research_statement: The research query for context
            - reference_index: Master reference index mapping ref IDs to details

    Yields:
        Content chunks (str) during streaming, then a final dict containing
        usage details: {'usage_details': {...}}.

    Raises:
        SummarizerError: If there is an error generating the summary.
    """
    final_usage_details = None

    try:
        model_settings = _get_model_settings()
        system_prompt, _, user_prompt_template = get_composed_prompt(
            "agent", "summarizer"
        )

        messages = _build_messages(
            system_prompt,
            user_prompt_template,
            aggregated_detailed_research,
            available_databases,
            summary_context,
        )

        llm_stream = call_llm(
            oauth_token=token,
            model=model_settings["name"],
            messages=messages,
            max_tokens=MODEL_MAX_TOKENS,
            temperature=MODEL_TEMPERATURE,
            stream=True,
            prompt_token_cost=model_settings["prompt_token_cost"],
            completion_token_cost=model_settings["completion_token_cost"],
        )

        for item in llm_stream:
            if isinstance(item, dict) and "usage_details" in item:
                final_usage_details = item
                break
            if (
                hasattr(item, "choices")
                and item.choices
                and item.choices[0].delta
                and item.choices[0].delta.content
            ):
                yield item.choices[0].delta.content

        if final_usage_details:
            yield final_usage_details
        else:
            logger.warning("Usage details not found in summary stream")
            yield {"usage_details": {"error": "Usage data missing from stream"}}

    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        logger.error("Error generating streaming summary: %s", str(exc), exc_info=True)
        yield f"\n\n**Error generating research summary:** {exc}\n"
        raise SummarizerError(f"Failed to generate streaming summary: {exc}") from exc
