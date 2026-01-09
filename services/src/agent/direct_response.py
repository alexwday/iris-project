"""
Direct Response Agent Module.

Handles direct response generation based solely on conversation context
without requiring additional database research. Used when the router
determines no research is needed.

Functions:
    response_from_conversation: Generate a direct response based on conversation

Classes:
    DirectResponseError: Exception for direct response errors
"""

import logging
from typing import Any, Dict, Generator, Optional

from ..connections.llm import call_llm
from ..utils.env_config import config
from ..utils.input_sanitizer import format_conversation_for_prompt
from ..utils.prompt_loader import get_composed_prompt

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 16384
MODEL_TEMPERATURE = 0.0

logger = logging.getLogger(__name__)


class DirectResponseError(Exception):
    """Exception raised for direct response generation errors."""


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


def _build_messages(
    system_prompt: str,
    user_prompt_template: str,
    conversation: Dict[str, Any],
) -> list:
    """
    Build the messages list for the LLM call.

    Args:
        system_prompt: The system prompt content.
        user_prompt_template: Template for user message with {{conversation}} placeholder.
        conversation: Conversation dict with 'messages' key.

    Returns:
        List of message dictionaries for the LLM.

    Raises:
        DirectResponseError: If user_prompt_template is not provided from database.
    """
    if not user_prompt_template:
        raise DirectResponseError(
            "user_prompt not found in database for agent/direct_response. "
            "Please ensure the prompt is configured in the prompts table."
        )

    messages = [{"role": "system", "content": system_prompt}]

    conversation_context = format_conversation_for_prompt(conversation)
    user_content = user_prompt_template.replace(
        "{{conversation}}", conversation_context
    )

    messages.append({"role": "user", "content": user_content})
    return messages


def response_from_conversation(
    conversation: Dict[str, Any],
    token: str,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """
    Generate a direct response based solely on conversation context.

    Streams content chunks to the caller, with usage details yielded as
    the final item.

    Args:
        conversation: Conversation dict with 'messages' key containing message list.
        token: Authentication token for API access (OAuth token in RBC,
            API key in local environment).
        available_databases: Dict of available database configurations
            filtered by user selection. Provides context about available data sources.

    Yields:
        Content chunks (str) during streaming, then a final dict containing
        usage details: {'usage_details': {...}}.

    Raises:
        DirectResponseError: If there is an error generating the response.
    """
    final_usage_details = None
    try:
        db_names = list(available_databases.keys()) if available_databases else None
        system_prompt, _, user_prompt_template = get_composed_prompt(
            "agent", "direct_response", filtered_database=True, db_names=db_names
        )
        model_settings = _get_model_settings()
        messages = _build_messages(system_prompt, user_prompt_template, conversation)

        response_stream = call_llm(
            oauth_token=token,
            model=model_settings["name"],
            messages=messages,
            max_tokens=MODEL_MAX_TOKENS,
            temperature=MODEL_TEMPERATURE,
            stream=True,
            prompt_token_cost=model_settings["prompt_token_cost"],
            completion_token_cost=model_settings["completion_token_cost"],
        )

        for item in response_stream:
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
            logger.warning("Usage details not found in direct response stream")
            yield {"usage_details": {"error": "Usage data missing from stream"}}

    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
        logger.error("Error generating direct response: %s", str(exc), exc_info=True)
        raise DirectResponseError(f"Failed to generate direct response: {exc}") from exc
