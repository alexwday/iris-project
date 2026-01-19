"""Generate responses directly from conversation context."""

import logging
from typing import Any, Dict, Generator, Optional

from ..connections.llm import execute_llm_call
from ..utils.env_config import config
from ..utils.input_sanitizer import format_conversation_history_for_prompt
from ..utils.prompt_loader import get_prompt

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 16384
MODEL_TEMPERATURE = 0.0

logger = logging.getLogger(__name__)


class DirectResponseError(Exception):
    """Exception raised for direct response generation errors."""


def _get_model_settings() -> Dict[str, Any]:
    """Return model settings based on the configured capability tier.

    Returns:
        Dict[str, Any]: Model name and token costs.
    """
    model_config = config.get_model_settings(MODEL_CAPABILITY)
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
    """Build messages payload for the LLM call.

    Args:
        system_prompt (str): System prompt content.
        user_prompt_template (str): User prompt template containing a
            ``{{conversation}}`` placeholder.
        conversation (Dict[str, Any]): Conversation payload with a ``messages`` key.

    Returns:
        list: Message dictionaries ready for the LLM call.

    Raises:
        DirectResponseError: If no user prompt template is provided.
    """
    if not user_prompt_template:
        raise DirectResponseError(
            "user_prompt not found in database for agent/direct_response. "
            "Please ensure the prompt is configured in the prompts table."
        )

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": user_prompt_template.replace(
                "{{conversation}}",
                format_conversation_history_for_prompt(conversation),
            ),
        },
    ]


def stream_direct_response_from_conversation(
    conversation: Dict[str, Any],
    token: str,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """Stream a direct response based solely on the conversation context.

    Args:
        conversation (Dict[str, Any]): Conversation payload with a ``messages`` list.
        token (str): Authentication token for the LLM request.
        available_databases (Optional[Dict[str, Any]]): User-selected database
            configurations that shape the prompt context.

    Yields:
        str: Content chunks during streaming.
        Dict[str, Any]: Final dictionary containing usage details under the
            ``usage_details`` key.

    Raises:
        DirectResponseError: If response generation fails.
    """
    final_usage_details = None
    try:
        system_prompt, _, user_prompt_template = get_prompt(
            "agent",
            "direct_response",
            inject_fiscal=True,
            inject_database=True,
            available_databases=available_databases,
        )
        model_settings = _get_model_settings()
        messages = _build_messages(system_prompt, user_prompt_template, conversation)

        response_stream = execute_llm_call(
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

        if not final_usage_details:
            logger.warning("Usage details not found in direct response stream")
            final_usage_details = {
                "usage_details": {"error": "Usage data missing from stream"}
            }
        yield final_usage_details

    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
        logger.error("Error generating direct response: %s", str(exc), exc_info=True)
        raise DirectResponseError(f"Failed to generate direct response: {exc}") from exc
