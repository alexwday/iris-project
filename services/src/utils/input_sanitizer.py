"""
Input Sanitizer Module.

Handles processing and filtering of conversation histories for use with
language models. Standardizes different conversation formats, filters by
role, and manages history length.

Functions:
    sanitize_conversation_history: Filter and format conversation data
    format_conversation_history_for_prompt: Format conversation dict to string for LLM prompts
"""

import logging
from typing import Any, Dict, List

from .env_config import config

ALLOWED_ROLES = config.ALLOWED_ROLES
INCLUDE_SYSTEM_MESSAGES = config.INCLUDE_SYSTEM_MESSAGES
MAX_HISTORY_LENGTH = config.MAX_HISTORY_LENGTH

logger = logging.getLogger(__name__)


def sanitize_conversation_history(
    conversation: Any,
) -> Dict[str, List[Dict[str, str]]]:
    """Filter conversation history based on configured settings.

    Args:
        conversation (Any): Raw conversation data. Either a list of message
            dicts or a dict containing a `messages` key.

    Returns:
        Dict[str, List[Dict[str, str]]]: Sanitized conversation data containing
        standardized messages.

    Raises:
        ValueError: If the conversation format is invalid.
    """
    if isinstance(conversation, list):
        messages = conversation
    elif isinstance(conversation, dict) and "messages" in conversation:
        messages = conversation["messages"]
    else:
        raise ValueError(
            "Invalid conversation format; expected list or dict with 'messages'."
        )

    if not isinstance(messages, list):
        raise ValueError("Conversation messages must be provided as a list.")

    filtered_messages = []
    for msg in messages:
        if not isinstance(msg, dict):
            logger.warning("Skipping non-dict message: %s", msg)
            continue

        role = msg.get("role")
        content = msg.get("content")
        if role is None or content is None:
            logger.warning("Skipping message missing required fields: %s", msg)
            continue

        if role == "system" and not INCLUDE_SYSTEM_MESSAGES:
            continue
        if role != "system" and role not in ALLOWED_ROLES:
            continue

        filtered_messages.append({"role": role, "content": content})

    return {"messages": filtered_messages[-MAX_HISTORY_LENGTH:]}


def format_conversation_history_for_prompt(conversation: Dict[str, Any]) -> str:
    """Format conversation messages into a structured string for LLM prompts.

    Args:
        conversation (Dict[str, Any]): Conversation dict with a `messages` key
            containing message dicts with `role` and `content` keys.

    Returns:
        str: Conversation rendered as "[ROLE]: content" separated by double
        newlines, or a fallback message when no history is available.

    Raises:
        ValueError: If the `messages` entry is not a list.
    """
    messages = conversation.get("messages") if isinstance(conversation, dict) else None
    if not messages:
        return "No conversation history available."
    if not isinstance(messages, list):
        raise ValueError("conversation['messages'] must be provided as a list.")

    formatted_parts = []
    for msg in messages:
        if not isinstance(msg, dict):
            logger.warning("Skipping non-dict message: %s", msg)
            continue
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        formatted_parts.append(f"[{role}]: {content}")

    return (
        "\n\n".join(formatted_parts)
        if formatted_parts
        else "No conversation history available."
    )
