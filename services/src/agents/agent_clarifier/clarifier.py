# services/src/agents/agent_clarifier/clarifier.py
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
import os
import yaml
from typing import Tuple, Dict, Optional, Any

from ...initial_setup.env_config import config
from ...llm_connectors.rbc_openai import call_llm
from ...global_prompts.project_statement import get_project_statement
from ...global_prompts.fiscal_statement import get_fiscal_statement
from ...global_prompts.database_statement import get_database_statement
from ...global_prompts.restrictions_statement import get_restrictions_statement

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)


class ClarifierError(Exception):
    """Base exception class for clarifier-related errors."""

    pass


def get_filtered_database_statement(available_databases):
    """
    Generate a filtered database statement containing only the specified databases.

    Args:
        available_databases (dict): Dictionary of available database configurations

    Returns:
        str: Formatted database statement with only filtered databases
    """
    statement = """<AVAILABLE_DATABASES>
The following databases are available for research:

"""

    # Group databases by type for better organization
    internal_dbs = {
        k: v for k, v in available_databases.items() if k.startswith("internal_")
    }
    external_dbs = {
        k: v for k, v in available_databases.items() if k.startswith("external_")
    }

    # Add internal databases section if any exist
    if internal_dbs:
        statement += "<INTERNAL_DATABASES>\n"
        for db_name, db_info in internal_dbs.items():
            statement += f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
</DATABASE>

"""
        statement += "</INTERNAL_DATABASES>\n\n"

    # Add external databases section if any exist
    if external_dbs:
        statement += "<EXTERNAL_DATABASES>\n"
        for db_name, db_info in external_dbs.items():
            statement += f"""<DATABASE id="{db_name}">
  <NAME>{db_info['name']}</NAME>
  <DESCRIPTION>{db_info['description']}</DESCRIPTION>
</DATABASE>

"""
        statement += "</EXTERNAL_DATABASES>\n\n"

    statement += "</AVAILABLE_DATABASES>"
    return statement


def load_agent_config(available_databases=None):
    """
    Load agent configuration from YAML file and resolve dynamic context.
    NOTE: Clarifier can optionally use available_databases for filtered database_statement

    Args:
        available_databases (dict, optional): Dictionary of available database configurations

    Returns:
        dict: Configuration dictionary with resolved system prompt and settings
    """
    try:
        # Build context statements dynamically
        context_parts = [get_project_statement(), get_fiscal_statement()]

        # Handle database statement - use filtered version if available_databases provided
        if available_databases is not None:
            context_parts.append(get_filtered_database_statement(available_databases))
        else:
            context_parts.append(get_database_statement())

        context_parts.append(get_restrictions_statement())

        # Build the complete context block
        context_block = "\n\n".join(context_parts)

        # Read and parse the YAML file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, "clarifier_prompt.yaml")

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        # Extract model configuration from YAML
        model_config = yaml_config.get("model", {})
        capability = model_config.get("capability", "large")  # Default fallback
        max_tokens = model_config.get("max_tokens", 4096)
        temperature = model_config.get("temperature", 0.0)

        # Extract system prompt from YAML
        system_prompt = yaml_config.get("system_prompt", "")
        if not system_prompt:
            raise Exception("No system_prompt found in YAML configuration")

        # Replace the context placeholder
        system_prompt = system_prompt.replace(
            "{{CONTEXT_START}}", f"<CONTEXT>\n{context_block}\n</CONTEXT>"
        )

        # Define tools (hardcoded for simplicity)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "make_clarifier_decision",
                    "description": (
                        "Decide whether to request essential context or create a research statement. "
                        "Optionally flags accounting queries to trigger user confirmation for external source inclusion."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "The chosen action based on conversation analysis.",
                                "enum": [
                                    "request_essential_context",
                                    "create_research_statement",
                                ],
                            },
                            "output": {
                                "type": "string",
                                "description": (
                                    "Either a list of context questions (numbered) or "
                                    "a research statement."
                                ),
                            },
                            "scope": {
                                "type": "string",
                                "description": "The determined scope of the user's request ('metadata' for catalog lookup, 'research' for content analysis). Required if action is 'create_research_statement'.",
                                "enum": ["metadata", "research"],
                            },
                        },
                        "required": [
                            "action",
                            "output",
                        ],  # Scope is conditionally required, handled in clarifier.py
                    },
                },
            }
        ]

        return {
            "model_capability": capability,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system_prompt": system_prompt,
            "tool_definitions": tools,
        }

    except Exception as e:
        logger.error(f"Error loading agent configuration: {str(e)}", exc_info=True)
        raise ClarifierError(f"Failed to load agent configuration: {str(e)}") from e


# Load configuration once at module level
try:
    _config = load_agent_config()
    MODEL_CAPABILITY = _config["model_capability"]
    MAX_TOKENS = _config["max_tokens"]
    TEMPERATURE = _config["temperature"]
    SYSTEM_PROMPT = _config["system_prompt"]
    TOOL_DEFINITIONS = _config["tool_definitions"]

    # Get model configuration based on capability
    model_config = config.get_model_config(MODEL_CAPABILITY)
    MODEL_NAME = model_config["name"]
    PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
    COMPLETION_TOKEN_COST = model_config["completion_token_cost"]


except Exception as e:
    logger.error(
        f"Failed to initialize clarifier agent from YAML: {str(e)}", exc_info=True
    )
    raise


def clarify_research_needs(
    conversation, token, available_databases=None
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Determine if essential context is needed or create a research statement.

    Args:
        conversation (dict): Conversation with 'messages' key
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key
        available_databases (dict, optional): Dictionary of available database configurations (filtered by user selection)

    Returns:
        Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
            - Clarifier decision dictionary.
            - Usage details dictionary for the LLM call, or None if error.

    Raises:
        ClarifierError: If there is an error in the clarification process.
    """
    usage_details = None  # Initialize usage details
    try:
        # Generate dynamic configuration with filtered databases if provided
        if available_databases is not None:
            agent_config = load_agent_config(available_databases)
            system_prompt = agent_config["system_prompt"]
        else:
            system_prompt = SYSTEM_PROMPT

        # Prepare system message with clarifier prompt
        system_message = {"role": "system", "content": system_prompt}

        # Prepare messages for the API call
        messages = [system_message]
        if conversation and "messages" in conversation:
            messages.extend(conversation["messages"])

        logger.debug(f"Clarifying research needs using model: {MODEL_NAME}")

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
        if not response or not hasattr(response, "choices") or not response.choices:
            raise ClarifierError("Invalid or empty response received from LLM")

        # Extract the tool call from the response
        message = response.choices[0].message
        if not message or not message.tool_calls:
            content_returned = (
                message.content if message and message.content else "No content"
            )
            logger.warning(
                f"Expected tool call but received content: {content_returned[:100]}..."
            )
            raise ClarifierError(
                "No tool call received in response, content returned instead."
            )

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

        logger.debug(f"Clarifier decision: {action}")
        if action == "create_research_statement":
            logger.debug(f"Determined scope: {scope}")

        # Construct the decision dictionary
        decision = {
            "action": action,
            "output": output,
            "scope": scope,
        }

        # Return both decision and usage details
        return decision, usage_details

    except Exception as e:
        logger.error(
            f"Error clarifying research needs: {str(e)}", exc_info=True
        )  # Add exc_info
        # Re-raise to signal failure upstream
        raise ClarifierError(f"Failed to clarify research needs: {str(e)}") from e
