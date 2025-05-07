"""
Configuration Settings for Test Evaluation Tool

This module contains configuration settings for the entire test evaluation tool,
including environment variables, model settings, and operational parameters.
"""

import logging
import os
from typing import Dict, List, Optional

# Environment settings
IS_RBC_ENV = os.environ.get("IS_RBC_ENV", "false").lower() == "true"
USE_SSL = os.environ.get("USE_SSL", "false").lower() == "true"
USE_OAUTH = os.environ.get("USE_OAUTH", "false").lower() == "true"

# LLM Model settings
DEFAULT_MODEL = "gpt-4"
BASE_URL = "https://api.openai.com/v1"  # Default OpenAI URL, will be overridden in RBC env

# If in RBC environment, use their base URL
if IS_RBC_ENV:
    BASE_URL = "https://perf-apigw-int.saifg.rbc.com/JLCO/llm-control-stack/v1"

# Request settings
REQUEST_TIMEOUT = 180  # Timeout in seconds for API requests (3 minutes)

# Retry settings for API requests
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
RETRY_DELAY_SECONDS = 2  # Delay between retry attempts in seconds

# Token preview settings for logging
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

# Excel processing settings
EXCEL_CELL_MAX_ROWS = 100
EXCEL_CELL_COLUMNS = ["A", "B", "C"]  # Default columns to process

# Get module logger
logger = logging.getLogger(__name__)
logger.debug("Test evaluation tool configuration loaded")