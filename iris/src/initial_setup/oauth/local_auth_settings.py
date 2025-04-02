# python/iris/src/initial_setup/oauth/local_auth_settings.py
"""
Local Authentication Settings

This module defines the authentication settings for the local development environment.
In this environment, we use OpenAI API key instead of OAuth.

Attributes:
    OPENAI_API_KEY (str): OpenAI API key for local development
    TOKEN_PREVIEW_LENGTH (int): Number of characters to show in token preview for logging

Dependencies:
    - logging
"""

import logging

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Authentication settings for local environment
OPENAI_API_KEY = "sk-proj-your-openai-api-key-here"  # Set your OpenAI API key here or use an environment variable

# Token preview settings for logging
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

logger.debug("Local authentication settings initialized")