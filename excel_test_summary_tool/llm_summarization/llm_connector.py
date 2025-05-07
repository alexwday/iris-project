"""
LLM connector for interacting with OpenAI API.

This module provides a connector to the OpenAI API for summarizing test cases.
It handles authentication, SSL configuration, and API communication.
"""

import logging
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from ..config import (
    BASE_URL,
    IS_RBC_ENV,
    MAX_RETRY_ATTEMPTS,
    REQUEST_TIMEOUT,
    RETRY_DELAY_SECONDS,
    TOKEN_PREVIEW_LENGTH,
    USE_OAUTH,
    USE_SSL
)
from ..oauth.oauth import setup_oauth
from ..ssl.ssl import setup_ssl

# Set up logging
logger = logging.getLogger(__name__)


class LLMConnectorError(Exception):
    """Base exception class for LLM connector errors."""
    pass


def setup_llm_environment():
    """
    Set up the environment for LLM API access.
    
    Returns:
        str: API token or key to use for API access
    """
    # Configure SSL if needed
    if USE_SSL:
        setup_ssl()
    
    # Get API token or key
    return setup_oauth()


def call_llm(
    api_key: str = None,
    messages: list = None,
    model: str = "gpt-4",
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    **params
) -> Dict[str, Any]:
    """
    Makes a call to the OpenAI API and returns the response.
    
    Args:
        api_key: OpenAI API key (optional if setup_llm_environment is called separately)
        messages: List of message dictionaries to send to the model
        model: The model to use
        temperature: Randomness parameter
        max_tokens: Maximum tokens for model response
        **params: Additional parameters to pass to the OpenAI API
        
    Returns:
        Dictionary containing the model's response
        
    Raises:
        LLMConnectorError: If the API call fails
    """
    # Get API key if not provided
    if api_key is None:
        api_key = setup_llm_environment()
    
    attempts = 0
    last_exception = None
    call_start_time = time.time()  # Start timing the call including retries
    
    # Set base URL for the API client
    api_base_url = BASE_URL
    
    # Create the OpenAI client
    client = OpenAI(api_key=api_key, base_url=api_base_url)
    
    # Log token preview for security
    token_preview = (
        api_key[:TOKEN_PREVIEW_LENGTH] + "..."
        if len(api_key) > TOKEN_PREVIEW_LENGTH
        else api_key
    )
    auth_type = "OAuth token" if IS_RBC_ENV and USE_OAUTH else "API key"
    logger.info(f"Using {auth_type}: {token_preview}")
    logger.info(f"Using API base URL: {api_base_url}")
    
    # Prepare request parameters
    request_params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "timeout": REQUEST_TIMEOUT
    }
    
    # Add max_tokens if provided
    if max_tokens is not None:
        request_params["max_tokens"] = max_tokens
        
    # Add any additional parameters
    request_params.update(params)
    
    # Log key parameters (excluding sensitive content)
    safe_params = {
        k: v
        for k, v in request_params.items()
        if k not in ["messages"]
    }
    logger.info(f"API call parameters (excluding message content): {safe_params}")
    
    while attempts < MAX_RETRY_ATTEMPTS:
        attempt_start_time = time.time()  # Time this specific attempt
        attempts += 1
        
        try:
            logger.info(
                f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Sending request to OpenAI API"
            )
            
            # Make the API call
            api_response = client.chat.completions.create(**request_params)
            attempt_response_time_ms = int((time.time() - attempt_start_time) * 1000)
            
            logger.info(f"Received response for attempt {attempts} in {attempt_response_time_ms} ms")
            
            # Extract and return the response content
            if hasattr(api_response, 'choices') and len(api_response.choices) > 0:
                content = api_response.choices[0].message.content
                
                # Calculate usage for logging
                if hasattr(api_response, "usage") and api_response.usage:
                    prompt_tokens = api_response.usage.prompt_tokens or 0
                    completion_tokens = api_response.usage.completion_tokens or 0
                    usage_details = {
                        'model': model,
                        'prompt_tokens': prompt_tokens,
                        'completion_tokens': completion_tokens,
                        'response_time_ms': attempt_response_time_ms
                    }
                    logger.info(f"Usage details: {usage_details}")
                
                return {
                    "content": content,
                    "model": model,
                    "finish_reason": api_response.choices[0].finish_reason
                }
            else:
                raise LLMConnectorError("Invalid API response format")
                
        except Exception as e:
            last_exception = e
            attempt_time_secs = time.time() - attempt_start_time
            logger.warning(
                f"Call attempt {attempts} failed after {attempt_time_secs:.2f} seconds: {str(e)}"
            )
            
            if attempts < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
                
    # If we've exhausted all retries, raise the last exception
    total_time_secs = time.time() - call_start_time
    logger.error(f"Failed to complete call after {attempts} attempts and {total_time_secs:.2f} seconds")
    raise LLMConnectorError(f"Failed to complete API call: {str(last_exception)}")


def summarize_test_case(
    api_key: str,
    markdown_content: str,
    prompt_template: str,
    model: str = "gpt-4",
    temperature: float = 0.1
) -> str:
    """
    Summarizes a test case using the LLM.
    
    Args:
        api_key: OpenAI API key
        markdown_content: Markdown content of the test case
        prompt_template: Prompt template with {test_case_markdown} placeholder
        model: The model to use
        temperature: Randomness parameter
        
    Returns:
        Summary of the test case
        
    Raises:
        LLMConnectorError: If the API call fails
    """
    # Format the prompt by replacing the placeholder with the actual content
    prompt = prompt_template.replace("{test_case_markdown}", markdown_content)
    
    # Create the messages array
    messages = [
        {"role": "system", "content": "You are a test analysis assistant that summarizes test cases."},
        {"role": "user", "content": prompt}
    ]
    
    # Call the LLM
    response = call_llm(
        api_key=api_key,
        messages=messages,
        model=model,
        temperature=temperature
    )
    
    return response["content"]


def summarize_system_tests(
    api_key: str,
    system_name: str,
    test_summaries: str,
    prompt_template: str,
    model: str = "gpt-4",
    temperature: float = 0.1
) -> str:
    """
    Generates a system-level summary from individual test case summaries.
    
    Args:
        api_key: OpenAI API key
        system_name: Name of the system/sheet
        test_summaries: Combined summaries of all test cases in the system
        prompt_template: Prompt template with {system_name} and {test_case_summaries} placeholders
        model: The model to use
        temperature: Randomness parameter
        
    Returns:
        System-level summary
        
    Raises:
        LLMConnectorError: If the API call fails
    """
    # Format the prompt
    prompt = prompt_template.replace("{system_name}", system_name)
    prompt = prompt.replace("{test_case_summaries}", test_summaries)
    
    # Create the messages array
    messages = [
        {"role": "system", "content": "You are a test analysis assistant that summarizes test cases at a system level."},
        {"role": "user", "content": prompt}
    ]
    
    # Call the LLM
    response = call_llm(
        api_key=api_key,
        messages=messages,
        model=model,
        temperature=temperature
    )
    
    return response["content"]


def create_file_level_summary(
    api_key: str,
    system_summaries: str,
    prompt_template: str,
    model: str = "gpt-4",
    temperature: float = 0.1
) -> str:
    """
    Generates a file-level summary from all system summaries.
    
    Args:
        api_key: OpenAI API key
        system_summaries: Combined summaries of all systems
        prompt_template: Prompt template with {system_summaries} placeholder
        model: The model to use
        temperature: Randomness parameter
        
    Returns:
        File-level summary
        
    Raises:
        LLMConnectorError: If the API call fails
    """
    # Format the prompt
    prompt = prompt_template.replace("{system_summaries}", system_summaries)
    
    # Create the messages array
    messages = [
        {"role": "system", "content": "You are a test analysis assistant that summarizes test coverage across systems."},
        {"role": "user", "content": prompt}
    ]
    
    # Call the LLM
    response = call_llm(
        api_key=api_key,
        messages=messages,
        model=model,
        temperature=temperature
    )
    
    return response["content"]