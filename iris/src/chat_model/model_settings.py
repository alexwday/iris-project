# src/chat_model/model_settings.py
"""
Model Settings Configuration

This module provides centralized configuration for switching between RBC and local environments.
It defines model capabilities, endpoints, and environment-specific settings.

Attributes:
    ENVIRONMENT (str): Current environment ('rbc' or 'local')
    IS_RBC_ENV (bool): Whether we're in the RBC environment
    BASE_URL (str): API endpoint URL based on environment
    MODELS (dict): Model configurations by capability and environment
    
Functions:
    get_model_config: Returns model configuration based on capability and environment

Dependencies:
    - logging
"""

import logging

# Get module logger
logger = logging.getLogger(__name__)

# Manual environment selection - change this when switching environments
ENVIRONMENT = "local"  # Options: "local" or "rbc"
IS_RBC_ENV = ENVIRONMENT == "rbc"

logger.info(f"Using environment: {ENVIRONMENT}")

# API configuration with explicit base URLs for both environments
RBC_BASE_URL = "https://perf-apigw-int.saifg.rbc.com/JLCO/llm-control-stack/v1"
LOCAL_BASE_URL = "https://api.openai.com/v1"  # Standard OpenAI API endpoint
BASE_URL = RBC_BASE_URL if IS_RBC_ENV else LOCAL_BASE_URL

logger.info(f"Using API base URL: {BASE_URL}")

# Environment-specific settings
USE_SSL = IS_RBC_ENV
USE_OAUTH = IS_RBC_ENV

# Model capability mapping - defines models for each capability in each environment
MODELS = {
    "small": {
        "rbc": {
            "name": "gpt-4o-mini-2024-07-18", 
            "prompt_token_cost": 0.00016238, 
            "completion_token_cost": 0.00065175
        },
        "local": {
            "name": "gpt-4o-mini-2024-07-18", 
            "prompt_token_cost": 0.0000015, 
            "completion_token_cost": 0.000002
        }
    },
    "large": {
        "rbc": {
            "name": "gpt-4o-2024-05-13", 
            "prompt_token_cost": 0.00064952, 
            "completion_token_cost": 0.00260748
        },
        "local": {
            "name": "gpt-4o-2024-08-06", 
            "prompt_token_cost": 0.00001, 
            "completion_token_cost": 0.00003
        }
    }
}

# Request settings
REQUEST_TIMEOUT = 30  # Timeout in seconds for API requests
MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
RETRY_DELAY_SECONDS = 2  # Delay between retry attempts in seconds
TOKEN_PREVIEW_LENGTH = 7  # Number of characters to show in token preview

# Usage display settings
SHOW_USAGE_SUMMARY = True  # Whether to display token usage summary at the end of responses

def get_model_config(capability):
    """
    Get model configuration based on capability and current environment.
    
    Args:
        capability (str): The model capability ('small' or 'large')
        
    Returns:
        dict: Configuration for the requested model capability
        
    Raises:
        ValueError: If the requested capability is not defined
    """
    env_type = "rbc" if IS_RBC_ENV else "local"
    
    if capability not in MODELS:
        available = list(MODELS.keys())
        raise ValueError(f"Unknown model capability: {capability}. Available: {available}")
        
    config = MODELS[capability][env_type]
    logger.info(f"Using {capability} model: {config['name']} in {env_type} environment")
    return config

logger.debug("Model settings initialized")