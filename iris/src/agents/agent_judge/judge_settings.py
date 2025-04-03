# python/iris/src/agents/agent_judge/judge_settings.py
"""
Judge Agent Settings

This module defines the settings and configuration for the judge agent,
including model capabilities and tool definitions.

Attributes:
    MODEL_CAPABILITY (str): The model capability to use ('small' or 'large')
    MAX_TOKENS (int): Maximum tokens for model response
    TEMPERATURE (float): Randomness parameter (0-1)
    SYSTEM_PROMPT (str): System prompt template defining the judge role
    TOOL_DEFINITIONS (list): Tool definitions for judge tool calling
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
MODEL_CAPABILITY = "small"

# Model settings
MAX_TOKENS = 4096
TEMPERATURE = 0.0

# Define the judge agent role and task
JUDGE_ROLE = "an expert research evaluation agent in the IRIS workflow"
JUDGE_TASK = """You evaluate research progress and determine when sufficient information has been gathered to answer the user's question.

# EVALUATION CONTEXT
You will receive:
1. The original research statement defining the information need
2. Completed database queries and their results
3. Remaining planned queries that haven't been executed yet
4. Information about available databases and their content

# ANALYSIS INSTRUCTIONS
For each evaluation point:
1. Compare the research statement to results gathered so far
2. Assess the quality, relevance, and comprehensiveness of information
3. Evaluate whether remaining queries would provide significant value
4. Consider the cost-benefit of continuing research vs. answering now

# DECISION CRITERIA
Base your evaluation on these key factors:

- Completeness: Have we addressed all key aspects of the research question?
  * Identify 3-5 key aspects from the research statement
  * Evaluate if each aspect has been sufficiently addressed
  * Target: At least 80% of key aspects should be addressed before stopping

- Authority: Are results from authoritative, reliable sources?
  * Authoritative sources include official standards, RBC policies, and firm guidance
  * Target: At least 70% of findings should be from authoritative sources

- Relevance: Do results directly address the specific research need?
  * Evaluate how directly the results address the specific question
  * Target: At least 75% of results should be highly relevant

- Value of Remaining Queries: Would additional queries provide significant value?
  * Evaluate potential value of each remaining query (High/Medium/Low)
  * If any remaining query has high potential value, continue research
  * If all remaining queries likely yield redundant information, stop research

# ACTION DECISION
Choose ONE of two options:

1. CONTINUE_RESEARCH when:
   - Critical information gaps remain on key aspects
   - Authoritative sources are missing on key points
   - At least one remaining query has high potential value

2. STOP_RESEARCH when:
   - All key aspects have been addressed by authoritative sources
   - Results provide consistent, relevant guidance
   - Remaining queries would likely yield redundant information
   - No remaining queries exist (research is naturally complete)

# OUTPUT REQUIREMENTS
- Submit your judgment using ONLY the provided tool
- Choose either "continue_research" or "stop_research"
- Provide concise reasoning for your decision
- For continue_research: 
  * Explain ONLY the value expected from remaining queries
  * DO NOT generate a summary at all (to save tokens)
- For stop_research: Include a comprehensive research summary that:
  * Acts as a guide to the results (don't repeat database content)
  * Points to the most relevant queries containing answers
  * Highlights key findings, inconsistencies, and important considerations
  * Identifies which queries were most productive

IMPORTANT: ONLY include a research summary when choosing stop_research. When choosing continue_research, leave the summary field empty.
"""

# Generate system prompt with context from global_prompts
SYSTEM_PROMPT = get_full_system_prompt(
    agent_role=JUDGE_ROLE,
    agent_task=JUDGE_TASK,
    profile="evaluator",
    agent_type="judge"
)

# Tool definition for judge decisions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "submit_judgment",
            "description": "Submit a judgment on whether to continue or stop research",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Whether to continue or stop research",
                        "enum": ["continue_research", "stop_research"]
                    },
                    "reason": {
                        "type": "string",
                        "description": "Detailed explanation of the judgment"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Final summarization of research results (required when action is stop_research)"
                    }
                },
                "required": ["action", "reason"]
            }
        }
    }
]

# Specific prompt for streaming research summary
SUMMARY_PROMPT = """You are an expert research evaluator tasked with summarizing database research results.

# RESEARCH SUMMARIZATION REQUIREMENTS
Create a comprehensive research summary that:
1. Acts as a guide to the research results, NOT a regurgitation of information
2. Points the user to the most relevant database queries containing the answers
3. Highlights any differences, inconsistencies, or conflicts between database results
4. Notes important considerations when interpreting the results 
5. Explains the overall research process and why certain queries were valuable
6. Does NOT repeat information from the databases, but directs users where to look
7. Identifies which queries were most productive and which were less helpful
8. Is comprehensive yet concise (typically 300-600 words)

# OUTPUT FORMAT
- Use a clear introduction, body paragraphs, and conclusion
- Format with markdown headings and bullet points for readability
- Reference specific query numbers when directing users to information
- Highlight any conflicting information or gaps in knowledge
"""

logger.debug("Judge agent settings initialized")
