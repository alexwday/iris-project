# python/iris/src/agents/agent_summarizer/summarizer_settings.py
"""
Summarizer Agent Settings

This module defines the settings and configuration for the summarizer agent,
including model capabilities and the system prompt.

Attributes:
    MODEL_CAPABILITY (str): The model capability to use ('small' or 'large')
    MAX_TOKENS (int): Maximum tokens for model response
    TEMPERATURE (float): Randomness parameter (0-1)
    SYSTEM_PROMPT (str): System prompt template defining the summarizer role
    AVAILABLE_DATABASES (dict): Information about available databases
"""

import logging
from ...global_prompts.prompt_utils import get_full_system_prompt

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Import database configuration from global prompts
from ...global_prompts.database_statement import get_available_databases
AVAILABLE_DATABASES = get_available_databases()

# Model capability - used to get specific model based on environment
# Consider using a 'large' model for potentially better summarization quality
MODEL_CAPABILITY = "large" 

# Model settings
MAX_TOKENS = 4096
TEMPERATURE = 0.1 # Slightly higher temp might allow for more nuanced summaries

# Define the summarizer agent role and task
SUMMARIZER_ROLE = "an expert research analyst specializing in synthesizing complex information"
SUMMARIZER_TASK = """You are tasked with creating a final summary of database research results.

# CONTEXT
You will receive:
1. The original research statement that guided the research.
2. A list of completed database queries and their full results.
3. Information about the available databases that were queried.

# RESEARCH SUMMARIZATION REQUIREMENTS
Create a comprehensive research summary that:
1. Acts as a guide to the research results, NOT a regurgitation of information.
2. Points the user to the most relevant database queries containing the answers (reference query numbers if available in context).
3. Highlights any differences, inconsistencies, or conflicts between database results.
4. Notes important considerations when interpreting the results.
5. Explains the overall research process and why certain queries were valuable (if discernible from context).
6. Does NOT repeat lengthy information from the databases, but directs users where to look.
7. Identifies which queries were most productive and which were less helpful.
8. Is comprehensive yet concise (typically 300-600 words).

# OUTPUT FORMAT
- Generate ONLY the summary content itself. Do not include any preamble like "Here is the summary:".
- Use a clear introduction, body paragraphs, and conclusion.
- Format with markdown headings (e.g., `## Key Findings`) and bullet points for readability.
- Reference specific query numbers when directing users to information (e.g., "See Query 3 for details on...").
- Highlight any conflicting information or gaps in knowledge discovered during the research.
"""

# Generate system prompt with context from global_prompts
SYSTEM_PROMPT = get_full_system_prompt(
    agent_role=SUMMARIZER_ROLE,
    agent_task=SUMMARIZER_TASK,
    profile="analyst", # Profile focused on synthesis and analysis
    agent_type="summarizer"
)

logger.debug("Summarizer agent settings initialized")
