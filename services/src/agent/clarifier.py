"""
Clarifier Agent Module.

Handles context assessment to determine if research can proceed or if essential
context is missing and must be requested from the user.

Part of IRIS Enhancement: Revised Retrieval Architecture.
The clarifier determines:
1. Whether to ask clarifying questions or proceed with research
2. Whether the query is DB-wide (requires checking ALL files) or selective
3. For DB-wide queries, whether to request user approval for extended research

Functions:
    clarify_research_needs: Determines if essential context is needed,
                            detects DB-wide queries, and manages approval flow

Classes:
    ClarifierError: Exception for clarifier-related errors
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


class ClarifierError(Exception):
    """Exception raised for clarifier-related errors."""


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
        ClarifierError: If user_prompt_template is not provided from database.
    """
    if not user_prompt_template:
        raise ClarifierError(
            "user_prompt not found in database for agent/clarifier. "
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
        ClarifierError: If response is invalid or tool call parsing fails.
    """
    if not response or not hasattr(response, "choices") or not response.choices:
        raise ClarifierError("Invalid or empty response received from LLM")

    message = response.choices[0].message
    if not message or not message.tool_calls:
        content_returned = (
            message.content if message and message.content else "No content"
        )
        logger.warning(
            "Expected tool call but received content: %s...",
            content_returned[:100],
        )
        raise ClarifierError(
            "No tool call received in response, content returned instead."
        )

    tool_call = message.tool_calls[0]

    if tool_call.function.name != "make_clarifier_decision":
        raise ClarifierError(f"Unexpected function call: {tool_call.function.name}")

    try:
        return json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        raise ClarifierError(
            f"Invalid JSON in tool arguments: {tool_call.function.arguments}"
        ) from exc


def _validate_decision_fields(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and extract decision fields from tool arguments.

    Args:
        arguments: Parsed tool call arguments.

    Returns:
        Validated decision dictionary with:
        - action: The clarifier decision action
        - output: Questions, approval request, or research statement
        - is_db_wide: Whether query requires checking ALL files in a database
        - deep_research_approved: Whether user approved extended research

    Raises:
        ClarifierError: If required fields are missing.
    """
    action = arguments.get("action")
    output = arguments.get("output")

    if not action:
        raise ClarifierError("Missing 'action' in tool arguments")

    if not output:
        raise ClarifierError("Missing 'output' in tool arguments")

    # Validate action is one of the expected values
    valid_actions = {
        "request_essential_context",
        "request_deep_research_approval",
        "create_research_statement",
    }
    if action not in valid_actions:
        logger.warning("Unexpected action '%s', defaulting to create_research_statement", action)
        action = "create_research_statement"

    # Extract optional boolean fields with defaults
    is_db_wide = arguments.get("is_db_wide", False)
    deep_research_approved = arguments.get("deep_research_approved", False)

    # Ensure boolean types
    if not isinstance(is_db_wide, bool):
        is_db_wide = bool(is_db_wide) if is_db_wide else False
    if not isinstance(deep_research_approved, bool):
        deep_research_approved = bool(deep_research_approved) if deep_research_approved else False

    return {
        "action": action,
        "output": output,
        "is_db_wide": is_db_wide,
        "deep_research_approved": deep_research_approved,
    }


def clarify_research_needs(
    conversation: Dict[str, Any],
    token: str,
    available_databases: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Determine if essential context is needed or create a research statement.

    Uses LLM tool calling to make a structured decision about whether to
    ask clarifying questions, request approval for extended research, or
    proceed with creating a research statement.

    The clarifier also detects DB-wide queries (queries that require checking
    ALL files in a database) and manages the approval flow for extended research.

    Args:
        conversation: Conversation dict with 'messages' key containing message list.
        token: Authentication token for API access (OAuth token in RBC,
            API key in local environment).
        available_databases: Dict of available database configurations
            filtered by user selection. Used to show only accessible databases.

    Returns:
        Tuple containing:
            - Clarifier decision dict with:
                - action: 'request_essential_context', 'request_deep_research_approval',
                          or 'create_research_statement'
                - output: Questions, approval request message, or research statement
                - is_db_wide: True if query requires checking ALL files in a database
                - deep_research_approved: True if user approved extended research
            - Usage details dict for the LLM call, or None if error

    Raises:
        ClarifierError: If there is an error in the clarification process.
    """
    try:
        db_names = list(available_databases.keys()) if available_databases else None
        system_prompt, tools, user_prompt_template = get_composed_prompt(
            "agent", "clarifier", filtered_database=True, db_names=db_names
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
                "function": {"name": "make_clarifier_decision"},
            },
            stream=False,
            prompt_token_cost=model_settings["prompt_token_cost"],
            completion_token_cost=model_settings["completion_token_cost"],
        )

        arguments = _extract_tool_response(response)
        decision = _validate_decision_fields(arguments)

        logger.info(
            "Clarifier decision: action=%s, is_db_wide=%s, deep_research_approved=%s",
            decision["action"],
            decision["is_db_wide"],
            decision["deep_research_approved"],
        )

        return decision, usage_details

    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        logger.error("Error clarifying research needs: %s", str(exc), exc_info=True)
        raise ClarifierError(f"Failed to clarify research needs: {exc}") from exc
