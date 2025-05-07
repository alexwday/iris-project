"""LLM connector for interacting with OpenAI API."""

import logging
import time
from typing import Any, Dict, Optional, Iterator

from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMConnectorError(Exception):
    """Base exception class for LLM connector errors."""
    pass


def call_llm(
    api_key: str,
    messages: list,
    model: str = "gpt-4",
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    **params
) -> Dict[str, Any]:
    """
    Makes a call to the OpenAI API and returns the response.
    
    Args:
        api_key: OpenAI API key
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
    try:
        # Create OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Prepare parameters
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
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
            
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        raise LLMConnectorError(f"Failed to complete API call: {str(e)}")


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