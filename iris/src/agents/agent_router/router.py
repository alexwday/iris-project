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
from typing import Tuple, Dict, Optional, Any # Added Tuple, Dict, Optional, Any

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


def get_routing_decision(conversation, token) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Get routing decision from the model using a tool call.

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In RBC environment: OAuth token
            - In local environment: API key

    Returns:
        Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
            - Routing decision dictionary with 'function_name' key.
            - Usage details dictionary for the LLM call, or None if error/not applicable.

    Raises:
        RouterError: If there is an error in getting the routing decision.
    """
    usage_details = None # Initialize usage details
    try:
        # Prepare system message with router prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare the messages for the API call
        messages = [system_message]
        if conversation and "messages" in conversation:
            messages.extend(conversation["messages"])

        logger.info(f"Getting routing decision using model: {MODEL_NAME}")
        logger.info("Initiating Router API call")

        # Make the API call with tool calling (non-streaming returns tuple)
        response, usage_details = call_llm(
            oauth_token=token,
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

        # Check if response object itself is valid before accessing attributes
        if not response or not hasattr(response, 'choices') or not response.choices:
             raise RouterError("Invalid or empty response received from LLM")

        # Extract the tool call from the response
        message = response.choices[0].message
        if not message or not message.tool_calls:
            # Handle cases where the model might return content instead of a tool call
            content_returned = message.content if message and message.content else "No content"
            logger.warning(f"Expected tool call but received content: {content_returned[:100]}...")
            # Decide on fallback behavior - perhaps default routing or raise error
            # For now, raise error as tool call is expected
            raise RouterError("No tool call received in response, content returned instead.")

        tool_call = message.tool_calls[0]

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

        # Return both decision and usage details
        return {"function_name": function_name}, usage_details

    except Exception as e:
        logger.error(f"Error getting routing decision: {str(e)}", exc_info=True) # Add exc_info
        # Return default decision and None for usage on error
        # Or re-raise, depending on desired handling in model.py
        # Re-raising seems appropriate to signal failure upstream
        raise RouterError(f"Failed to get routing decision: {str(e)}") from e
