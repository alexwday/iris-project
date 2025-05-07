"""
Configuration Settings for Test Evaluation Tool

This module contains configuration settings for the entire test evaluation tool,
including environment variables, model settings, and operational parameters.
"""

import logging
import os
from typing import Dict, List, Optional

# Environment settings - hardcoded for simplicity
IS_RBC_ENV = False  # Set to True if using in RBC environment
USE_SSL = False     # Set to True if using SSL
USE_OAUTH = False   # Set to True if using OAuth

# LLM Model settings
DEFAULT_MODEL = "gpt-4"
BASE_URL = "https://api.openai.com/v1"  # Default OpenAI URL

# RBC environment URL - uncomment and modify if using RBC environment
# BASE_URL = "https://perf-apigw-int.saifg.rbc.com/JLCO/llm-control-stack/v1"

# Request settings
REQUEST_TIMEOUT = 180  # Timeout in seconds for API requests (3 minutes)

# Retry settings for API requests
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
RETRY_DELAY_SECONDS = 2  # Delay between retry attempts in seconds

# Token preview settings for logging
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

# Excel processing settings - removed as we now process entire sheets automatically

# Get module logger
logger = logging.getLogger(__name__)
logger.debug("Test evaluation tool configuration loaded")