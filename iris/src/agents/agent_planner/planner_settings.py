# python/iris/src/agents/agent_planner/planner_settings.py
"""
Planner Agent Settings

This module defines the settings and configuration for the planner agent,
including model capabilities and tool definitions.

Attributes:
    MODEL_CAPABILITY (str): The model capability to use ('small' or 'large')
    MAX_TOKENS (int): Maximum tokens for model response
    TEMPERATURE (float): Randomness parameter (0-1)
    SYSTEM_PROMPT (str): System prompt template defining the planner role
    TOOL_DEFINITIONS (list): Tool definitions for planner tool calling
    AVAILABLE_DATABASES (dict): Information about available databases
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

# Import database configuration from global prompts
from ...global_prompts.database_statement import get_available_databases

AVAILABLE_DATABASES = get_available_databases()

# Define the planner agent role and task
PLANNER_ROLE = "an expert query planning agent in the IRIS workflow"
PLANNER_TASK = """You create strategic database query plans to efficiently research accounting topics.

# ANALYSIS INSTRUCTIONS
For each research statement:
1. Analyze the core accounting question and information needs **as defined in the research statement**.
2. Identify which databases contain the most relevant information based on the statement's scope.
3. **Scale the number of queries (1-5) based on the complexity of the research statement.** Simple requests (e.g., definition of a single term) may only require 1-2 queries to authoritative sources. Complex requests involving multiple facets, comparisons, or specific scenarios may require more queries across different tiers.
4. Create specific, targeted queries optimized for each chosen database.
5. Develop a comprehensive, multi-source research strategy appropriate for the statement's complexity, referencing the database details provided in the CONTEXT section for strategic guidance.

# QUERY FORMULATION GUIDELINES
For each database query:
1. Match query terminology to the database's domain and content type
2. Use technical accounting terms and standard numbers (e.g., IFRS 9, IAS 38)
3. Create concise, focused queries rather than compound questions
4. Consider each database's search method (semantic vs. keyword)
5. Format queries clearly and professionally as they will be displayed to users in titles
6. Keep queries concise (under 100 characters if possible) for better display in headers
7. Use proper capitalization and punctuation in queries

# CONTINUATION HANDLING
If this is a continuation of previous research:
- Focus on gaps identified in previous results
- Avoid duplicating previously executed queries
- Target areas where deeper information is needed
- Build upon insights from earlier query results

# OUTPUT REQUIREMENTS
- Submit your query plan using ONLY the provided tool.
- **Create 1-5 queries, scaling the number based on the research statement's complexity.** A simple definition might need only 1 query; a complex comparison might need 3-5. Do not create unnecessary queries.
- Each query must include a specific database and query text.
- Queries should work together as a cohesive research plan.


# WORKFLOW & ROLE SUMMARY
- You are the PLANNER, following the Clarifier in the research path.
- Input: Research statement from Clarifier, database info, continuation status.
- Task: Design an optimal query plan (1-5 queries) targeting relevant databases.
- Impact: Your plan determines the queries executed and evaluated by the Judge. Quality of results depends on your plan.

# I/O SPECIFICATIONS (Tool Call Only)
- Input: Research statement, DB info, continuation status.
- Validation: Understand need? Identify topics/standards? Determine relevant DBs?
- Output: `submit_query_plan` tool call (`queries`: array of {database, query}).
- Validation: Queries optimized? DBs prioritized? Logical progression? No duplicate queries on continuation?

# ERROR HANDLING SUMMARY
- General: Handle unexpected input, ambiguity (choose likely, state assumption), missing info (assume reasonably, state assumption), limitations (acknowledge). Use confidence signaling.
- Planner Specific: Vague statement -> query likely interpretations. Unsure DBs -> include broader range. Multiple standards -> query each. Missing continuation info -> avoid duplicating likely previous queries.
"""

# Generate system prompt with context from global_prompts
# Now uses the simplified get_full_system_prompt which includes global context by default
SYSTEM_PROMPT = get_full_system_prompt(agent_role=PLANNER_ROLE, agent_task=PLANNER_TASK)

# Tool definition for query planning
# Create query plan tool with database enum from central config
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "submit_query_plan",
            "description": "Submit a plan of database queries based on the research statement",
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "description": "The list of queries to execute",
                        "items": {
                            "type": "object",
                            "properties": {
                                "database": {
                                    "type": "string",
                                    "description": "The database to query",
                                    "enum": list(AVAILABLE_DATABASES.keys()),
                                },
                                "query": {
                                    "type": "string",
                                    "description": "The search query text",
                                },
                            },
                            "required": ["database", "query"],
                        },
                    }
                },
                "required": ["queries"],
            },
        },
    }
]

logger.debug("Planner agent settings initialized")
