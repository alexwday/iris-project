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


def clarify_research_needs(conversation, token):
    """
    Determine if essential context is needed or create a research statement.

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key

    Returns:
        dict: Clarifier decision with keys:
            - action: Either "request_essential_context" or "create_research_statement"
            - output: Either context questions or a research statement
            - is_continuation: Whether this is a continuation of previous research

    Raises:
        ClarifierError: If there is an error in the clarification process
    """
    try:
        # Prepare system message with clarifier prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare messages for the API call
        messages = [system_message]
        if conversation and "messages" in conversation:
            messages.extend(conversation["messages"])

        logger.info(f"Clarifying research needs using model: {MODEL_NAME}")

        # Make the API call with tool calling
        response = call_llm(
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

        # Extract the tool call from the response
        if (
            not response.choices
            or not response.choices[0].message
            or not response.choices[0].message.tool_calls
            or not response.choices[0].message.tool_calls[0]
        ):
            raise ClarifierError("No tool call received in response")

        tool_call = response.choices[0].message.tool_calls[0]

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
        is_continuation = arguments.get("is_continuation", False)

        if not action:
            raise ClarifierError("Missing 'action' in tool arguments")

        if not output:
            raise ClarifierError("Missing 'output' in tool arguments")

        # Log the clarifier decision
        logger.info(f"Clarifier decision: {action}")
        logger.info(f"Is continuation: {is_continuation}")

        return {"action": action, "output": output, "is_continuation": is_continuation}

    except Exception as e:
        logger.error(f"Error clarifying research needs: {str(e)}")
        raise ClarifierError(f"Failed to clarify research needs: {str(e)}")
