# services/src/llm_connectors/rbc_openai.py
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

from ..initial_setup.env_config import config

# Get settings from config
BASE_URL = config.BASE_URL
MAX_RETRY_ATTEMPTS = config.MAX_RETRY_ATTEMPTS
REQUEST_TIMEOUT = config.REQUEST_TIMEOUT
RETRY_DELAY_SECONDS = config.RETRY_DELAY_SECONDS
TOKEN_PREVIEW_LENGTH = config.TOKEN_PREVIEW_LENGTH

# Get module logger
logger = logging.getLogger(__name__)


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


def call_llm(
    oauth_token: str,
    prompt_token_cost: float = 0,
    completion_token_cost: float = 0,
    database_name: Optional[str] = None,  # Keep this for subagent compatibility
    **params,
) -> (
    Any
):  # Returns completion object OR stream iterator (which yields usage dict at end)
    """
    Makes a call to the OpenAI API with the given parameters. Returns the API
    response directly for non-streaming calls. For streaming calls, returns an
    iterator that yields response chunks and, as the final item, a dictionary
    containing usage statistics for that specific call.

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
        Any: OpenAI API response object (non-streaming) or an iterator (streaming).
             The streaming iterator yields content chunks followed by a final dict:
             {'usage_details': {'model': str, 'prompt_tokens': int, ...}}

    Raises:
        OpenAIConnectorError: If the API call fails after all retry attempts.
    """
    attempts = 0
    last_exception = None
    call_start_time = time.time()  # Start timing the call including retries

    # Set base URL for the API client
    api_base_url = BASE_URL

    # Now create the OpenAI client with the properly formed URL
    client = OpenAI(api_key=oauth_token, base_url=api_base_url)

    # Log token preview for security (only at debug level)
    token_preview = (
        oauth_token[:TOKEN_PREVIEW_LENGTH] + "..."
        if len(oauth_token) > TOKEN_PREVIEW_LENGTH
        else oauth_token
    )
    logger.info(f"Connecting to OpenAI API at {api_base_url}")

    # Set timeout if not provided
    if "timeout" not in params:
        params["timeout"] = REQUEST_TIMEOUT

    # Check if this is an embedding request
    is_embedding = params.pop("is_embedding", False)  # Remove flag from params

    # Handle streaming option (only for chat completions)
    is_streaming = params.get("stream", False) if not is_embedding else False
    if is_streaming:
        # Ensure stream_options includes usage for the final chunk
        params["stream_options"] = {"include_usage": True}

    # Capture model name for usage tracking
    model_name = params.get("model", "unknown")
    has_tools = "tools" in params
    logger.info(f"Making API call to {model_name} (streaming={is_streaming})")

    while attempts < MAX_RETRY_ATTEMPTS:
        attempt_start_time = time.time()  # Time this specific attempt
        attempts += 1

        try:

            # --- Make the API call based on type ---
            if is_embedding:
                # Extract embedding-specific parameters
                embedding_params = {
                    "input": params.get("input"),
                    "model": params.get("model"),
                    "dimensions": params.get("dimensions"),
                    "timeout": params.get("timeout", REQUEST_TIMEOUT),
                    # Add other relevant params if needed, e.g., encoding_format
                }
                # Filter out None values
                embedding_params = {
                    k: v for k, v in embedding_params.items() if v is not None
                }
                api_response = client.embeddings.create(**embedding_params)
                return api_response

            else:  # It's a chat completion call
                api_response = client.chat.completions.create(**params)
                attempt_response_time_ms = int(
                    (time.time() - attempt_start_time) * 1000
                )

            # --- Return based on type ---
            if is_streaming:
                # Return the stream wrapper directly
                return _stream_wrapper(
                    stream_iterator=api_response,
                    model_name=model_name,
                    prompt_token_cost=prompt_token_cost,
                    completion_token_cost=completion_token_cost,
                    # Pass the overall call start time to calculate total duration later
                    call_start_time=call_start_time,
                )
            else:  # Non-streaming chat completion or embedding
                # Calculate usage details for non-streaming chat completion
                usage_details = None
                if (
                    not is_embedding
                    and hasattr(api_response, "usage")
                    and api_response.usage
                ):
                    prompt_tokens = api_response.usage.prompt_tokens or 0
                    completion_tokens = api_response.usage.completion_tokens or 0
                    cost = calculate_cost(
                        prompt_tokens,
                        completion_tokens,
                        prompt_token_cost,
                        completion_token_cost,
                    )
                    usage_details = {
                        "model": model_name,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "cost": cost,
                        "response_time_ms": attempt_response_time_ms,  # Time for this successful attempt
                    }

                # Return the response object AND usage details (if applicable)
                # Caller needs to handle this tuple format
                return api_response, usage_details

        except Exception as e:
            last_exception = e
            attempt_time_secs = time.time() - attempt_start_time
            logger.warning(
                f"Call attempt {attempts} failed after {attempt_time_secs:.2f} seconds: {type(e).__name__}"
            )

            if attempts < MAX_RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    # If we've exhausted all retries, raise the last exception
    logger.error(f"Failed to complete call after {attempts} attempts")
    raise OpenAIConnectorError(
        f"Failed to complete OpenAI API call: {str(last_exception)}"
    )


# Helper generator for streaming responses to yield usage details at the end
def _stream_wrapper(
    stream_iterator: Iterator,
    model_name: str,
    prompt_token_cost: float,
    completion_token_cost: float,
    call_start_time: float,  # Overall start time of the call_llm function
) -> Iterator:
    """
    Wraps the OpenAI stream iterator to handle usage statistics and error handling.

    Args:
        stream_iterator (Iterator): The streaming response from OpenAI API
        model_name (str): Name of the model being used
        prompt_token_cost (float): Cost per prompt token
        completion_token_cost (float): Cost per completion token
        call_start_time (float): Start time of the API call

    Returns:
        Iterator: Wrapped streaming response with usage statistics
    """
    final_usage_data = None
    stream_start_time = time.time()  # Time the streaming part itself

    try:
        for chunk in stream_iterator:
            yield chunk
            # The final chunk in streams with include_usage=True contains the usage stats
            if hasattr(chunk, "usage") and chunk.usage:
                final_usage_data = chunk.usage
                # Don't break here, ensure the stream is fully consumed
    finally:
        # Calculate total duration from the initial call_llm start
        total_response_time_ms = int((time.time() - call_start_time) * 1000)

        # After the stream is exhausted, process and yield the final usage details
        if final_usage_data:
            prompt_tokens = final_usage_data.prompt_tokens or 0
            completion_tokens = final_usage_data.completion_tokens or 0
            cost = calculate_cost(
                prompt_tokens,
                completion_tokens,
                prompt_token_cost,
                completion_token_cost,
            )
            usage_details = {
                "model": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
                "response_time_ms": total_response_time_ms,  # Total time for the call
            }
            # Yield the usage details as the very last item
            yield {"usage_details": usage_details}
        else:
            logger.warning(
                "Stream finished, but no usage data found in the final chunk. Cannot report usage."
            )
            # Yield an empty usage dict or None to signal completion without usage
            yield {
                "usage_details": {
                    "model": model_name,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0,
                    "response_time_ms": total_response_time_ms,
                    "error": "Usage data missing from stream",
                }
            }
