# services/src/agents/agent_planner/planner.py
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

# Tool name constant
PLANNER_TOOL_NAME = "select_databases"


class PlannerError(Exception):
    """Base exception class for planner-related errors."""

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
  <CONTENT_TYPE>{db_info['content_type']}</CONTENT_TYPE>
  <QUERY_TYPE>{db_info['query_type']}</QUERY_TYPE>
  <USAGE>{db_info['use_when']}</USAGE>
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
  <CONTENT_TYPE>{db_info['content_type']}</CONTENT_TYPE>
  <QUERY_TYPE>{db_info['query_type']}</QUERY_TYPE>
  <USAGE>{db_info['use_when']}</USAGE>
</DATABASE>

"""
        statement += "</EXTERNAL_DATABASES>\n\n"

    statement += "</AVAILABLE_DATABASES>"
    return statement


def get_tool_definitions(available_databases):
    """
    Generate tool definitions with dynamic database enum based on available databases.

    Args:
        available_databases (dict): Dictionary of available database configurations

    Returns:
        list: Tool definitions for the planner agent
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "select_databases",
                "description": "Submit a plan of selected databases based on the research statement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "databases": {
                            "type": "array",
                            "description": "The list of database names to query using the full research statement.",
                            "items": {
                                "type": "string",
                                "description": "The name of the database to query.",
                                "enum": list(
                                    available_databases.keys()
                                ),  # Dynamic enum
                            },
                            "minItems": 1,
                            "maxItems": 5,
                        }
                    },
                    "required": ["databases"],
                },
            },
        }
    ]


def load_agent_config(available_databases=None):
    """
    Load agent configuration from YAML file and resolve dynamic context.
    NOTE: Planner requires available_databases for filtered database_statement and dynamic tools

    Args:
        available_databases (dict): Dictionary of available database configurations

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
        yaml_path = os.path.join(current_dir, "planner_prompt.yaml")

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

        # Generate dynamic tools if available_databases provided
        if available_databases is not None:
            tools = get_tool_definitions(available_databases)
        else:
            # Fallback to basic tool structure
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "select_databases",
                        "description": "Submit a plan of selected databases based on the research statement.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "databases": {
                                    "type": "array",
                                    "description": "The list of database names to query using the full research statement.",
                                    "items": {
                                        "type": "string",
                                        "description": "The name of the database to query.",
                                    },
                                    "minItems": 1,
                                    "maxItems": 5,
                                }
                            },
                            "required": ["databases"],
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
        raise PlannerError(f"Failed to load agent configuration: {str(e)}") from e


# Module-level configuration variables (will be set by the functions that call the planner)
MODEL_CAPABILITY = "small"
MAX_TOKENS = 4096
TEMPERATURE = 0.0

# Get model configuration based on capability
model_config = config.get_model_config(MODEL_CAPABILITY)
MODEL_NAME = model_config["name"]
PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
COMPLETION_TOKEN_COST = model_config["completion_token_cost"]


def create_database_selection_plan(
    research_statement, token, available_databases, is_continuation=False, apg_catalog_context=None
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Create a plan of selected databases based on a research statement.

    Args:
        research_statement (str): The research statement from the clarifier
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key
        available_databases (dict): Dictionary of available database configurations (filtered by user selection)
        is_continuation (bool, optional): Whether this is a continuation of previous research.
        apg_catalog_context (list, optional): List of relevant documents from apg_catalog search

    Returns:
        Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
            - Database selection plan dictionary.
            - Usage details dictionary for the LLM call, or None if error.

    Raises:
        PlannerError: If there is an error in creating the database selection plan.
    """
    usage_details = None  # Initialize usage details
    try:
        # Generate dynamic configuration with filtered databases
        agent_config = load_agent_config(available_databases)
        system_prompt = agent_config["system_prompt"]
        tool_definitions = agent_config["tool_definitions"]
        system_message = {"role": "system", "content": system_prompt}

        # Prepare the research statement as user message
        continuation_prefix = "[CONTINUATION REQUEST] " if is_continuation else ""
        user_content = f"{continuation_prefix}Research Statement: {research_statement}"
        
        # Add apg_catalog context if available
        if apg_catalog_context and len(apg_catalog_context) > 0:
            user_content += "\n\n<RELEVANT_DOCUMENTS_CONTEXT>\n"
            user_content += "The following documents were found to be relevant to this research statement:\n\n"
            for i, doc in enumerate(apg_catalog_context[:5], 1):
                user_content += f"{i}. **{doc.get('document_source', 'Unknown Source')}**\n"
                user_content += f"   Description: {doc.get('document_description', 'No description available')}\n"
                user_content += f"   Similarity: {doc.get('similarity_score', 0.0):.3f}\n\n"
            user_content += "</RELEVANT_DOCUMENTS_CONTEXT>\n"
        
        research_message = {
            "role": "user",
            "content": user_content,
        }

        # Prepare messages for the API call
        messages = [system_message, research_message]

        # Database information is included in the SYSTEM_PROMPT

        logger.debug(f"Creating database selection plan using model: {MODEL_NAME}")
        logger.debug(f"Is continuation: {is_continuation}")
        logger.debug(f"Available databases: {list(available_databases.keys())}")

        # Tool definitions already loaded from agent_config above

        # Make the API call with tool calling (non-streaming returns tuple)
        response, usage_details = call_llm(
            oauth_token=token,
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            tools=tool_definitions,
            tool_choice={
                "type": "function",
                "function": {"name": PLANNER_TOOL_NAME},
            },  # Use new tool name
            stream=False,
            prompt_token_cost=PROMPT_TOKEN_COST,
            completion_token_cost=COMPLETION_TOKEN_COST,
        )

        # Check if response object itself is valid before accessing attributes
        if not response or not hasattr(response, "choices") or not response.choices:
            raise PlannerError("Invalid or empty response received from LLM")

        # Extract the tool call from the response
        message = response.choices[0].message
        if not message or not message.tool_calls:
            content_returned = (
                message.content if message and message.content else "No content"
            )
            logger.warning(
                f"Expected tool call but received content: {content_returned[:100]}..."
            )
            raise PlannerError(
                "No tool call received in response, content returned instead."
            )

        tool_call = message.tool_calls[0]

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
            if db_name not in available_databases:
                raise PlannerError(f"Selected database {i+1} is unknown: {db_name}")
            validated_databases.append(db_name)

        logger.debug(
            f"Database selection plan created with {len(validated_databases)} databases: {validated_databases}"
        )

        # Return both plan and usage details
        return {"databases": validated_databases}, usage_details

    except Exception as e:
        logger.error(
            f"Error creating database selection plan: {str(e)}", exc_info=True
        )  # Add exc_info
        # Re-raise to signal failure upstream
        raise PlannerError(f"Failed to create database selection plan: {str(e)}") from e
