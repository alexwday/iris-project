# python/iris/src/conversation_setup/conversation_settings.py
"""
Configuration settings for conversation management.
Defines message history limits and allowed roles.

Attributes:
    MAX_HISTORY_LENGTH (int): Number of most recent messages to retain
    ALLOWED_ROLES (list): Roles to include in processed conversation
    INCLUDE_SYSTEM_MESSAGES (bool): Whether to include system messages

Dependencies:
    - logging
"""

import logging

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Number of most recent messages to retain
MAX_HISTORY_LENGTH = 10

# Roles to include in processed conversation
ALLOWED_ROLES = ["user", "assistant"]

# Whether to include system messages
INCLUDE_SYSTEM_MESSAGES = False

logger.debug("Conversation settings initialized")
