# python/iris/src/initial_setup/oauth/oauth_settings.py
"""
OAuth Authentication Settings Configuration

This module defines the configuration settings for OAuth authentication,
including endpoints, credentials, and operational parameters for token
acquisition and management.

Attributes:
    OAUTH_URL (str): OAuth token endpoint URL
    CLIENT_ID (str): OAuth client identifier
    CLIENT_SECRET (str): OAuth client secret
    REQUEST_TIMEOUT (int): Timeout in seconds for OAuth requests
    MAX_RETRY_ATTEMPTS (int): Maximum number of retry attempts
    RETRY_DELAY_SECONDS (int): Delay between retry attempts in seconds
    TOKEN_PREVIEW_LENGTH (int): Number of characters to show in token preview

Dependencies:
    - logging
"""

import logging

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# OAuth endpoint configuration
OAUTH_URL = "x"  # Replace with actual OAuth endpoint in production
CLIENT_ID = "x"  # Replace with actual client ID in production
CLIENT_SECRET = "x"  # Replace with actual client secret in production
REQUEST_TIMEOUT = 30  # Timeout in seconds for OAuth requests

# Retry settings for token requests
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
RETRY_DELAY_SECONDS = 2  # Delay between retry attempts in seconds

# Token preview settings
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

logger.debug("OAuth settings initialized")