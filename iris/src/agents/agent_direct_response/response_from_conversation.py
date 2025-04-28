# python/iris/src/agents/agent_direct_response/response_from_conversation.py
"""
Direct Response Agent Module

This module handles direct response generation based solely on conversation context
without requiring additional database research.

Functions:
    response_from_conversation: Generate a direct response based on conversation context

Dependencies:
    - json
    - logging
    - OpenAI connector for LLM calls
"""

import logging
from typing import Generator, Dict, Any # Added Generator, Dict, Any

from ...chat_model.model_settings import get_model_config
from ...llm_connectors.rbc_openai import call_llm
from .response_settings import MAX_TOKENS, MODEL_CAPABILITY, SYSTEM_PROMPT, TEMPERATURE

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Get model configuration based on capability
model_config = get_model_config(MODEL_CAPABILITY)
MODEL_NAME = model_config["name"]
PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
COMPLETION_TOKEN_COST = model_config["completion_token_cost"]


class DirectResponseError(Exception):
    """Base exception class for direct response errors."""

    pass


def response_from_conversation(conversation, token) -> Generator[Any, None, None]:
    """
    Generate a direct response based solely on conversation context.

    Yields content chunks (str) and finally a dictionary containing usage details:
    {'usage_details': {'model': str, ...}}

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In RBC environment: OAuth token
            - In local environment: API key

    Yields:
        str: Content chunks of the response.
        dict: The final item yielded is a dictionary {'usage_details': ...}.

    Raises:
        DirectResponseError: If there is an error in generating the response.
    """
    final_usage_details = None
    try:
        # Prepare system message with response prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare messages for the API call
        messages = [system_message]
        if conversation and "messages" in conversation:
            messages.extend(conversation["messages"])

        logger.info(f"Generating direct response using model: {MODEL_NAME}")
        logger.info(
            "Initiating Direct Response stream API call"
        )  # Added contextual log

        # Make the API call with streaming
        response_stream = call_llm(
            oauth_token=token,
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True,
            prompt_token_cost=PROMPT_TOKEN_COST,
            completion_token_cost=COMPLETION_TOKEN_COST,
        )

        # Process the streaming response (which includes usage details at the end)
        for item in response_stream:
            # Check if it's the final usage dictionary
            if isinstance(item, dict) and 'usage_details' in item:
                final_usage_details = item # Capture usage details
                break # Stop iteration after getting usage details
            # Otherwise, process content chunks
            elif hasattr(item, 'choices') and item.choices and item.choices[0].delta and item.choices[0].delta.content:
                content = item.choices[0].delta.content
                yield content
            # Handle potential empty chunks or other stream elements if necessary
            # else:
            #     logger.debug("Received non-content chunk in direct response stream.")

        logger.info("Direct response stream finished.")

        # Yield the captured usage details as the final item
        if final_usage_details:
            yield final_usage_details
        else:
            # If usage details weren't found (e.g., error in stream wrapper), yield empty/error
            logger.warning("Usage details not found in direct response stream.")
            yield {'usage_details': {'error': 'Usage data missing from stream'}}


    except Exception as e:
        logger.error(f"Error generating direct response: {str(e)}", exc_info=True) # Add exc_info
        # Re-raise to signal failure upstream
        raise DirectResponseError(f"Failed to generate direct response: {str(e)}") from e
