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

# ANALYSIS INSTRUCTIONS
For each user query, analyze:
1. The entire conversation history
2. The latest question
3. Whether sufficient information exists in the conversation

# DECISION CRITERIA
This system relies only on conversation context, not internal training data:
- For accounting/finance topics, PREFER RESEARCH over direct response by default
- Consider research especially when:
  * Query mentions specific accounting standards (IFRS, IAS, GAAP, etc.)
  * Query mentions specific financial reporting requirements
  * Query asks about implementations, interpretations, or applications of standards
  * Query mentions or implies the need for authoritative sources
  * Query contains database specificity phrases like "check guidance", "reference", etc.
- Only choose direct response when:
  * The question is extremely basic, definitional, or conceptual without needing authoritative reference
  * The user explicitly requests a direct response using phrases like "without research", "quick answer"
  * The conversation already contains the complete information needed to answer
  * The question is about general calculations or formulas without reference to standards

# ROUTING EXAMPLES
## Examples that should route to RESEARCH:
1. "What does IFRS 15 say about revenue recognition for long-term contracts?"
   (Mentions specific accounting standard, requires authoritative reference)
   
2. "How should we account for leases under the new standards?"
   (Refers to accounting standards, requires authoritative guidance)
   
3. "What's RBC's policy on hedge accounting?"
   (Asks about specific policy that would be in the databases)
   
4. "Can you check the guidance on impairment testing for goodwill?"
   (Explicitly requests checking guidance/reference material)
   
5. "What are the disclosure requirements for related party transactions?"
   (Asks about specific requirements that need authoritative reference)

## Examples that should route to DIRECT RESPONSE:
1. "What's the difference between FIFO and LIFO inventory methods?"
   (Basic accounting concept that doesn't require specific policy reference)
   
2. "Can you quickly explain what EBITDA means?"
   (Contains "quickly explain" indicating desire for direct answer)
   
3. "Based on our previous conversation about revenue recognition, how would this apply to software sales?"
   (Builds on information already provided in conversation)
   
4. "How do I calculate the present value of future cash flows?"
   (General calculation question without reference to specific standards)
   
5. "Can you summarize what we discussed earlier about lease classifications?"
   (Explicitly asks for summary of previous conversation content)

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
    profile="router",
    agent_type="router"
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
