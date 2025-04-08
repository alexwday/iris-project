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
from typing import Any, Dict, Optional, Iterator

from openai import OpenAI

from ..chat_model.model_settings import (
    BASE_URL,
    IS_RBC_ENV,
    MAX_RETRY_ATTEMPTS,
    REQUEST_TIMEOUT,
    RETRY_DELAY_SECONDS,
    TOKEN_PREVIEW_LENGTH,
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Global variables for token usage tracking
_token_usage = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "cost": 0.0,
}


class OpenAIConnectorError(Exception):
    """Base exception class for OpenAI connector errors."""

    pass


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    prompt_token_cost: float,
    completion_token_cost: float,
) -> float:
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


def log_usage_statistics(
    response,
    prompt_token_cost,
    completion_token_cost,
    database_name: Optional[str] = None,
    usage_data=None,  # Allow passing usage data directly for streams
):
    """
    Log token usage and cost statistics from the model response or provided data.

    Updates both the global token counter and, if provided, the database-specific counter.

    Args:
        response: Model response object with usage attribute
        prompt_token_cost (float): Cost per 1K prompt tokens in USD
        completion_token_cost (float): Cost per 1K completion tokens in USD
        database_name (str, optional): Identifier for database-specific tracking. Defaults to None.

    Returns:
        dict: Usage statistics including token counts and costs
    """
    global _token_usage

    # Use provided usage_data if available, otherwise try to get from response
    usage = usage_data
    if usage is None:
        if response and hasattr(response, "usage") and response.usage:
            usage = response.usage
        else:
            logger.warning(
                "Attempted to log usage statistics but no usage data was found in response or arguments."
            )
            return None

    # Safely access usage attributes from the determined source
    completion_tokens = getattr(usage, "completion_tokens", 0)
    prompt_tokens = getattr(usage, "prompt_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", 0)

    # Check if tokens are None (which can happen) and default to 0
    completion_tokens = completion_tokens if completion_tokens is not None else 0
    prompt_tokens = prompt_tokens if prompt_tokens is not None else 0
    total_tokens = total_tokens if total_tokens is not None else 0

    # Calculate costs
    total_cost = calculate_cost(
        prompt_tokens, completion_tokens, prompt_token_cost, completion_token_cost
    )
    prompt_cost = (prompt_tokens / 1000) * prompt_token_cost
    completion_cost = (completion_tokens / 1000) * completion_token_cost

    logger.info(
        f"Token usage - Completion: {completion_tokens} (${completion_cost:.4f}), "
        f"Prompt: {prompt_tokens} (${prompt_cost:.4f}), "
        f"Total: {total_tokens} tokens, Total Cost: ${total_cost:.4f}"
        f"{f' (Database: {database_name})' if database_name else ''}",
    )

    # Update global token usage tracker
    _token_usage["prompt_tokens"] += prompt_tokens
    _token_usage["completion_tokens"] += completion_tokens
    _token_usage["total_tokens"] += total_tokens
    _token_usage["cost"] += total_cost

    # Database-specific tracking was removed from database_router.py
    # The code attempting to call update_database_token_usage has been removed.
    # Global tracking above still works.
    if database_name:
        logger.debug(
            f"Database name '{database_name}' provided, but specific tracking is disabled."
        )

    return {
        "completion_tokens": completion_tokens,
        "prompt_tokens": prompt_tokens,
        "total_tokens": total_tokens,
        "cost": total_cost,
    }


def call_llm(
    oauth_token: str,
    prompt_token_cost: float = 0,
    completion_token_cost: float = 0,
    database_name: Optional[str] = None,
    **params,
) -> Any:  # Returns completion object or stream iterator
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
        database_name (str, optional): Identifier for database-specific tracking. Defaults to None.
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
        Any: OpenAI API response (completion object or a generator yielding stream chunks)

    Raises:
        OpenAIConnectorError: If the API call fails after all retry attempts
    """
    attempts = 0
    last_exception = None

    # Set base URL for the API client (no query parameters here)
    api_base_url = BASE_URL

    # Now create the OpenAI client with the properly formed URL
    client = OpenAI(api_key=oauth_token, base_url=api_base_url)

    # Log token preview for security
    token_preview = (
        oauth_token[:TOKEN_PREVIEW_LENGTH] + "..."
        if len(oauth_token) > TOKEN_PREVIEW_LENGTH
        else oauth_token
    )
    auth_type = "OAuth token" if IS_RBC_ENV else "API key"
    logger.info(f"Using {auth_type}: {token_preview}")
    logger.info(f"Using API base URL: {api_base_url}")

    # Set timeout if not provided
    if "timeout" not in params:
        params["timeout"] = REQUEST_TIMEOUT

    # Handle streaming with usage tracking
    is_streaming = params.get("stream", False)
    if is_streaming:
        # Ensure stream_options with include_usage is set
        stream_options = params.get("stream_options", {})
        stream_options["include_usage"] = True
        params["stream_options"] = stream_options
    else:
        # Ensure stream_options is not present for non-streaming calls if it causes issues
        # (Though generally harmless, explicit removal might prevent future API conflicts)
        params.pop("stream_options", None)

    # Log key parameters
    model = params.get("model", "unknown")
    has_tools = "tools" in params
    env_type = "RBC" if IS_RBC_ENV else "local"
    logger.info(
        f"Making {'streaming' if is_streaming else 'non-streaming'} call to model: {model}"
        f"{' with tools' if has_tools else ''} in {env_type} environment"
    )

    while attempts < MAX_RETRY_ATTEMPTS:
        attempt_start = time.time()
        attempts += 1

        try:
            logger.info(
                f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Sending request to OpenAI API"
            )

            # Log only non-sensitive API call parameters
            safe_params = {
                k: v
                for k, v in params.items()
                if k not in ["messages", "tools", "tool_choice"]
            }
            logger.info(
                f"API call parameters (excluding message content): {safe_params}"
            )

            # Make the API call
            api_response = client.chat.completions.create(**params)

            elapsed_time = time.time() - attempt_start
            logger.info(
                f"Received {'initial stream chunk' if is_streaming else 'response'} in {elapsed_time:.2f} seconds"
            )

            # Handle streaming vs non-streaming response and logging
            if is_streaming:
                # Return a generator that wraps the stream and logs usage at the end
                return _stream_wrapper(
                    api_response,
                    prompt_token_cost,
                    completion_token_cost,
                    database_name,
                )
            else:
                # Log usage for non-streaming responses immediately
                if prompt_token_cost and completion_token_cost:
                    log_usage_statistics(
                        api_response,
                        prompt_token_cost,
                        completion_token_cost,
                        database_name=database_name,
                    )
                return api_response  # Return the complete response object

        except Exception as e:
            last_exception = e
            attempt_time = time.time() - attempt_start
            logger.warning(
                f"Call attempt {attempts} failed after {attempt_time:.2f} seconds: {str(e)}"
            )

            if attempts < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)

    # If we've exhausted all retries, raise the last exception
    logger.error(f"Failed to complete call after {attempts} attempts")
    raise OpenAIConnectorError(
        f"Failed to complete OpenAI API call: {str(last_exception)}"
    )


# Helper generator for streaming responses to log usage at the end
def _stream_wrapper(
    stream: Iterator,
    prompt_token_cost: float,
    completion_token_cost: float,
    database_name: Optional[str] = None,
) -> Iterator:
    """Wraps the OpenAI stream iterator to log usage statistics after completion."""
    last_chunk = None
    try:
        for chunk in stream:
            yield chunk
            last_chunk = chunk  # Keep track of the last chunk
    finally:
        # After the stream is exhausted (or loop breaks), check the last chunk for usage
        if last_chunk and hasattr(last_chunk, "usage") and last_chunk.usage:
            logger.info("Stream finished. Logging usage from final chunk.")
            log_usage_statistics(
                response=None,  # Pass None as response, we use usage_data
                prompt_token_cost=prompt_token_cost,
                completion_token_cost=completion_token_cost,
                database_name=database_name,
                usage_data=last_chunk.usage,  # Pass the usage data directly
            )
        else:
            logger.warning(
                "Stream finished, but no usage data found in the final chunk."
            )


def get_token_usage() -> Dict[str, Any]:
    """
    Get the current token usage statistics.

    Returns:
        Dict containing prompt_tokens, completion_tokens, total_tokens, and cost
    """
    global _token_usage
    return _token_usage.copy()


def reset_token_usage() -> None:
    """
    Reset the token usage statistics to zero.
    """
    global _token_usage
    _token_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost": 0.0,
    }
