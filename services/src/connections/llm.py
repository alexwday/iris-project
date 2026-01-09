"""
OpenAI Connector Module.

Provides a single connector to the OpenAI API that handles all types of calls
including streaming, non-streaming, and tool calls. Works in both RBC and local
environments.

Functions:
    calculate_cost: Calculate token usage costs
    call_llm: Make a call to the OpenAI API with the given parameters

Classes:
    OpenAIConnectorError: Exception for OpenAI connector errors
"""

import logging
import time
from typing import Any, Iterator, Optional, Tuple

from openai import OpenAI

from ..utils.env_config import config

logger = logging.getLogger(__name__)
logging.getLogger("openai").setLevel(logging.INFO)

BASE_URL = config.BASE_URL
MAX_RETRY_ATTEMPTS = config.MAX_RETRY_ATTEMPTS
REQUEST_TIMEOUT = config.REQUEST_TIMEOUT
RETRY_DELAY_SECONDS = config.RETRY_DELAY_SECONDS


class OpenAIConnectorError(Exception):
    """Exception class for OpenAI connector errors."""


UsageDetails = Optional[dict]
LLMResponse = Tuple[Any, UsageDetails]


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    prompt_token_cost: float,
    completion_token_cost: float,
) -> float:
    """
    Calculate total cost based on token usage and per-token costs.

    Args:
        prompt_tokens: Number of prompt tokens used.
        completion_tokens: Number of completion tokens used.
        prompt_token_cost: Cost per 1K prompt tokens in USD.
        completion_token_cost: Cost per 1K completion tokens in USD.

    Returns:
        Total cost in USD.
    """
    prompt_cost = (prompt_tokens / 1000) * prompt_token_cost
    completion_cost = (completion_tokens / 1000) * completion_token_cost
    return prompt_cost + completion_cost


def _build_usage_details(
    api_response: Any,
    model_name: str,
    prompt_token_cost: float,
    completion_token_cost: float,
    response_time_ms: int,
) -> UsageDetails:
    """
    Build usage details dict from API response.

    Args:
        api_response: The OpenAI API response object.
        model_name: Name of the model used.
        prompt_token_cost: Cost per 1K prompt tokens.
        completion_token_cost: Cost per 1K completion tokens.
        response_time_ms: Response time in milliseconds.

    Returns:
        Usage details dict or None if no usage data.
    """
    if not hasattr(api_response, "usage") or not api_response.usage:
        return None

    prompt_tokens = api_response.usage.prompt_tokens or 0
    completion_tokens = api_response.usage.completion_tokens or 0
    cost = calculate_cost(
        prompt_tokens, completion_tokens, prompt_token_cost, completion_token_cost
    )
    return {
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost": cost,
        "response_time_ms": response_time_ms,
    }


def _make_embedding_call(client: OpenAI, params: dict) -> Any:
    """
    Make an embedding API call.

    Args:
        client: OpenAI client instance.
        params: Parameters for the embedding call.

    Returns:
        API response from embeddings.create.
    """
    embedding_params = {
        "input": params.get("input"),
        "model": params.get("model"),
        "dimensions": params.get("dimensions"),
        "timeout": params.get("timeout", REQUEST_TIMEOUT),
    }
    embedding_params = {k: v for k, v in embedding_params.items() if v is not None}
    return client.embeddings.create(**embedding_params)


def call_llm(
    oauth_token: str,
    prompt_token_cost: float = 0,
    completion_token_cost: float = 0,
    **params,
) -> Any:
    """
    Make a call to the OpenAI API with the given parameters.

    Returns the API response directly for non-streaming calls. For streaming
    calls, returns an iterator that yields response chunks and a final dict
    containing usage statistics.

    Args:
        oauth_token: OAuth token (RBC) or OpenAI API key (local).
        prompt_token_cost: Cost per 1K prompt tokens in USD.
        completion_token_cost: Cost per 1K completion tokens in USD.
        **params: Parameters to pass to the OpenAI API including model,
            messages, stream, tools, tool_choice, temperature, max_tokens.

    Returns:
        OpenAI API response object (non-streaming) or an iterator (streaming).

    Raises:
        OpenAIConnectorError: If the API call fails after all retry attempts.
    """
    call_start_time = time.time()
    client = OpenAI(api_key=oauth_token, base_url=BASE_URL)
    logger.info("Connecting to OpenAI API at %s", BASE_URL)

    if "timeout" not in params:
        params["timeout"] = REQUEST_TIMEOUT

    is_embedding = params.pop("is_embedding", False)
    is_streaming = params.get("stream", False) if not is_embedding else False
    if is_streaming:
        params["stream_options"] = {"include_usage": True}

    model_name = params.get("model", "unknown")
    last_exception = None

    for attempt_num in range(1, MAX_RETRY_ATTEMPTS + 1):
        start_time = time.time()

        try:
            if is_embedding:
                return _make_embedding_call(client, params)

            api_response = client.chat.completions.create(**params)

            if is_streaming:
                return _stream_wrapper(
                    stream_iterator=api_response,
                    model_name=model_name,
                    prompt_token_cost=prompt_token_cost,
                    completion_token_cost=completion_token_cost,
                    call_start_time=call_start_time,
                )

            return api_response, _build_usage_details(
                api_response,
                model_name,
                prompt_token_cost,
                completion_token_cost,
                int((time.time() - start_time) * 1000),
            )

        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
            last_exception = exc
            logger.warning(
                "Call attempt %d failed after %.2f seconds: %s",
                attempt_num,
                time.time() - start_time,
                type(exc).__name__,
            )

            if attempt_num < MAX_RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    logger.error("Failed to complete call after %d attempts", MAX_RETRY_ATTEMPTS)
    raise OpenAIConnectorError(
        f"Failed to complete OpenAI API call: {last_exception}"
    ) from last_exception


def _stream_wrapper(
    stream_iterator: Iterator,
    model_name: str,
    prompt_token_cost: float,
    completion_token_cost: float,
    call_start_time: float,
) -> Iterator:
    """
    Wrap the OpenAI stream iterator to handle usage statistics.

    Args:
        stream_iterator: The streaming response from OpenAI API.
        model_name: Name of the model being used.
        prompt_token_cost: Cost per 1K prompt tokens.
        completion_token_cost: Cost per 1K completion tokens.
        call_start_time: Start time of the API call.

    Yields:
        Response chunks followed by usage details dict.
    """
    final_usage_data = None

    try:
        for chunk in stream_iterator:
            yield chunk
            if hasattr(chunk, "usage") and chunk.usage:
                final_usage_data = chunk.usage
    finally:
        total_response_time_ms = int((time.time() - call_start_time) * 1000)

        if final_usage_data:
            prompt_tokens = final_usage_data.prompt_tokens or 0
            completion_tokens = final_usage_data.completion_tokens or 0
            cost = calculate_cost(
                prompt_tokens,
                completion_tokens,
                prompt_token_cost,
                completion_token_cost,
            )
            yield {
                "usage_details": {
                    "model": model_name,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cost": cost,
                    "response_time_ms": total_response_time_ms,
                }
            }
        else:
            logger.warning("Stream finished but no usage data found in final chunk")
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
