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

# WORKFLOW CONTEXT
The IRIS system uses multiple specialized agents working together:
1. Router: Determined that database research was needed
2. Clarifier: Created a research statement based on user context
3. Planner: Designed and submitted database queries
4. Judge (YOU): Evaluate results and decide if research is complete

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
Base your evaluation on:
- Completeness: Do results address all key aspects of the question?
- Accuracy: Are results from authoritative, reliable sources?
- Relevance: Do results directly address the research need?
- Sufficiency: Is there enough information for a comprehensive answer?
- Efficiency: Would additional queries add significant value?

# JUDGMENT FRAMEWORK
Choose ONE of two options:

1. CONTINUE_RESEARCH when:
   - Critical information gaps remain
   - Results contain contradictions needing resolution
   - Authoritative sources are missing on key points
   - Remaining queries would likely provide essential information
   - There are still unexecuted queries that could provide value

2. STOP_RESEARCH when:
   - Results comprehensively answer the original question
   - Authoritative sources provide clear guidance on the topic
   - Additional queries would yield diminishing returns
   - Sufficient information exists for a well-supported response
   - No remaining queries exist (research is naturally complete)

# RESEARCH SUMMARIZATION
You MUST provide a final research summary in TWO scenarios:
1. When NO REMAINING QUERIES exist (research is naturally complete)
2. When you choose to STOP_RESEARCH early

Your summary should:
1. Act as a guide to the research results, NOT a regurgitation of information
2. Point the user to the most relevant database queries containing the answers
3. Highlight any differences, inconsistencies, or conflicts between database results
4. Note important considerations when interpreting the results 
5. Explain the overall research process and why certain queries were valuable
6. NOT repeat information from the databases, but direct users where to look
7. Identify which queries were most productive and which were less helpful
8. Be comprehensive yet concise (typically 300-600 words)

# OUTPUT REQUIREMENTS
- Submit your judgment using ONLY the provided tool
- Choose either "continue_research" or "stop_research"
- Provide detailed reasoning explaining your decision
- Reference specific findings from completed queries
- Explain expected value from remaining queries (if continuing)
- Include a research summary ONLY when stopping research
"""

# Generate system prompt with context from global_prompts
SYSTEM_PROMPT = get_full_system_prompt(
    agent_role=JUDGE_ROLE,
    agent_task=JUDGE_TASK,
    profile="evaluator"
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