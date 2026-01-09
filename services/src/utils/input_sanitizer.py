"""
Input Sanitizer Module.

Handles processing and filtering of conversation histories for use with
language models. Standardizes different conversation formats, filters by
role, and manages history length.

Functions:
    process_conversation: Filter and format conversation data
    format_conversation_for_prompt: Format conversation dict to string for LLM prompts
"""

import logging
from typing import Any, Dict, List

from .env_config import config

ALLOWED_ROLES = config.ALLOWED_ROLES
INCLUDE_SYSTEM_MESSAGES = config.INCLUDE_SYSTEM_MESSAGES
MAX_HISTORY_LENGTH = config.MAX_HISTORY_LENGTH

logger = logging.getLogger(__name__)


def process_conversation(conversation: Any) -> Dict[str, List[Dict[str, str]]]:
    """
    Process and filter conversation history based on configured settings.

    Only extracts required fields (role and content) from messages.

    Args:
        conversation: Raw conversation data. Either a list of messages
            (e.g. [{"role": "...", "content": "..."}]) or a dict with
            "messages" as a key.

    Returns:
        Filtered conversation data with standardized messages.

    Raises:
        ValueError: If conversation format is invalid or required fields missing.
    """
    try:
        if isinstance(conversation, list):
            conversation = {"messages": conversation}
        elif not isinstance(conversation, dict) or "messages" not in conversation:
            raise ValueError("Invalid conversation format")

        messages = conversation["messages"]

        filtered_messages = []
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                logger.warning("Skipping message missing required fields: %s", msg)
                continue

            role_allowed = msg["role"] in ALLOWED_ROLES
            is_system = INCLUDE_SYSTEM_MESSAGES and msg["role"] == "system"
            if role_allowed or is_system:
                filtered_message = {"role": msg["role"], "content": msg["content"]}
                filtered_messages.append(filtered_message)

        recent_messages = filtered_messages[-MAX_HISTORY_LENGTH:]

        return {"messages": recent_messages}

    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Error processing conversation: %s", exc)
        raise


def format_conversation_for_prompt(conversation: Dict[str, Any]) -> str:
    """
    Format conversation messages into a structured string for LLM prompts.

    Converts a conversation dict (with 'messages' key) into a formatted
    string suitable for inclusion in prompt templates.

    Args:
        conversation: Conversation dict with 'messages' key containing
            list of message dicts with 'role' and 'content' keys.

    Returns:
        Formatted string representation of the conversation.
        Format: "[ROLE]: content" separated by double newlines.

    Example:
        Input: {"messages": [{"role": "user", "content": "Hello"}]}
        Output: "[USER]: Hello"
    """
    if not conversation or "messages" not in conversation:
        return "No conversation history available."

    formatted_parts = []
    for msg in conversation["messages"]:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        formatted_parts.append(f"[{role}]: {content}")

    return "\n\n".join(formatted_parts)
