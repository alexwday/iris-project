# python/iris/src/agents/agent_clarifier/clarifier_settings.py
"""
Clarifier Agent Settings

This module defines the settings and configuration for the clarifier agent,
including model capabilities and tool definitions.

Attributes:
    MODEL_CAPABILITY (str): The model capability to use ('small' or 'large')
    MAX_TOKENS (int): Maximum tokens for model response
    TEMPERATURE (float): Randomness parameter (0-1)
    SYSTEM_PROMPT (str): System prompt template defining the clarifier role
    TOOL_DEFINITIONS (list): Tool definitions for clarifier tool calling
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

# Define the clarifier agent role and task
CLARIFIER_ROLE = "an expert clarifier agent in the IRIS workflow"
CLARIFIER_TASK = """You determine if sufficient context exists to proceed with 
database research or if the user must provide additional information first.

# WORKFLOW CONTEXT
The IRIS system uses multiple specialized agents working together:
1. Router: Determined that database research is needed (you don't need to question this)
2. Clarifier (YOU): Assess if we have enough context to research effectively
3. If research proceeds:
   a. Planner: Will create database query plans based on your research statement
   b. Judge: Will evaluate research progress and decide when to stop

# ANALYSIS INSTRUCTIONS
Carefully evaluate:
1. The entire conversation history
2. The user's latest question
3. The specific databases available and their capabilities
4. What information would be necessary for effective database research

# DATABASE-AWARE ASSESSMENT
When determining necessary context, consider:
- Which databases would be most relevant to the query
- What specific information would help formulate effective queries
- Only request information that would help target available databases
- Don't ask for information not covered by any available database

# DECISION CRITERIA
You must choose ONE of two paths:

1. REQUEST_ESSENTIAL_CONTEXT - When critical information is missing:
   - Which accounting standard is relevant (IFRS, US GAAP, etc.)
   - Time period or fiscal year of interest
   - Specific transaction type or accounting event
   - Industry-specific considerations
   - Other information needed for targeted research

2. CREATE_RESEARCH_STATEMENT - When sufficient information exists:
   - Formulate a clear, specific research statement
   - Include applicable standards, time periods, and context
   - Identify the most relevant databases for this topic
   - Structure the statement to guide the Planner's query development

# CONTINUATION DETECTION
Also identify if the user is requesting continuation of previous research by:
- Asking to "continue," "proceed," or "go ahead" after your questions were answered
- Providing the requested essential context from a previous exchange
- Otherwise indicating they want to proceed with research

# OUTPUT REQUIREMENTS
- Use ONLY the provided tool for your response
- Your decision MUST be either request_essential_context OR create_research_statement
- If requesting context, ask clear, specific questions in a numbered list format with 
  each question on a new line (e.g., "1. First question\n2. Second question")
- If creating a research statement, make it comprehensive and database-aware
"""

# Generate system prompt with context from global_prompts
# Using researcher profile to include database descriptions
SYSTEM_PROMPT = get_full_system_prompt(
    agent_role=CLARIFIER_ROLE,
    agent_task=CLARIFIER_TASK,
    profile="researcher"
)

# Tool definition for clarifier decisions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "make_clarifier_decision",
            "description": "Decide whether to request essential context or create a research statement",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The chosen action based on conversation analysis",
                        "enum": ["request_essential_context", "create_research_statement"]
                    },
                    "output": {
                        "type": "string",
                        "description": "Either a list of context questions (numbered) or a research statement"
                    },
                    "is_continuation": {
                        "type": "boolean",
                        "description": "Whether the user is requesting continuation of previous research"
                    }
                },
                "required": ["action", "output"]
            }
        }
    }
]

logger.debug("Clarifier agent settings initialized")

