# python/iris/src/llm_connectors/rbc_openai_settings.py
"""
RBC OpenAI Connection Settings

This module defines the connection settings for the RBC OpenAI endpoint.

Attributes:
    BASE_URL (str): RBC OpenAI API endpoint URL
    REQUEST_TIMEOUT (int): Timeout in seconds for API requests
    MAX_RETRY_ATTEMPTS (int): Maximum number of retry attempts
    RETRY_DELAY_SECONDS (int): Delay between retry attempts in seconds
    TOKEN_PREVIEW_LENGTH (int): Number of characters to show in token preview for logging
"""

import logging

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# API endpoint configuration
BASE_URL = "https://perf-apigw-int.saifg.rbc.com/JLCO/llm-control-stack/v1"

# Request settings
REQUEST_TIMEOUT = 180  # Timeout in seconds for API requests (3 minutes)

# Retry settings for API requests
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
RETRY_DELAY_SECONDS = 2  # Delay between retry attempts in seconds

# Token preview settings for logging
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

logger.debug("RBC OpenAI connection settings initialized")
