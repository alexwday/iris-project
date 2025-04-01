# python/iris/src/llm_connectors/rbc_openai.py
"""
OpenAI Connector Module

This module provides a single connector to the OpenAI API that handles
all types of calls including streaming, non-streaming, and tool calls.
It works in both RBC and local environments.

Functions:
    calculate_cost: Calculates token usage costs
    log_usage_statistics: Logs token usage and costs
    call_llm: Makes a call to the OpenAI API with the given parameters

Dependencies:
    - openai
    - logging
    - time
"""

import logging
import time
from typing import Dict, Any
from openai import OpenAI
from ..chat_model.model_settings import (
    IS_RBC_ENV, 
    BASE_URL, 
    USE_DLP,
    REQUEST_TIMEOUT,
    MAX_RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS,
    TOKEN_PREVIEW_LENGTH
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

class OpenAIConnectorError(Exception):
    """Base exception class for OpenAI connector errors."""
    pass

def calculate_cost(prompt_tokens: int, completion_tokens: int, prompt_token_cost: float, completion_token_cost: float) -> float:
    """
    Calculate total cost based on token usage and per-token costs.
    
    Args:
        prompt_tokens (int): Number of prompt tokens used
        completion_tokens (int): Number of completion tokens used
        prompt_token_cost (float): Cost per 1K prompt tokens in USD
        completion_token_cost (float): Cost per 1K completion tokens in USD
        
    Returns:
        float: Total cost in USD
    """
    prompt_cost = (prompt_tokens / 1000) * prompt_token_cost
    completion_cost = (completion_tokens / 1000) * completion_token_cost
    return prompt_cost + completion_cost

def log_usage_statistics(response, prompt_token_cost, completion_token_cost):
    """
    Log token usage and cost statistics from the model response.
    
    Args:
        response: Model response object with usage attribute
        prompt_token_cost (float): Cost per 1K prompt tokens in USD
        completion_token_cost (float): Cost per 1K completion tokens in USD
        
    Returns:
        dict: Usage statistics including token counts and costs
    """
    if hasattr(response, "usage"):
        completion_tokens = response.usage.completion_tokens
        prompt_tokens = response.usage.prompt_tokens
        total_tokens = response.usage.total_tokens
        
        # Calculate costs
        total_cost = calculate_cost(prompt_tokens, completion_tokens, prompt_token_cost, completion_token_cost)
        prompt_cost = (prompt_tokens / 1000) * prompt_token_cost
        completion_cost = (completion_tokens / 1000) * completion_token_cost
        
        logger.info(
            f"Token usage - Completion: {completion_tokens} (${completion_cost:.4f}), "
            f"Prompt: {prompt_tokens} (${prompt_cost:.4f}), "
            f"Total: {total_tokens} tokens, Total Cost: ${total_cost:.4f}"
        )
        
        return {
            "completion_tokens": completion_tokens,
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens,
            "cost": total_cost
        }
    
    return None

def call_llm(oauth_token: str, prompt_token_cost: float = 0, completion_token_cost: float = 0, **params) -> Any:
    """
    Makes a call to the OpenAI API with the given parameters.
    
    This is a general-purpose function that handles all types of calls to the OpenAI API.
    It works in both RBC and local environments.
    
    Args:
        oauth_token (str): 
            - In RBC environment: OAuth token for API authentication
            - In local environment: OpenAI API key
        prompt_token_cost (float): Cost per 1K prompt tokens in USD
        completion_token_cost (float): Cost per 1K completion tokens in USD
        **params: Parameters to pass to the OpenAI API
            Required parameters:
                - model (str): The model to use
                - messages (list): The messages to send to the model
            Optional parameters:
                - stream (bool): Whether to stream the response
                - tools (list): Tool definitions for tool calls
                - tool_choice (dict/str): Tool choice specification
                - temperature (float): Randomness parameter
                - max_tokens (int): Maximum tokens for model response
                - ... any other parameters supported by the OpenAI API
    
    Returns:
        Any: The response from the OpenAI API, either a completion object or a stream
        
    Raises:
        OpenAIConnectorError: If the API call fails after all retry attempts
    """
    attempts = 0
    last_exception = None
    
    # Process any extra query parameters before creating the client
    api_base_url = BASE_URL
    
    # Handle extra query parameters
    if 'extra_query' in params:
        extra_query = params.pop('extra_query')
        
        # In RBC environment, merge with default DLP settings
        if IS_RBC_ENV and USE_DLP and 'is_stateful_dlp' not in extra_query:
            extra_query['is_stateful_dlp'] = True
            
        # Create a properly formatted query string
        query_string = '&'.join([f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in extra_query.items()])
        
        if query_string:
            # Check if the base URL already has query parameters
            separator = '&' if '?' in api_base_url else '?'
            # Update the base URL
            api_base_url = f"{api_base_url}{separator}{query_string}"
            
    # Don't add extra_query in local environment
    elif IS_RBC_ENV and USE_DLP:
        # Only add default DLP in RBC environment
        query_string = 'is_stateful_dlp=true'
        separator = '&' if '?' in api_base_url else '?'
        api_base_url = f"{api_base_url}{separator}{query_string}"
    
    # Now create the OpenAI client with the properly formed URL
    client = OpenAI(
        api_key=oauth_token,
        base_url=api_base_url
    )
    
    # Log token preview for security
    token_preview = oauth_token[:TOKEN_PREVIEW_LENGTH] + "..." if len(oauth_token) > TOKEN_PREVIEW_LENGTH else oauth_token
    auth_type = "OAuth token" if IS_RBC_ENV else "API key"
    logger.info(f"Using {auth_type}: {token_preview}")
    logger.info(f"Using API base URL: {api_base_url}")
    
    # Set timeout if not provided
    if 'timeout' not in params:
        params['timeout'] = REQUEST_TIMEOUT
    
    # Handle streaming with usage tracking
    is_streaming = params.get('stream', False)
    if is_streaming:
        # Ensure stream_options with include_usage is set
        stream_options = params.get('stream_options', {})
        stream_options['include_usage'] = True
        params['stream_options'] = stream_options
        
    # Log key parameters
    model = params.get('model', 'unknown')
    has_tools = 'tools' in params
    env_type = "RBC" if IS_RBC_ENV else "local"
    logger.info(f"Making {'streaming' if is_streaming else 'non-streaming'} call to model: {model}" + 
               f"{' with tools' if has_tools else ''} in {env_type} environment")
    
    while attempts < MAX_RETRY_ATTEMPTS:
        attempt_start = time.time()
        attempts += 1
        
        try:
            logger.info(f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Sending request to OpenAI API")
            
            # Make the API call
            response = client.chat.completions.create(**params)
            
            elapsed_time = time.time() - attempt_start
            logger.info(f"Received response in {elapsed_time:.2f} seconds")
            
            # Log usage for non-streaming responses
            if not is_streaming and prompt_token_cost and completion_token_cost:
                log_usage_statistics(response, prompt_token_cost, completion_token_cost)
            
            return response
            
        except Exception as e:
            last_exception = e
            attempt_time = time.time() - attempt_start
            logger.warning(f"Call attempt {attempts} failed after {attempt_time:.2f} seconds: {str(e)}")
            
            if attempts < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
    
    # If we've exhausted all retries, raise the last exception
    logger.error(f"Failed to complete call after {attempts} attempts")
    raise OpenAIConnectorError(f"Failed to complete OpenAI API call: {str(last_exception)}")