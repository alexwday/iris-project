# python/iris/src/chat_model/model.py
"""
Model Initialization and Setup Module

This module serves as the main entry point for the IRIS application,
handling the full initialization process including logging setup,
SSL configuration, OAuth authentication, conversation processing,
and the full agent orchestration flow.

Functions:
    model: Main initialization function that sets up the necessary components
           and processes incoming conversations

Dependencies:
    - logging
    - SSL certificate setup
    - OAuth authentication
    - Conversation processing
    - Agent orchestration
"""

import json
import inspect
from datetime import datetime
from ..global_prompts.database_statement import get_available_databases
from ..llm_connectors.rbc_openai import get_token_usage, reset_token_usage


def format_usage_summary(token_usage, start_time=None):
    """
    Format token usage and timing information into a nicely formatted string.
    
    Args:
        token_usage (dict): Token usage dictionary with prompt_tokens, completion_tokens, etc.
        start_time (str, optional): ISO format timestamp of when processing started
        
    Returns:
        str: Formatted usage summary as markdown
    """
    # Calculate timing if start_time is provided
    duration = None
    if start_time:
        from datetime import datetime as dt
        end_dt = dt.now()
        start_dt = dt.fromisoformat(start_time)
        duration = (end_dt - start_dt).total_seconds()
    
    # Format the usage summary
    usage_summary = "\n\n---\n"
    usage_summary += "## Usage Statistics\n\n"
    usage_summary += f"- Input tokens: {token_usage['prompt_tokens']}\n"
    usage_summary += f"- Output tokens: {token_usage['completion_tokens']}\n"
    usage_summary += f"- Total tokens: {token_usage['total_tokens']}\n"
    usage_summary += f"- Cost: ${token_usage['cost']:.6f}\n"
    if duration:
        usage_summary += f"- Time: {duration:.2f} seconds\n"
    
    return usage_summary


def model(
    conversation=None,
    html_callback=None,
    debug_mode=False
):
    """
    Main model function that processes conversations and yields streaming responses.
    
    This function matches the signature and behavior of the original chat model,
    yielding response chunks directly as strings rather than as dictionaries.
    
    Args:
        conversation (dict, optional): Conversation in OpenAI format with a 'messages' key.
        html_callback (callable, optional): Callback function for HTML rendering (not used)
        debug_mode (bool, optional): When True, track agent decisions and yield debug data
            
    Returns:
        generator: A generator that yields response chunks as strings.
                  When debug_mode is True, the final yielded item will be a debug
                  data object (prefixed with "DEBUG_DATA:") containing all agent decisions.
    """
    # Initialize debug tracking if debug mode is enabled
    debug_data = {
        "decisions": [], 
        "tokens": {
            "prompt": 0, 
            "completion": 0, 
            "total": 0,
            "stages": {
                "router": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                "clarifier": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                "planner": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                "judge": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                "database_query": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                "summary": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}
            }
        },
        "cost": 0.0,
        "start_timestamp": datetime.now().isoformat()
    } if debug_mode else None
    
    # Reset token usage tracking
    if debug_mode:
        reset_token_usage()
    # Import modules - using relative imports for better portability
    from ..initial_setup.logging_config import configure_logging
    from ..initial_setup.ssl.ssl import setup_ssl
    from ..initial_setup.oauth.oauth import setup_oauth
    from ..conversation_setup.conversation import process_conversation
    from ..agents.agent_router.router import get_routing_decision
    from ..agents.agent_direct_response.response_from_conversation import response_from_conversation
    from ..agents.agent_clarifier.clarifier import clarify_research_needs
    from ..agents.agent_planner.planner import create_query_plan
    from ..agents.agent_judge.judge import evaluate_research_progress, generate_streaming_summary
    from ..agents.database_subagents.database_router import route_database_query
    
    try:
        # Set up centralized logging
        logger = configure_logging()
        
        logger.info("Initializing model setup...")
        
        # Set up SSL certificates for secure communication
        cert_path = setup_ssl()
        
        # Obtain OAuth token
        token = setup_oauth()
        
        # Process conversation if provided
        if conversation:
            logger.info("Processing input conversation...")
            processed_conversation = process_conversation(conversation)
            logger.info(f"Conversation processed: {len(processed_conversation['messages'])} messages")
            
            # Get routing decision
            logger.info("Getting routing decision...")
            routing_decision = get_routing_decision(processed_conversation, token)
            
            # Record routing decision in debug data if debug mode is enabled
            if debug_mode and debug_data is not None:
                # Get current token usage after router stage
                token_usage = get_token_usage()
                
                # Calculate and store per-stage token usage
                debug_data["tokens"]["stages"]["router"]["prompt"] = token_usage["prompt_tokens"]
                debug_data["tokens"]["stages"]["router"]["completion"] = token_usage["completion_tokens"]
                debug_data["tokens"]["stages"]["router"]["total"] = token_usage["total_tokens"]
                debug_data["tokens"]["stages"]["router"]["cost"] = token_usage["cost"]
                
                debug_data["decisions"].append({
                    "stage": "router",
                    "decision": routing_decision,
                    "timestamp": datetime.now().isoformat(),
                    "token_usage": {
                        "prompt": token_usage["prompt_tokens"],
                        "completion": token_usage["completion_tokens"],
                        "total": token_usage["total_tokens"],
                        "cost": token_usage["cost"]
                    }
                })
                
                # Reset token usage for next stage
                reset_token_usage()
            
            # Handle response based on routing decision
            if routing_decision["function_name"] == "response_from_conversation":
                # Direct response without research
                logger.info("Using direct response path based on routing decision")
                
                # Get the streaming response directly - each chunk is already a string
                for chunk in response_from_conversation(
                    processed_conversation, 
                    token
                ):
                    yield chunk
                
                # Add token usage summary if enabled
                from .model_settings import SHOW_USAGE_SUMMARY
                if SHOW_USAGE_SUMMARY:
                    # Get the final token usage
                    token_usage = get_token_usage()
                    
                    # Get the start timestamp from debug data if available
                    start_time = debug_data["start_timestamp"] if debug_data else None
                    
                    # Format and yield usage summary
                    usage_summary = format_usage_summary(token_usage, start_time)
                    yield usage_summary
                    
            elif routing_decision["function_name"] == "research_from_database":
                # Research path
                logger.info("Using research path based on routing decision")
                
                # Step 1: Clarify research needs
                logger.info("Clarifying research needs...")
                clarifier_decision = clarify_research_needs(processed_conversation, token)
                
                # Record clarifier decision in debug data if debug mode is enabled
                if debug_mode and debug_data is not None:
                    # Get current token usage after clarifier stage
                    token_usage = get_token_usage()
                    
                    # Calculate and store per-stage token usage
                    debug_data["tokens"]["stages"]["clarifier"]["prompt"] = token_usage["prompt_tokens"]
                    debug_data["tokens"]["stages"]["clarifier"]["completion"] = token_usage["completion_tokens"]
                    debug_data["tokens"]["stages"]["clarifier"]["total"] = token_usage["total_tokens"]
                    debug_data["tokens"]["stages"]["clarifier"]["cost"] = token_usage["cost"]
                    
                    debug_data["decisions"].append({
                        "stage": "clarifier",
                        "decision": clarifier_decision,
                        "timestamp": datetime.now().isoformat(),
                        "token_usage": {
                            "prompt": token_usage["prompt_tokens"],
                            "completion": token_usage["completion_tokens"],
                            "total": token_usage["total_tokens"],
                            "cost": token_usage["cost"]
                        }
                    })
                    
                    # Reset token usage for next stage
                    reset_token_usage()
                
                # If we need more context, yield the context questions directly as strings
                if clarifier_decision["action"] == "request_essential_context":
                    logger.info("Essential context needed, returning context questions")
                    
                    # Stream the questions, preserving any existing numbering
                    questions = clarifier_decision["output"].strip()
                    questions_text = "Before proceeding with research, please clarify:\n\n"
                    questions_text += questions
                    
                    yield questions_text
                
                # Otherwise, proceed with research
                else:  # create_research_statement
                    logger.info("Creating research statement, proceeding with research")
                    research_statement = clarifier_decision["output"]
                    is_continuation = clarifier_decision.get("is_continuation", False)
                    
                    # Step 2: Create query plan
                    logger.info("Creating database query plan...")
                    query_plan = create_query_plan(research_statement, token, is_continuation)
                    logger.info(f"Query plan created with {len(query_plan['queries'])} queries")
                    
                    # Record planner decision in debug data if debug mode is enabled
                    if debug_mode and debug_data is not None:
                        # Get current token usage after planner stage
                        token_usage = get_token_usage()
                        
                        # Calculate and store per-stage token usage
                        debug_data["tokens"]["stages"]["planner"]["prompt"] = token_usage["prompt_tokens"]
                        debug_data["tokens"]["stages"]["planner"]["completion"] = token_usage["completion_tokens"]
                        debug_data["tokens"]["stages"]["planner"]["total"] = token_usage["total_tokens"]
                        debug_data["tokens"]["stages"]["planner"]["cost"] = token_usage["cost"]
                        
                        debug_data["decisions"].append({
                            "stage": "planner",
                            "decision": query_plan,
                            "timestamp": datetime.now().isoformat(),
                            "token_usage": {
                                "prompt": token_usage["prompt_tokens"],
                                "completion": token_usage["completion_tokens"],
                                "total": token_usage["total_tokens"],
                                "cost": token_usage["cost"]
                            }
                        })
                        
                        # Reset token usage for next stage
                        reset_token_usage()
                    
                    # Get database configurations for display names
                    available_databases = get_available_databases()
                    
                    # Create a formatted markdown box with research plan using horizontal rules
                    research_plan_box = "---\n"
                    research_plan_box += "# 📋 Research Plan\n\n"
                    research_plan_box += f"## Research Statement\n{research_statement}\n\n"
                    research_plan_box += "## Database Queries\n"
                    
                    for j, query in enumerate(query_plan["queries"]):
                        db_name = query["database"]
                        # Get the display name from the database configuration
                        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
                        research_plan_box += f"{j+1}. {db_display_name}: {query['query']}\n"
                    
                    research_plan_box += "---\n\n"
                    
                    # Yield the entire research plan box
                    yield research_plan_box
                    
                    # Prepare lists to track queries and results
                    completed_queries = []
                    query_results = []
                    remaining_queries = query_plan["queries"].copy()
                    
                    # Process queries one by one
                    i = 0
                    while i < len(query_plan["queries"]) and remaining_queries:
                        # Get the current query
                        current_query = query_plan["queries"][i]
                        
                        # Remove from remaining and add to completed
                        remaining_queries.remove(current_query)
                        completed_queries.append(current_query)
                        
                        # Get database name from the query
                        db_name = current_query["database"]
                        
                        # Get the display name from the database configuration
                        available_databases = get_available_databases()
                        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
                        
                        # Yield query information with improved formatting using display name
                        query_header = f"\n## 🔍 Query {i+1}: {db_display_name} - {current_query['query']}\n\n"
                        yield query_header
                        
                        # Execute the query
                        try:
                            # Execute database query and yield result directly
                            results = route_database_query(db_name, current_query["query"], token)
                            current_query["results"] = results
                            query_results.append(results)
                            
                            # Record database query result in debug data if debug mode is enabled
                            if debug_mode and debug_data is not None:
                                # Get current token usage after database query
                                token_usage = get_token_usage()
                                
                                # Calculate and store per-stage token usage
                                # For database queries, we accumulate since there might be multiple
                                debug_data["tokens"]["stages"]["database_query"]["prompt"] += token_usage["prompt_tokens"]
                                debug_data["tokens"]["stages"]["database_query"]["completion"] += token_usage["completion_tokens"]
                                debug_data["tokens"]["stages"]["database_query"]["total"] += token_usage["total_tokens"]
                                debug_data["tokens"]["stages"]["database_query"]["cost"] += token_usage["cost"]
                                
                                debug_data["decisions"].append({
                                    "stage": "database_query",
                                    "decision": {
                                        "database": db_name,
                                        "query": current_query["query"],
                                        "results_type": str(type(results).__name__) 
                                    },
                                    "timestamp": datetime.now().isoformat(),
                                    "token_usage": {
                                        "prompt": token_usage["prompt_tokens"],
                                        "completion": token_usage["completion_tokens"],
                                        "total": token_usage["total_tokens"],
                                        "cost": token_usage["cost"]
                                    }
                                })
                                
                                # Reset token usage for next stage
                                reset_token_usage()
                            
                            # Handle streaming results (generators) or direct string results
                            if inspect.isgenerator(results):
                                # For generator results, iterate and yield each chunk
                                # This ensures we always yield strings, never a nested generator
                                for chunk in results:
                                    if isinstance(chunk, str):
                                        yield chunk
                                    elif inspect.isgenerator(chunk):
                                        # Handle nested generators by consuming them
                                        for subchunk in chunk:
                                            yield str(subchunk)
                                    else:
                                        # Convert any non-string objects to strings
                                        yield str(chunk)
                                # Add horizontal rule after all chunks
                                yield "\n\n---"
                            else:
                                # For string results, yield directly with ending horizontal rule
                                yield f"{results}\n\n---"
                            
                        except Exception as e:
                            logger.error(f"Error executing query: {str(e)}")
                            error_message = f"Error: {str(e)}\n\n"
                            current_query["results"] = error_message
                            query_results.append(error_message)
                            
                            yield f"{error_message}\n---"
                        
                        logger.info(f"Completed database query {i+1}/{len(query_plan['queries'])}: {db_name}")
                        
                        # Only consult judge if there are more queries to process
                        if remaining_queries:
                            # Consult judge to decide whether to continue
                            judgment = evaluate_research_progress(
                                research_statement, 
                                completed_queries, 
                                remaining_queries, 
                                token
                            )
                            
                            # Record judge decision in debug data if debug mode is enabled
                            if debug_mode and debug_data is not None:
                                # Get current token usage after judge evaluation
                                token_usage = get_token_usage()
                                
                                # Calculate and store per-stage token usage
                                debug_data["tokens"]["stages"]["judge"]["prompt"] += token_usage["prompt_tokens"]
                                debug_data["tokens"]["stages"]["judge"]["completion"] += token_usage["completion_tokens"]
                                debug_data["tokens"]["stages"]["judge"]["total"] += token_usage["total_tokens"]
                                debug_data["tokens"]["stages"]["judge"]["cost"] += token_usage["cost"]
                                
                                debug_data["decisions"].append({
                                    "stage": "judge",
                                    "decision": judgment,
                                    "timestamp": datetime.now().isoformat(),
                                    "token_usage": {
                                        "prompt": token_usage["prompt_tokens"],
                                        "completion": token_usage["completion_tokens"],
                                        "total": token_usage["total_tokens"],
                                        "cost": token_usage["cost"]
                                    }
                                })
                                
                                # Reset token usage for next stage
                                reset_token_usage()
                            
                            # Determine whether to continue
                            continue_research = (judgment["action"] == "continue_research")
                            
                            if not continue_research:
                                # Generate a streaming summary when stopping early with improved formatting
                                yield "\n## 📊 Research Summary\n"
                                
                                # Record start of streaming summary in debug data if debug mode is enabled
                                if debug_mode and debug_data is not None:
                                    # Reset token usage for streaming summary
                                    reset_token_usage()
                                    
                                    # Add a decision entry for summary start
                                    debug_data["decisions"].append({
                                        "stage": "summary",
                                        "decision": {
                                            "action": "start_streaming_summary",
                                            "completed_queries": len(completed_queries)
                                        },
                                        "timestamp": datetime.now().isoformat()
                                    })
                                
                                # Get streaming summary from judge agent
                                for summary_chunk in generate_streaming_summary(
                                    research_statement,
                                    completed_queries,
                                    token
                                ):
                                    yield summary_chunk
                                
                                # Record completion of streaming summary in debug data if debug mode is enabled
                                if debug_mode and debug_data is not None:
                                    # Get token usage for summary generation
                                    token_usage = get_token_usage()
                                    
                                    # Store per-stage token usage for summary
                                    debug_data["tokens"]["stages"]["summary"]["prompt"] = token_usage["prompt_tokens"]
                                    debug_data["tokens"]["stages"]["summary"]["completion"] = token_usage["completion_tokens"]
                                    debug_data["tokens"]["stages"]["summary"]["total"] = token_usage["total_tokens"]
                                    debug_data["tokens"]["stages"]["summary"]["cost"] = token_usage["cost"]
                                    
                                    # Add a decision entry for summary completion
                                    debug_data["decisions"].append({
                                        "stage": "summary",
                                        "decision": {
                                            "action": "complete_streaming_summary",
                                            "completed_queries": len(completed_queries)
                                        },
                                        "timestamp": datetime.now().isoformat(),
                                        "token_usage": {
                                            "prompt": token_usage["prompt_tokens"],
                                            "completion": token_usage["completion_tokens"],
                                            "total": token_usage["total_tokens"],
                                            "cost": token_usage["cost"]
                                        }
                                    })
                                    
                                    # Reset token usage for next stage
                                    reset_token_usage()
                                
                                yield "\n\n---"
                                
                                # If stopping, provide information about remaining queries
                                if remaining_queries:
                                    yield format_remaining_queries(remaining_queries)
                                break
                        
                        # Move to next query
                        i += 1
                    
                    # When naturally completing all queries, stream the final research summary
                    if not remaining_queries and completed_queries:
                        # Yield a header for the research summary with improved formatting
                        yield "\n## 📊 Research Summary\n"
                        
                        # Record start of streaming summary in debug data if debug mode is enabled
                        if debug_mode and debug_data is not None:
                            # Reset token usage for streaming summary
                            reset_token_usage()
                            
                            # Add a decision entry for summary start
                            debug_data["decisions"].append({
                                "stage": "summary",
                                "decision": {
                                    "action": "start_streaming_summary",
                                    "completed_queries": len(completed_queries)
                                },
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        # Get streaming summary from judge agent
                        for summary_chunk in generate_streaming_summary(
                            research_statement,
                            completed_queries,
                            token
                        ):
                            yield summary_chunk
                        
                        # Record completion of streaming summary in debug data if debug mode is enabled
                        if debug_mode and debug_data is not None:
                            # Get token usage for summary generation
                            token_usage = get_token_usage()
                            
                            # Store per-stage token usage for summary
                            debug_data["tokens"]["stages"]["summary"]["prompt"] = token_usage["prompt_tokens"]
                            debug_data["tokens"]["stages"]["summary"]["completion"] = token_usage["completion_tokens"]
                            debug_data["tokens"]["stages"]["summary"]["total"] = token_usage["total_tokens"]
                            debug_data["tokens"]["stages"]["summary"]["cost"] = token_usage["cost"]
                            
                            # Add a decision entry for summary completion
                            debug_data["decisions"].append({
                                "stage": "summary",
                                "decision": {
                                    "action": "complete_streaming_summary",
                                    "completed_queries": len(completed_queries)
                                },
                                "timestamp": datetime.now().isoformat(),
                                "token_usage": {
                                    "prompt": token_usage["prompt_tokens"],
                                    "completion": token_usage["completion_tokens"],
                                    "total": token_usage["total_tokens"],
                                    "cost": token_usage["cost"]
                                }
                            })
                        
                        # Add a buffer after the summary with closing horizontal rule
                        yield "\n\n---"
                    
                    # Final completion message
                    completion_message = f"\nCompleted {len(completed_queries)} database queries.\n"
                    yield completion_message
                    logger.info("Completed research process")
                    
                    # Add token usage summary if enabled
                    from .model_settings import SHOW_USAGE_SUMMARY
                    if SHOW_USAGE_SUMMARY:
                        # Get the final token usage
                        token_usage = get_token_usage()
                        
                        # Get the start timestamp from debug data if available
                        start_time = debug_data["start_timestamp"] if debug_data else None
                        
                        # Format and yield usage summary
                        usage_summary = format_usage_summary(token_usage, start_time)
                        yield usage_summary
            
            else:
                # Unknown function - yield error
                logger.error(f"Unknown routing function: {routing_decision['function_name']}")
                yield "Error: Unable to process query due to internal routing error."
        
        else:
            # If no conversation was provided, yield initialization message
            logger.info("Model initialization complete")
            yield "Model initialized successfully, but no conversation was provided."
            
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        
        # Record error in debug data if debug mode is enabled
        if debug_mode and debug_data is not None:
            debug_data["error"] = error_msg
            debug_data["completed"] = False
            
            # Get token usage data
            token_usage = get_token_usage()
            debug_data["tokens"]["prompt"] = token_usage["prompt_tokens"]
            debug_data["tokens"]["completion"] = token_usage["completion_tokens"]
            debug_data["tokens"]["total"] = token_usage["total_tokens"]
            debug_data["cost"] = token_usage["cost"]
            
            debug_data["end_timestamp"] = datetime.now().isoformat()
            # Yield debug data as a special message
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"
            
        yield error_msg
        
    finally:
        # Add completion status and yield debug data if debug mode is enabled
        if debug_mode and debug_data is not None:
            debug_data["completed"] = True
            
            # Get any remaining token usage data from global counter
            token_usage = get_token_usage()
            
            # Update the overall token usage from the per-stage metrics
            total_prompt = 0
            total_completion = 0
            total_tokens = 0
            total_cost = 0
            
            # Sum up token usage across all stages
            for stage, usage in debug_data["tokens"]["stages"].items():
                total_prompt += usage["prompt"]
                total_completion += usage["completion"]
                total_tokens += usage["total"]
                total_cost += usage["cost"]
            
            # Store the summed values in the main token usage
            debug_data["tokens"]["prompt"] = total_prompt
            debug_data["tokens"]["completion"] = total_completion
            debug_data["tokens"]["total"] = total_tokens
            debug_data["cost"] = total_cost
            
            # Add final timestamp
            debug_data["end_timestamp"] = datetime.now().isoformat()
            
            # Yield debug data as a special message that can be parsed by the notebook
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"


def format_remaining_queries(remaining_queries):
    """Format remaining queries for display to the user."""
    if not remaining_queries:
        return "There are no remaining database queries."
    
    # Get database configurations for display names
    available_databases = get_available_databases()
    
    message = "## ⏸️ Remaining Queries\n\n"
    message += "The following database queries were not processed:\n\n"
    for i, query in enumerate(remaining_queries, 1):
        db_name = query['database']
        # Get the display name from the database configuration
        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
        message += f"**{i}.** {db_display_name}: {query['query']}\n"
    
    message += "\nPlease let me know if you would like to continue with these remaining database queries in a new search."
    return message
