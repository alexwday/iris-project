# python/iris/src/agents/agent_router/router_settings.py
"""
Router Agent Settings

This module defines the settings and configuration for the router agent,
including model capabilities and tool definitions.

Attributes:
    MODEL_CAPABILITY (str): The model capability to use ('small' or 'large')
    MAX_TOKENS (int): Maximum tokens for model response
    TEMPERATURE (float): Randomness parameter (0-1)
    SYSTEM_PROMPT (str): System prompt template defining the router role
    TOOL_DEFINITIONS (list): Tool definitions for router tool calling
"""

import logging
from ...global_prompts.prompt_utils import get_full_system_prompt

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Model capability - used to get specific model based on environment
MODEL_CAPABILITY = "small"

# Model settings
MAX_TOKENS = 4096
TEMPERATURE = 0.0

# Define the router agent role and task
ROUTER_ROLE = "an expert routing agent in the IRIS workflow"
ROUTER_TASK = """You are the initial step in the IRIS workflow, responsible for determining how to handle each user query.

# WORKFLOW CONTEXT
The IRIS system uses multiple specialized agents working together:
1. Router (YOU): Determine if the query needs research or can be answered directly
2. Direct Response Agent: Generate answers using only conversation context
3. Research Path:
   a. Clarifier: Determine if more context is needed or research can proceed
   b. Planner: Create database query plans for research
   c. Judge: Evaluate research progress and decide when to stop

# ANALYSIS INSTRUCTIONS
For each user query, analyze:
1. The entire conversation history
2. The latest question
3. Whether sufficient information exists in the conversation

# DECISION CRITERIA
This system relies only on conversation context, not internal training data:
- If the query is about accounting or finance topics, prefer research unless directly asked for immediate response
- Choose direct response when the conversation contains sufficient information (no research needed)
- Choose research when additional information from RBC databases is required

# DECISION OPTIONS
Choose exactly ONE option:
1. 'response_from_conversation': When conversation context is sufficient
2. 'research_from_database': When database research is necessary

# OUTPUT REQUIREMENTS
- You MUST use the provided tool only
- NO direct responses or commentary to the user
- Your purpose is ONLY to determine the next step
- ONLY make the routing decision via tool call

REMEMBER: Your response should only contain the tool call, no additional text or response to the user.
"""

# Generate system prompt with context from global_prompts
SYSTEM_PROMPT = get_full_system_prompt(
    agent_role=ROUTER_ROLE,
    agent_task=ROUTER_TASK,
    profile="router"
)

# Tool definition for routing decisions
TOOL_DEFINITIONS = [
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
                        "enum": ["response_from_conversation", "research_from_database"]
                    },
                },
                "required": ["function_name"]
            }
        }
    }
]

logger.debug("Router agent settings initialized")