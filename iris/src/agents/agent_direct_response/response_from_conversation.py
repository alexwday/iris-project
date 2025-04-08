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


def response_from_conversation(conversation, token):
    """
    Generate a direct response based solely on conversation context.

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key

    Returns:
        generator: Stream of response chunks for real-time display

    Raises:
        DirectResponseError: If there is an error in generating the response
    """
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

        # Process the streaming response
        for chunk in response_stream:
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                content = chunk.choices[0].delta.content
                yield content

        logger.info("Direct response generation complete")

    except Exception as e:
        logger.error(f"Error generating direct response: {str(e)}")
        raise DirectResponseError(f"Failed to generate direct response: {str(e)}")
