# python/iris/src/agents/agent_router/router.py
"""
Router Agent Module

This module handles routing decisions for user queries by analyzing
conversation context and determining the appropriate processing path
(direct response or research).

Functions:
    load_agent_config: Loads configuration from YAML file and resolves dynamic context
    get_routing_decision: Gets routing decision from the model via tool call

Dependencies:
    - json
    - logging
    - OpenAI connector for LLM calls
"""

import json
import logging
import os
from typing import Tuple, Dict, Optional, Any

from ...initial_setup.env_config import config
from ...llm_connectors.rbc_openai import call_llm
from ...global_prompts.project_statement import get_project_statement
from ...global_prompts.fiscal_statement import get_fiscal_statement
from ...global_prompts.database_statement import get_database_statement
from ...global_prompts.restrictions_statement import get_restrictions_statement

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)


class RouterError(Exception):
    """Base exception class for router-related errors."""
    pass


def load_agent_config():
    """
    Load agent configuration from YAML file and resolve dynamic context.
    
    Returns:
        dict: Configuration dictionary with resolved system prompt and settings
    """
    try:
        # Build context statements dynamically
        context_parts = [
            get_project_statement(),
            get_fiscal_statement(), 
            get_database_statement(),
            get_restrictions_statement()
        ]
        
        # Build the complete context block
        context_block = "\n\n".join(context_parts)
        
        # Read the system prompt template from YAML file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_path = os.path.join(current_dir, 'router_prompt.yaml')
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the system prompt (everything between system_prompt: | and # Tool definitions)
        start_marker = "system_prompt: |"
        end_marker = "# Tool definitions"
        
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            raise Exception("Could not find system prompt in YAML file")
        
        # Extract and clean the system prompt
        system_prompt = content[start_idx + len(start_marker):end_idx].strip()
        
        # Replace the context placeholder
        system_prompt = system_prompt.replace('{{CONTEXT_START}}', f"<CONTEXT>\n{context_block}\n</CONTEXT>")
        
        # Define tools (hardcoded for simplicity)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "route_query",
                    "description": "Route the user query to the appropriate function based on conversation analysis",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "function_name": {
                                "type": "string",
                                "description": "The function to route to based on conversation context analysis",
                                "enum": [
                                    "response_from_conversation",
                                    "research_from_database",
                                ],
                            },
                        },
                        "required": ["function_name"],
                    },
                },
            }
        ]
        
        return {
            'model_capability': 'small',
            'max_tokens': 4096,
            'temperature': 0.0,
            'system_prompt': system_prompt,
            'tool_definitions': tools
        }
        
    except Exception as e:
        logger.error(f"Error loading agent configuration: {str(e)}", exc_info=True)
        raise RouterError(f"Failed to load agent configuration: {str(e)}") from e


# Load configuration once at module level
try:
    _config = load_agent_config()
    MODEL_CAPABILITY = _config['model_capability']
    MAX_TOKENS = _config['max_tokens']
    TEMPERATURE = _config['temperature']
    SYSTEM_PROMPT = _config['system_prompt']
    TOOL_DEFINITIONS = _config['tool_definitions']
    
    # Get model configuration based on capability
    model_config = config.get_model_config(MODEL_CAPABILITY)
    MODEL_NAME = model_config["name"]
    PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
    COMPLETION_TOKEN_COST = model_config["completion_token_cost"]
    
    logger.debug("Router agent configuration loaded from YAML successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize router agent from YAML: {str(e)}", exc_info=True)
    # Fallback to original settings if YAML loading fails
    try:
        from .router_settings import (
            MAX_TOKENS,
            MODEL_CAPABILITY,
            SYSTEM_PROMPT,
            TEMPERATURE,
            TOOL_DEFINITIONS,
        )
        model_config = config.get_model_config(MODEL_CAPABILITY)
        MODEL_NAME = model_config["name"]
        PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
        COMPLETION_TOKEN_COST = model_config["completion_token_cost"]
        logger.warning("Fell back to original router_settings.py due to YAML loading error")
    except Exception as fallback_error:
        logger.error(f"Failed to load fallback settings: {str(fallback_error)}", exc_info=True)
        raise


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
