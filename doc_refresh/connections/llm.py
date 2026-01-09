"""
OpenAI Connector Module for Document Refresh Pipeline.

Provides a connector to the OpenAI API for LLM calls and embeddings.
Works in both RBC and local environments.

Functions:
    calculate_cost: Calculate token usage costs
    call_llm: Make a chat completion call to the OpenAI API
    create_embedding: Generate embeddings for text input

Classes:
    OpenAIConnectorError: Exception for OpenAI connector errors
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import OpenAI

from ..utils.env_config import Config

logger = logging.getLogger(__name__)
logging.getLogger("openai").setLevel(logging.INFO)


class OpenAIConnectorError(Exception):
    """Exception class for OpenAI connector errors."""


UsageDetails = Optional[Dict[str, Any]]
LLMResponse = Tuple[Any, UsageDetails]


def _get_client(oauth_token: str) -> OpenAI:
    """
    Create OpenAI client with appropriate configuration.

    Args:
        oauth_token: OAuth token (RBC) or OpenAI API key (local).

    Returns:
        Configured OpenAI client.
    """
    base_url = Config.RBC_BASE_URL if Config.RBC_BASE_URL else None
    return OpenAI(api_key=oauth_token, base_url=base_url)


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
        prompt_token_cost: Cost per 1M prompt tokens in USD.
        completion_token_cost: Cost per 1M completion tokens in USD.

    Returns:
        Total cost in USD.
    """
    prompt_cost = (prompt_tokens / 1_000_000) * prompt_token_cost
    completion_cost = (completion_tokens / 1_000_000) * completion_token_cost
    return prompt_cost + completion_cost


def calculate_embedding_cost(token_count: int, cost_per_million: float) -> float:
    """
    Calculate embedding cost based on token count.

    Args:
        token_count: Number of tokens embedded.
        cost_per_million: Cost per 1M tokens in USD.

    Returns:
        Total cost in USD.
    """
    return (token_count / 1_000_000) * cost_per_million


def call_llm(
    oauth_token: str,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    prompt_token_cost: float = 0,
    completion_token_cost: float = 0,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict] = None,
    **kwargs,
) -> LLMResponse:
    """
    Make a chat completion call to the OpenAI API.

    Args:
        oauth_token: OAuth token (RBC) or OpenAI API key (local).
        messages: List of message dicts with 'role' and 'content'.
        model: Model name (defaults to Config.MODEL_LARGE).
        prompt_token_cost: Cost per 1M prompt tokens in USD.
        completion_token_cost: Cost per 1M completion tokens in USD.
        temperature: Sampling temperature (0.0 = deterministic).
        max_tokens: Maximum tokens in response.
        response_format: Response format specification (e.g., {"type": "json_object"}).
        **kwargs: Additional parameters for the API call.

    Returns:
        Tuple of (response_object, usage_details_dict).

    Raises:
        OpenAIConnectorError: If the API call fails after all retry attempts.
    """
    if model is None:
        model = Config.MODEL_LARGE

    client = _get_client(oauth_token)
    last_exception = None

    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "timeout": Config.REQUEST_TIMEOUT,
        **kwargs,
    }
    if max_tokens:
        params["max_tokens"] = max_tokens
    if response_format:
        params["response_format"] = response_format

    for attempt_num in range(1, Config.MAX_RETRY_ATTEMPTS + 1):
        start_time = time.time()

        try:
            logger.debug(
                "LLM call attempt %d/%d with model %s",
                attempt_num,
                Config.MAX_RETRY_ATTEMPTS,
                model,
            )
            response = client.chat.completions.create(**params)

            response_time_ms = int((time.time() - start_time) * 1000)
            usage_details = _build_usage_details(
                response, model, prompt_token_cost, completion_token_cost, response_time_ms
            )

            logger.debug(
                "LLM call successful: %d prompt tokens, %d completion tokens",
                usage_details.get("prompt_tokens", 0) if usage_details else 0,
                usage_details.get("completion_tokens", 0) if usage_details else 0,
            )

            return response, usage_details

        except Exception as exc:
            last_exception = exc
            logger.warning(
                "LLM call attempt %d failed after %.2f seconds: %s",
                attempt_num,
                time.time() - start_time,
                type(exc).__name__,
            )

            if attempt_num < Config.MAX_RETRY_ATTEMPTS:
                time.sleep(Config.RETRY_DELAY_SECONDS)

    logger.error("LLM call failed after %d attempts", Config.MAX_RETRY_ATTEMPTS)
    raise OpenAIConnectorError(
        f"Failed to complete OpenAI API call: {last_exception}"
    ) from last_exception


def create_embedding(
    oauth_token: str,
    text: Union[str, List[str]],
    model: Optional[str] = None,
    dimensions: Optional[int] = None,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    """
    Generate embeddings for text input.

    Args:
        oauth_token: OAuth token (RBC) or OpenAI API key (local).
        text: Single string or list of strings to embed.
        model: Embedding model name (defaults to Config.MODEL_EMBEDDING).
        dimensions: Output dimensions (optional, model-dependent).

    Returns:
        Tuple of (embeddings_list, usage_details_dict).
        embeddings_list is a list of embedding vectors (one per input text).

    Raises:
        OpenAIConnectorError: If the API call fails.
    """
    if model is None:
        model = Config.MODEL_EMBEDDING

    client = _get_client(oauth_token)

    params = {
        "input": text,
        "model": model,
        "timeout": Config.REQUEST_TIMEOUT,
    }
    if dimensions:
        params["dimensions"] = dimensions

    try:
        start_time = time.time()
        response = client.embeddings.create(**params)
        response_time_ms = int((time.time() - start_time) * 1000)

        embeddings = [item.embedding for item in response.data]
        token_count = response.usage.total_tokens if response.usage else 0
        cost = calculate_embedding_cost(token_count, Config.MODEL_EMBEDDING_COST)

        usage_details = {
            "model": model,
            "token_count": token_count,
            "cost": cost,
            "response_time_ms": response_time_ms,
            "embedding_count": len(embeddings),
        }

        logger.debug(
            "Created %d embeddings (%d tokens, $%.6f)",
            len(embeddings),
            token_count,
            cost,
        )

        return embeddings, usage_details

    except Exception as exc:
        logger.error("Embedding call failed: %s", exc)
        raise OpenAIConnectorError(f"Failed to create embeddings: {exc}") from exc


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
        prompt_token_cost: Cost per 1M prompt tokens.
        completion_token_cost: Cost per 1M completion tokens.
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
