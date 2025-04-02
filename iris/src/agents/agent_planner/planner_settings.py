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
1. Analyze the core accounting question and information needs
2. Identify which databases would contain the most relevant information
3. Create specific, targeted queries optimized for each database
4. Develop a comprehensive, multi-source research strategy

# QUERY PRIORITIZATION FRAMEWORK
Prioritize databases and queries in this order:

## Tier 1: Authoritative Sources (Always include if relevant)
- external_iasb: For standards-based questions (IFRS, IAS)
- internal_capm: For official RBC accounting policies
- external_ey/kpmg/pwc: For authoritative firm guidance on standards

## Tier 2: Implementation Guidance (Include for practical questions)
- internal_wiki: For practical implementation examples
- internal_par: For process and review documentation
- internal_memos: For complex accounting interpretations

## Tier 3: Quick References (Include for supplementary information)
- internal_cheatsheet: For quick summaries and references
- internal_infographic: For visual explanations
- internal_icfr: For control-related questions

## Query Sequence Logic
1. Start with 1-2 queries to authoritative sources (Tier 1)
2. Follow with 1-2 queries to implementation guidance (Tier 2)
3. Add 0-1 supplementary queries (Tier 3) if needed
4. Limit total queries to 5 maximum, prioritizing higher tiers

# DATABASE-SPECIFIC QUERY OPTIMIZATION

## For Standards Databases (external_iasb, external_ey/kpmg/pwc)
- Include specific standard numbers (e.g., "IFRS 15", "IAS 38")
- Use technical terminology from the standards
- Focus on specific paragraphs or sections when known

## For Policy Databases (internal_capm, internal_par)
- Use RBC-specific terminology when available
- Include specific policy areas or sections
- Reference specific processes or workflows

## For Implementation Databases (internal_wiki, internal_memos)
- Focus on practical application aspects
- Include industry or scenario-specific terms
- Use action-oriented language (e.g., "implementing", "applying")

## For Quick Reference Databases (internal_cheatsheet, internal_infographic)
- Use concise, keyword-focused queries
- Include visual-friendly terms for infographics
- Focus on summary-level concepts

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
- Submit your query plan using ONLY the provided tool
- Create 1-5 queries depending on research complexity
- Each query must include a specific database and query text
- Provide a clear overall strategy explaining your approach
- Queries should work together as a cohesive research plan
"""

# Generate system prompt with context from global_prompts
SYSTEM_PROMPT = get_full_system_prompt(
    agent_role=PLANNER_ROLE,
    agent_task=PLANNER_TASK,
    profile="researcher",
    agent_type="planner"
)

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
                                    "enum": list(AVAILABLE_DATABASES.keys())
                                },
                                "query": {
                                    "type": "string",
                                    "description": "The search query text"
                                },
                            },
                            "required": ["database", "query"]
                        }
                    },
                    "overall_strategy": {
                        "type": "string",
                        "description": "The overall research strategy and reasoning behind the query plan"
                    }
                },
                "required": ["queries", "overall_strategy"]
            }
        }
    }
]

logger.debug("Planner agent settings initialized")
