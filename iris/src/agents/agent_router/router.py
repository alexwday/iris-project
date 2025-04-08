# python/iris/src/agents/agent_router/router.py
"""
Router Agent Module

This module handles routing decisions for user queries by analyzing
conversation context and determining the appropriate processing path
(direct response or research).

Functions:
    get_routing_decision: Gets routing decision from the model via tool call

Dependencies:
    - json
    - logging
    - OpenAI connector for LLM calls
"""

import json
import logging

from ...chat_model.model_settings import get_model_config
from ...llm_connectors.rbc_openai import call_llm
from .router_settings import (
    MAX_TOKENS,
    MODEL_CAPABILITY,
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOOL_DEFINITIONS,
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Get model configuration based on capability
model_config = get_model_config(MODEL_CAPABILITY)
MODEL_NAME = model_config["name"]
PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
COMPLETION_TOKEN_COST = model_config["completion_token_cost"]


class RouterError(Exception):
    """Base exception class for router-related errors."""

    pass


def get_routing_decision(conversation, token):
    """
    Get routing decision from the model using a tool call.

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key

    Returns:
        dict: Routing decision with 'function_name' key

    Raises:
        RouterError: If there is an error in getting the routing decision
    """
    try:
        # Prepare system message with router prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare the messages for the API call
        messages = [system_message]
        if conversation and "messages" in conversation:
            messages.extend(conversation["messages"])

        logger.info(f"Getting routing decision using model: {MODEL_NAME}")
        logger.info("Initiating Router API call")  # Added contextual log

        # Make the API call with tool calling
        response = call_llm(
            oauth_token=token,  # Works with both OAuth token and API key
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            tools=TOOL_DEFINITIONS,
            tool_choice={
                "type": "function",
                "function": {"name": "route_query"},
            },  # Force tool call
            stream=False,
            prompt_token_cost=PROMPT_TOKEN_COST,
            completion_token_cost=COMPLETION_TOKEN_COST,
        )
        # Extract the tool call from the response
        if (
            not response.choices
            or not response.choices[0].message
            or not response.choices[0].message.tool_calls
            or not response.choices[0].message.tool_calls[0]
        ):
            raise RouterError("No tool call received in response")

        tool_call = response.choices[0].message.tool_calls[0]

        # Verify that the correct function was called
        if tool_call.function.name != "route_query":
            msg = f"Unexpected function call: {tool_call.function.name}"
            raise RouterError(msg)

        # Parse the arguments
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            err_arg = tool_call.function.arguments
            # Break long f-string assignment
            msg = f"Invalid JSON in tool arguments: {err_arg}"
            raise RouterError(msg)

        # Extract function name only
        function_name = arguments.get("function_name")

        if not function_name:
            raise RouterError("Missing 'function_name' in tool arguments")

        # Log the routing decision
        logger.info(f"Routing decision: {function_name}")

        return {"function_name": function_name}

    except Exception as e:
        logger.error(f"Error getting routing decision: {str(e)}")
        raise RouterError(f"Failed to get routing decision: {str(e)}")
