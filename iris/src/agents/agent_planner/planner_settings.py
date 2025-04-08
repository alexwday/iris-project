# python/iris/src/agents/agent_planner/planner_settings.py
"""
Planner Agent Settings

This module defines the settings and configuration for the planner agent,
including model capabilities and tool definitions.

This version implements advanced prompt engineering techniques:
1. CO-STAR framework (Context, Objective, Style, Tone, Audience, Response)
2. Sectioning with XML-style delimiters
3. Enhanced LLM guardrails
4. Pattern recognition instructions

Attributes:
    MODEL_CAPABILITY (str): The model capability to use ('small' or 'large')
    MAX_TOKENS (int): Maximum tokens for model response
    TEMPERATURE (float): Randomness parameter (0-1)
    SYSTEM_PROMPT (str): System prompt template defining the planner role
    TOOL_DEFINITIONS (list): Tool definitions for planner tool calling
    AVAILABLE_DATABASES (dict): Information about available databases
"""

import logging

from ...global_prompts.project_statement import get_project_statement
from ...global_prompts.database_statement import (
    get_database_statement,
    get_available_databases,
)
from ...global_prompts.fiscal_calendar import get_fiscal_statement
from ...global_prompts.restrictions_statement import get_restrictions_statement

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Model capability - used to get specific model based on environment
MODEL_CAPABILITY = "small"

# Model settings
MAX_TOKENS = 4096
TEMPERATURE = 0.0

# Import database configuration from global prompts
AVAILABLE_DATABASES = get_available_databases()

# Define the planner agent role and task
PLANNER_ROLE = "an expert query planning agent in the IRIS workflow"

# CO-STAR Framework Components
PLANNER_OBJECTIVE = """
To create strategic database query plans that efficiently research accounting topics.
Your objective is to:
1. Analyze the research statement to identify key accounting concepts and information needs
2. Select the most relevant databases based on the research statement's scope
3. Create targeted, optimized queries for each selected database
4. Scale the number of queries (1-5) based on the complexity of the research statement
5. Develop a comprehensive, multi-source research strategy
"""

PLANNER_STYLE = """
Strategic and methodical like an expert research librarian.
Focus on efficient, targeted query design that maximizes information retrieval.
Be comprehensive in your analysis but precise in your query formulation.
"""

PLANNER_TONE = """
Professional and technical.
Focused on accuracy and efficiency in query design.
Deliberate and thoughtful in database selection.
"""

PLANNER_AUDIENCE = """
Internal system components that will execute your query plan.
Your queries will be displayed to users in titles, so they should be clear and professional.
The quality of research results depends directly on your query plan.
"""

# Define the planner agent task
PLANNER_TASK = """<TASK>
You create strategic database query plans to efficiently research accounting topics.

<ANALYSIS_INSTRUCTIONS>
For each research statement:
1. Analyze the core accounting question and information needs **as defined in the research statement**.
2. Identify which databases contain the most relevant information based on the statement's scope.
3. **Scale the number of queries (1-5) based on the complexity of the research statement.** Simple requests (e.g., definition of a single term) may only require 1-2 queries to authoritative sources. Complex requests involving multiple facets, comparisons, or specific scenarios may require more queries across different tiers.
4. Create specific, targeted queries optimized for each chosen database.
5. Develop a comprehensive, multi-source research strategy appropriate for the statement's complexity, referencing the database details provided in the CONTEXT section for strategic guidance.
</ANALYSIS_INSTRUCTIONS>

<QUERY_FORMULATION_GUIDELINES>
For each database query:
1. Match query terminology to the database's domain and content type
2. Use technical accounting terms and standard numbers (e.g., IFRS 9, IAS 38)
3. Create concise, focused queries rather than compound questions
4. Consider each database's search method (semantic vs. keyword)
5. Format queries clearly and professionally as they will be displayed to users in titles
6. Keep queries concise (under 100 characters if possible) for better display in headers
7. Use proper capitalization and punctuation in queries
</QUERY_FORMULATION_GUIDELINES>

<CONTINUATION_HANDLING>
If this is a continuation of previous research:
- Focus on gaps identified in previous results
- Avoid duplicating previously executed queries
- Target areas where deeper information is needed
- Build upon insights from earlier query results
</CONTINUATION_HANDLING>

<OUTPUT_REQUIREMENTS>
- Submit your query plan using ONLY the provided tool.
- **Create 1-5 queries, scaling the number based on the research statement's complexity.** A simple definition might need only 1 query; a complex comparison might need 3-5. Do not create unnecessary queries.
- Each query must include a specific database and query text.
- Queries should work together as a cohesive research plan.
</OUTPUT_REQUIREMENTS>

<WORKFLOW_SUMMARY>
- You are the PLANNER, following the Clarifier in the research path.
- Input: Research statement from Clarifier, database info, continuation status.
- Task: Design an optimal query plan (1-5 queries) targeting relevant databases.
- Impact: Your plan determines the queries executed and evaluated by the Judge. Quality of results depends on your plan.
</WORKFLOW_SUMMARY>

<IO_SPECIFICATIONS>
- Input: Research statement, DB info, continuation status.
- Validation: Understand need? Identify topics/standards? Determine relevant DBs?
- Output: `submit_query_plan` tool call (`queries`: array of {database, query}).
- Validation: Queries optimized? DBs prioritized? Logical progression? No duplicate queries on continuation?
</IO_SPECIFICATIONS>

<ERROR_HANDLING>
- General: Handle unexpected input, ambiguity (choose likely, state assumption), missing info (assume reasonably, state assumption), limitations (acknowledge). Use confidence signaling.
- Planner Specific: Vague statement -> query likely interpretations. Unsure DBs -> include broader range. Multiple standards -> query each. Missing continuation info -> avoid duplicating likely previous queries.
</ERROR_HANDLING>
</TASK>

<RESPONSE_FORMAT>
Your response must be a tool call to submit_query_plan with:
- queries: An array of 1-5 database queries, each containing:
  - database: The specific database to query (from the available databases list)
  - query: A concise, focused search query optimized for that database

No additional text or explanation should be included.
</RESPONSE_FORMAT>
"""


# Construct the complete system prompt by combining the necessary statements
def construct_system_prompt():
    # Get all the required statements
    project_statement = get_project_statement()
    fiscal_statement = get_fiscal_statement()
    database_statement = get_database_statement()
    restrictions_statement = get_restrictions_statement()

    # Combine into a formatted system prompt using CO-STAR framework
    prompt_parts = [
        "<CONTEXT>",
        project_statement,
        fiscal_statement,
        database_statement,
        restrictions_statement,
        "</CONTEXT>",
        
        "<OBJECTIVE>",
        PLANNER_OBJECTIVE,
        "</OBJECTIVE>",
        
        "<STYLE>",
        PLANNER_STYLE,
        "</STYLE>",
        
        "<TONE>",
        PLANNER_TONE,
        "</TONE>",
        
        "<AUDIENCE>",
        PLANNER_AUDIENCE,
        "</AUDIENCE>",
        
        f"You are {PLANNER_ROLE}.",
        PLANNER_TASK,
    ]

    # Join with double newlines for readability
    return "\n\n".join(prompt_parts)


# Generate the complete system prompt
SYSTEM_PROMPT = construct_system_prompt()

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
