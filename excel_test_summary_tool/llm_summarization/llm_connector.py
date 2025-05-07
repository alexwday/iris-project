"""LLM connector for interacting with OpenAI API."""

import logging
import ssl  # Added for SSL error handling
import time
from typing import Any, Dict, Optional, Iterator

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
logging.basicConfig(level=logging.INFO)
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
    
    while attempts < MAX_RETRY_ATTEMPTS:
        try:
            # Create OpenAI client
            client = OpenAI(api_key=api_key, base_url=BASE_URL)
            
            # Prepare parameters
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
            
            # Log request (excluding sensitive content)
            logger.info(f"Calling OpenAI API with model: {model}, temperature: {temperature}")
            
            # Make the API call
            start_time = time.time()
            response = client.chat.completions.create(**request_params)
            end_time = time.time()
            
            # Log response time
            logger.info(f"API call completed in {(end_time - start_time) * 1000:.2f}ms")
            
            # Extract and return the response content
            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                return {
                    "content": content,
                    "model": model,
                    "finish_reason": response.choices[0].finish_reason
                }
            else:
                raise LLMConnectorError("Invalid API response format")
                
        except ssl.SSLWantReadError as e:
            # Handle SSL-specific errors
            last_exception = e
            attempts += 1
            logger.warning(f"SSL error during API call attempt {attempts}: {str(e)}")
            
            if attempts < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
        except Exception as e:
            last_exception = e
            attempts += 1
            logger.warning(f"API call attempt {attempts} failed: {str(e)}")
            
            if attempts < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
                
    # If we've exhausted all retries, raise the last exception
    logger.error(f"Failed to complete API call after {attempts} attempts")
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