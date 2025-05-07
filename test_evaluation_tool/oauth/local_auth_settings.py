"""
Local Authentication Settings

This module contains authentication settings for local development environment.
"""

import logging
import os

# Get module logger
logger = logging.getLogger(__name__)

# OpenAI API key (for local development only)
# Always use environment variable to avoid hardcoding API keys
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-openai-api-key-here")

# Token preview settings
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

logger.debug("Local authentication settings initialized")