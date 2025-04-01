# python/iris/src/conversation_setup/conversation.py
"""
Conversation Processing Module

This module handles the processing and filtering of conversation histories
for use with language models. It standardizes different conversation formats,
filters by role, and manages history length.

Functions:
    process_conversation: Filters and formats conversation data

Dependencies:
    - logging
    - typing
"""

import logging
from typing import Any, Dict, List
from .conversation_settings import (
    MAX_HISTORY_LENGTH,
    ALLOWED_ROLES,
    INCLUDE_SYSTEM_MESSAGES
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

def process_conversation(conversation: Any) -> Dict[str, List[Dict[str, str]]]:
    """
    Process and filter conversation history based on configured settings.
    Only extracts required fields (role and content) from messages.
    
    Args:
        conversation (Any): Raw conversation data. This can be either:
            1) A list of messages (e.g. [{"role": "...", "content": "..."}])
            2) A dict with "messages" as a key.
    
    Returns:
        Dict[str, List[Dict[str, str]]]: Filtered conversation data with standardized messages.
    
    Raises:
        ValueError: If conversation format is invalid or required fields are missing.
    """
    try:
        # If conversation is just a list, wrap it in a dict
        if isinstance(conversation, list):
            conversation = {"messages": conversation}
        
        # If it's not a dict or doesn't have 'messages', raise an error
        elif not isinstance(conversation, dict) or 'messages' not in conversation:
            raise ValueError("Invalid conversation format")
        
        messages = conversation['messages']
        
        # Filter messages by role and extract only required fields
        filtered_messages = []
        for msg in messages:
            # Check for required fields
            if 'role' not in msg or 'content' not in msg:
                logger.warning(f"Skipping message missing required fields: {msg}")
                continue
            
            # Check if role is allowed
            if (msg['role'] in ALLOWED_ROLES) or (INCLUDE_SYSTEM_MESSAGES and msg['role'] == 'system'):
                # Create new message with only required fields
                filtered_message = {
                    'role': msg['role'],
                    'content': msg['content']
                }
                filtered_messages.append(filtered_message)
        
        # Keep only the most recent messages
        recent_messages = filtered_messages[-MAX_HISTORY_LENGTH:]
        
        logger.info(
            f"Processed conversation: {len(messages)} messages filtered to "
            f"{len(recent_messages)} messages"
        )
        
        return {
            "messages": recent_messages
        }
        
    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
        raise