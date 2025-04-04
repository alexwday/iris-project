# python/iris/src/agents/agent_judge/judge.py
"""
Judge Agent Module

This module evaluates whether database research should continue or stop based on
the results already gathered and the remaining planned queries.

Functions:
    evaluate_research_progress: Evaluates whether to continue or stop research

Dependencies:
    - json
    - logging
    - OpenAI connector for LLM calls
"""

import json
import logging
from ...llm_connectors.rbc_openai import call_llm, log_usage_statistics
from ...chat_model.model_settings import get_model_config
from .judge_settings import (
    MODEL_CAPABILITY,
    MAX_TOKENS,
    TEMPERATURE,
    SYSTEM_PROMPT,
    TOOL_DEFINITIONS,
    AVAILABLE_DATABASES
)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Get model configuration based on capability
model_config = get_model_config(MODEL_CAPABILITY)
MODEL_NAME = model_config["name"]
PROMPT_TOKEN_COST = model_config["prompt_token_cost"]
COMPLETION_TOKEN_COST = model_config["completion_token_cost"]

class JudgeError(Exception):
    """Base exception class for judge-related errors."""
    pass

def evaluate_research_progress(research_statement, completed_queries, remaining_queries, token):
    """
    Evaluate whether database research should continue or stop.
    
    Args:
        research_statement (str): The original research statement
        completed_queries (list): List of completed queries with their results
        remaining_queries (list): List of remaining queries to be executed
        token (str): Authentication token for API access
            - In RBC environment: OAuth token
            - In local environment: API key
            
    Returns:
        dict: Judgment with keys:
            - action: Either "continue_research" or "stop_research"
            - reason: Concise explanation of the decision
        
    Raises:
        JudgeError: If there is an error in evaluating the research decision
    """
    try:
        # Prepare system message with judge prompt
        system_message = {"role": "system", "content": SYSTEM_PROMPT}
        
        # Prepare messages for the API call
        messages = [system_message]
        
        # Add research statement
        research_message = {
            "role": "system", 
            "content": f"Research Statement: {research_statement}"
        }
        messages.append(research_message)
        
        # Add completed queries
        completed_content = "Completed Queries and Results:\n"
        for i, query in enumerate(completed_queries):
            completed_content += f"\n=== QUERY {i+1} ===\n"
            completed_content += f"Database: {query.get('database', 'Unknown')}\n"
            completed_content += f"Query: {query.get('query', 'Unknown')}\n"
            completed_content += f"Results: {query.get('results', 'No results')}\n"
        
        completed_message = {"role": "system", "content": completed_content}
        messages.append(completed_message)
        
        # Add remaining queries
        remaining_content = "Remaining Queries:\n"
        if not remaining_queries:
            remaining_content += "No remaining queries.\n"
        else:
            for i, query in enumerate(remaining_queries):
                remaining_content += f"\n=== QUERY {i+1} ===\n"
                remaining_content += f"Database: {query.get('database', 'Unknown')}\n"
                remaining_content += f"Query: {query.get('query', 'Unknown')}\n"
                remaining_content += f"Purpose: {query.get('thought', 'Unknown')}\n"
        
        remaining_message = {"role": "system", "content": remaining_content}
        messages.append(remaining_message)
        
        # Add database information for better context
        database_content = "Available Databases Information:\n"
        for db_id, db_info in AVAILABLE_DATABASES.items():
            database_content += f"\n{db_info['name']} ({db_id}):\n"
            database_content += f"  - Content: {db_info['content_type']}\n"
            database_content += f"  - Search method: {db_info['query_type']}\n"
            database_content += f"  - Use when: {db_info['use_when']}\n"
        
        database_message = {"role": "system", "content": database_content}
        messages.append(database_message)
        
        # User message requesting judgment, with additional context when no queries remain
        if not remaining_queries:
            user_message = {
                "role": "user", 
                "content": "All planned database queries have been completed. Please provide your final judgment and a comprehensive research summary."
            }
        else:
            user_message = {
                "role": "user", 
                "content": "Based on the completed queries and their results, should we continue with the remaining queries or stop research now?"
            }
        messages.append(user_message)
        
        logger.info(f"Evaluating research progress using model: {MODEL_NAME}")
        logger.info(f"Completed queries: {len(completed_queries)}, Remaining queries: {len(remaining_queries)}")
        
        # Make the API call with tool calling
        response = call_llm(
            oauth_token=token,
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            tools=TOOL_DEFINITIONS,
            tool_choice={"type": "function", "function": {"name": "submit_research_decision"}},
            stream=False,
            prompt_token_cost=PROMPT_TOKEN_COST,
            completion_token_cost=COMPLETION_TOKEN_COST
        )
        
        # Extract the tool call from the response
        if (not response.choices or 
            not response.choices[0].message or 
            not response.choices[0].message.tool_calls or 
            not response.choices[0].message.tool_calls[0]):
            raise JudgeError("No tool call received in response")
        
        tool_call = response.choices[0].message.tool_calls[0]
        
        # Verify that the correct function was called
        if tool_call.function.name != "submit_research_decision":
            raise JudgeError(f"Unexpected function call: {tool_call.function.name}")
        
        # Parse the arguments
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            raise JudgeError(f"Invalid JSON in tool arguments: {tool_call.function.arguments}")
        
        # Extract decision fields
        action = arguments.get("action")
        reason = arguments.get("reason")
        
        if not action:
            raise JudgeError("Missing 'action' in tool arguments")
        
        if not reason:
            # Allow empty reason, but log a warning
            logger.warning("Missing 'reason' in tool arguments, proceeding with empty reason.")
            reason = "" # Default to empty string if missing
        
        # Force "stop_research" when no remaining queries
        if not remaining_queries and action != "stop_research":
            action = "stop_research"
            logger.warning("Judge chose to continue but no queries remain; forcing stop_research")
        
        # Log the decision
        logger.info(f"Research decision: {action}")
        logger.info(f"Reason: {reason[:1000]}...") # Log first 1000 chars
        
        # Return only action and reason
        result = {
            "action": action,
            "reason": reason
        }
            
        return result
        
    except Exception as e:
        logger.error(f"Error evaluating research progress: {str(e)}")
        raise JudgeError(f"Failed to evaluate research progress: {str(e)}")
