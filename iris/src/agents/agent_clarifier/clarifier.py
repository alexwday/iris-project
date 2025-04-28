# python/iris/src/agents/agent_clarifier/clarifier.py
"""
Clarifier Agent Module

This module handles context assessment to determine if research can proceed or
if essential context is missing and must be requested from the user.

Functions:
    clarify_research_needs: Determines if essential context is needed
                            or if research can proceed

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
from .clarifier_settings import (
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


class ClarifierError(Exception):
    """Base exception class for clarifier-related errors."""
    pass


def clarify_research_needs(conversation, token) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Determine if essential context is needed or create a research statement.

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key

    Returns:
        Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
            - Clarifier decision dictionary.
            - Usage details dictionary for the LLM call, or None if error.

    Raises:
        ClarifierError: If there is an error in the clarification process.
    """
    usage_details = None # Initialize usage details
    try:
        # Prepare system message with clarifier prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare messages for the API call
        messages = [system_message]
        if conversation and "messages" in conversation:
            messages.extend(conversation["messages"])

        logger.info(f"Clarifying research needs using model: {MODEL_NAME}")
        logger.info("Initiating Clarifier API call")

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
                "function": {"name": "make_clarifier_decision"},
            },
            stream=False,
            prompt_token_cost=PROMPT_TOKEN_COST,
            completion_token_cost=COMPLETION_TOKEN_COST,
        )

        # Check if response object itself is valid before accessing attributes
        if not response or not hasattr(response, 'choices') or not response.choices:
             raise ClarifierError("Invalid or empty response received from LLM")

        # Extract the tool call from the response
        message = response.choices[0].message
        if not message or not message.tool_calls:
            content_returned = message.content if message and message.content else "No content"
            logger.warning(f"Expected tool call but received content: {content_returned[:100]}...")
            raise ClarifierError("No tool call received in response, content returned instead.")

        tool_call = message.tool_calls[0]

        # Verify that the correct function was called
        if tool_call.function.name != "make_clarifier_decision":
            raise ClarifierError(f"Unexpected function call: {tool_call.function.name}")

        # Parse the arguments
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            raise ClarifierError(
                f"Invalid JSON in tool arguments: {tool_call.function.arguments}"
            )

        # Extract decision fields
        action = arguments.get("action")
        output = arguments.get("output")
        scope = arguments.get("scope")  # Extract the new scope field
        is_continuation = arguments.get("is_continuation", False)

        if not action:
            raise ClarifierError("Missing 'action' in tool arguments")

        if not output:
            raise ClarifierError("Missing 'output' in tool arguments")

        # Validate scope: required only when creating a research statement
        if action == "create_research_statement":
            if not scope:
                raise ClarifierError(
                    "Missing 'scope' in tool arguments when action is 'create_research_statement'"
                )
            if scope not in ["metadata", "research"]:
                raise ClarifierError(
                    f"Invalid 'scope' value: {scope}. Must be 'metadata' or 'research'."
                )
        elif scope:
            # Scope should not be provided if action is request_essential_context
            logger.warning(
                f"Scope '{scope}' provided but action is '{action}'. Scope will be ignored."
            )
            scope = None  # Ensure scope is None if not applicable

        # Log the clarifier decision
        logger.info(f"Clarifier decision: {action}")
        if action == "create_research_statement":
            logger.info(f"Determined scope: {scope}")
        logger.info(f"Is continuation: {is_continuation}")

        # Construct the decision dictionary
        decision = {
            "action": action,
            "output": output,
            "scope": scope,
            "is_continuation": is_continuation,
        }

        # Return both decision and usage details
        return decision, usage_details

    except Exception as e:
        logger.error(f"Error clarifying research needs: {str(e)}", exc_info=True) # Add exc_info
        # Re-raise to signal failure upstream
        raise ClarifierError(f"Failed to clarify research needs: {str(e)}") from e
