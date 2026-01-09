"""
Router Agent Module.

Handles routing decisions for user queries by analyzing conversation context
and determining the appropriate processing path (direct response or research).

Functions:
    get_routing_decision: Get routing decision from the model via tool call

Classes:
    RouterError: Exception for router-related errors
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from ..connections.llm import call_llm
from ..utils.env_config import config
from ..utils.input_sanitizer import format_conversation_for_prompt
from ..utils.prompt_loader import get_composed_prompt

MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.0

logger = logging.getLogger(__name__)


class RouterError(Exception):
    """Exception raised for router-related errors."""


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
        RouterError: If user_prompt_template is not provided from database.
    """
    if not user_prompt_template:
        raise RouterError(
            "user_prompt not found in database for agent/router. "
            "Please ensure the prompt is configured in the prompts table."
        )

    messages = [{"role": "system", "content": system_prompt}]

    conversation_context = format_conversation_for_prompt(conversation)
    user_content = user_prompt_template.replace(
        "{{conversation}}", conversation_context
    )

    messages.append({"role": "user", "content": user_content})
    return messages


def _extract_tool_response(response: Any) -> Dict[str, Any]:
    """
    Extract and validate tool call arguments from LLM response.

    Args:
        response: The LLM response object.

    Returns:
        Parsed arguments dictionary from the tool call.

    Raises:
        RouterError: If response is invalid or tool call parsing fails.
    """
    if not response or not hasattr(response, "choices") or not response.choices:
        raise RouterError("Invalid or empty response received from LLM")

    message = response.choices[0].message
    if not message or not message.tool_calls:
        content_returned = (
            message.content if message and message.content else "No content"
        )
        logger.warning(
            "Expected tool call but received content: %s...",
            content_returned[:100],
        )
        raise RouterError(
            "No tool call received in response, content returned instead."
        )

    tool_call = message.tool_calls[0]

    if tool_call.function.name != "route_query":
        raise RouterError(f"Unexpected function call: {tool_call.function.name}")

    try:
        return json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        raise RouterError(
            f"Invalid JSON in tool arguments: {tool_call.function.arguments}"
        ) from exc


def _validate_routing_decision(arguments: Dict[str, Any]) -> str:
    """
    Validate and extract function name from tool arguments.

    Args:
        arguments: Parsed tool call arguments.

    Returns:
        Validated function name string.

    Raises:
        RouterError: If function_name is missing.
    """
    function_name = arguments.get("function_name")
    if not function_name:
        raise RouterError("Missing 'function_name' in tool arguments")
    return function_name


def get_routing_decision(
    conversation: Dict[str, Any],
    token: str,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Get routing decision from the model using a tool call.

    Analyzes the conversation and determines whether to respond directly
    or proceed with database research.

    Args:
        conversation: Conversation dict with 'messages' key containing message list.
        token: Authentication token for API access (OAuth token in RBC,
            API key in local environment).
        available_databases: Dict of available database configurations
            filtered by user selection. Helps router understand what data is available.

    Returns:
        Tuple containing:
            - Routing decision dict with 'function_name' key
            - Usage details dict for the LLM call, or None if error

    Raises:
        RouterError: If there is an error getting the routing decision.
    """
    try:
        db_names = list(available_databases.keys()) if available_databases else None
        system_prompt, tools, user_prompt_template = get_composed_prompt(
            "agent", "router", filtered_database=True, db_names=db_names
        )
        model_settings = _get_model_settings()
        messages = _build_messages(system_prompt, user_prompt_template, conversation)

        response, usage_details = call_llm(
            oauth_token=token,
            model=model_settings["name"],
            messages=messages,
            max_tokens=MODEL_MAX_TOKENS,
            temperature=MODEL_TEMPERATURE,
            tools=tools,
            tool_choice={
                "type": "function",
                "function": {"name": "route_query"},
            },
            stream=False,
            prompt_token_cost=model_settings["prompt_token_cost"],
            completion_token_cost=model_settings["completion_token_cost"],
        )

        arguments = _extract_tool_response(response)
        function_name = _validate_routing_decision(arguments)

        logger.info("Routing decision: %s", function_name)

        return {"function_name": function_name}, usage_details

    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        logger.error("Error getting routing decision: %s", str(exc), exc_info=True)
        raise RouterError(f"Failed to get routing decision: {exc}") from exc
