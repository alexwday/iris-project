# python/iris/src/agents/agent_planner/planner.py
"""
Planner Agent Module

This module handles the creation of database research query plans based on
research statements from the clarifier. It determines which databases to query
and what specific queries to run.

Functions:
    create_query_plan: Creates a plan of database queries based on a research statement

Dependencies:
    - json
    - logging
    - OpenAI connector for LLM calls
"""

import json
import logging

from ...chat_model.model_settings import get_model_config
from ...llm_connectors.rbc_openai import call_llm
from .planner_settings import (
    AVAILABLE_DATABASES,
    MAX_TOKENS,
    MODEL_CAPABILITY,
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOOL_DEFINITIONS,
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Extract the new tool name from settings for clarity
PLANNER_TOOL_NAME = TOOL_DEFINITIONS[0]["function"]["name"]

# Get model configuration based on capability
model_config = get_model_config(MODEL_CAPABILITY)
MODEL_NAME = model_config["name"]
PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
COMPLETION_TOKEN_COST = model_config["completion_token_cost"]


class PlannerError(Exception):
    """Base exception class for planner-related errors."""

    pass


def create_database_selection_plan(research_statement, token, is_continuation=False):
    """
    Create a plan of selected databases based on a research statement.

    Args:
        research_statement (str): The research statement from the clarifier
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key
        is_continuation (bool, optional): Whether this is a continuation of previous research

    Returns:
        dict: Database selection plan with keys:
            - databases: List of selected database names (strings)

    Raises:
        PlannerError: If there is an error in creating the database selection plan
    """
    try:
        # Prepare system message with planner prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}

        # Prepare the research statement as user message
        continuation_prefix = "[CONTINUATION REQUEST] " if is_continuation else ""
        research_message = {
            "role": "user",
            "content": f"{continuation_prefix}Research Statement: {research_statement}",
        }

        # Prepare messages for the API call
        messages = [system_message, research_message]

        # Database information is included in the SYSTEM_PROMPT

        logger.info(f"Creating database selection plan using model: {MODEL_NAME}")
        logger.info(f"Is continuation: {is_continuation}")
        logger.info("Initiating Planner API call for database selection")

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
                "function": {"name": PLANNER_TOOL_NAME},
            },  # Use new tool name
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
            raise PlannerError("No tool call received in response")

        tool_call = response.choices[0].message.tool_calls[0]

        # Verify that the correct function was called
        if tool_call.function.name != PLANNER_TOOL_NAME:
            raise PlannerError(f"Unexpected function call: {tool_call.function.name}")

        # Parse the arguments
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            raise PlannerError(
                f"Invalid JSON in tool arguments: {tool_call.function.arguments}"
            )

        # Extract selected databases
        selected_databases = arguments.get("databases", [])

        if not selected_databases:
            raise PlannerError("Missing or empty 'databases' in tool arguments")

        # Validate selected databases
        validated_databases = []
        for i, db_name in enumerate(selected_databases):
            if not isinstance(db_name, str):
                raise PlannerError(f"Database entry {i+1} is not a string: {db_name}")
            if db_name not in AVAILABLE_DATABASES:
                raise PlannerError(f"Selected database {i+1} is unknown: {db_name}")
            validated_databases.append(db_name)

        # Log the database selection plan
        logger.info(
            f"Database selection plan created with {len(validated_databases)} databases: {validated_databases}"
        )

        return {"databases": validated_databases}

    except Exception as e:
        logger.error(f"Error creating database selection plan: {str(e)}")
        raise PlannerError(f"Failed to create database selection plan: {str(e)}")
