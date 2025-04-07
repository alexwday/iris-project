# python/iris/src/chat_model/model.py
"""
Model Initialization and Setup Module (Async Core with Sync Wrapper)

This module serves as the main entry point for the IRIS application.
It uses an asynchronous core for parallel processing but provides a
synchronous interface for compatibility with standard Python iteration.

Functions:
    model: Synchronous wrapper that runs the async core and yields results.
    _model_async_generator: Main async core function handling the workflow.

Dependencies:
    - logging
    - SSL certificate setup
    - OAuth authentication
    - Conversation processing
    - Agent orchestration (async components)
"""

import inspect
import concurrent.futures
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Generator # Removed AsyncGenerator

# ... (Keep existing imports) ...
from ..global_prompts.database_statement import get_available_databases
from ..llm_connectors.rbc_openai import get_token_usage, reset_token_usage
# Import sync version of route_query
from ..agents.database_subagents.database_router import route_query_sync


# --- Formatting Function (Remains Synchronous) ---
def format_usage_summary(agent_token_usage: Dict[str, Any], start_time: Optional[str] = None) -> str:
    """
    Format token usage and timing information into a nicely formatted string.
    Note: Database usage is now included within agent_token_usage due to central logging.

    Args:
        agent_token_usage (dict): Accumulated token usage dictionary with keys like
                                  'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost'.
        start_time (str, optional): ISO format timestamp of when processing started.

    Returns:
        str: Formatted usage summary as markdown.
    """
    duration = None
    if start_time:
        try:
            end_dt = datetime.now()
            start_dt = datetime.fromisoformat(start_time)
            duration = (end_dt - start_dt).total_seconds()
        except ValueError:
            # Use root logger if module logger isn't configured yet
            logging.getLogger().warning(f"Could not parse start_time for duration calculation: {start_time}")
            duration = None # Ensure duration is None if parsing fails

    usage_summary = "\n\n---\n"
    usage_summary += "## Agent Usage Statistics\n\n" # Renamed for clarity
    usage_summary += f"- Overall Input tokens: {agent_token_usage.get('prompt_tokens', 0)}\n"
    usage_summary += f"- Overall Output tokens: {agent_token_usage.get('completion_tokens', 0)}\n"
    usage_summary += f"- Overall Total tokens: {agent_token_usage.get('total_tokens', 0)}\n"
    usage_summary += f"- Overall Cost: ${agent_token_usage.get('cost', 0.0):.6f}\n"
    if duration is not None: # Check if duration calculation was successful
        usage_summary += f"- Total Time: {duration:.2f} seconds\n"

    return usage_summary


# --- Worker Function for Threaded Query Execution ---
def _execute_query_worker(db_name: str, query_text: str, scope: str, token: str,
                          db_display_name: str, query_index: int, total_queries: int, 
                          debug_mode: bool = False) -> Dict[str, Any]:
    """
    Worker function executed by each thread to run a single database query.

    Args:
        db_name (str): Internal database identifier.
        query_text (str): The query string for the database.
        scope (str): The scope of the query ('research' or 'metadata').
        token (str): Authentication token.
        db_display_name (str): User-facing name of the database.
        query_index (int): The 0-based index of this query.
        total_queries (int): The total number of queries being run.
        debug_mode (bool): Whether to enable debug mode.

    Returns:
        dict: A dictionary containing query details, result, exception (if any),
              and token usage for this specific query.
    """
    logger = logging.getLogger(__name__) # Get logger instance
    result = None
    task_exception = None
    token_usage = {}
    
    # Import process monitor if debug mode is enabled
    if debug_mode:
        from ..initial_setup.process_monitor import get_process_monitor
        process_monitor = get_process_monitor()
        
        # Create a unique name for this query
        query_stage_name = f"db_query_{db_name}_{query_index}"
        
        # Start query stage
        process_monitor.start_stage(query_stage_name)
        process_monitor.add_stage_details(
            query_stage_name,
            db_name=db_name,
            db_display_name=db_display_name,
            query_text=query_text,
            scope=scope,
            query_index=query_index,
            total_queries=total_queries
        )

    try:
        logger.info(f"Thread executing query {query_index + 1}/{total_queries} for database: {db_name}")
        # Reset token usage specifically for this thread's context before the call
        reset_token_usage()
        
        start_time = time.time()
        # Call the synchronous router function
        result = route_query_sync(db_name, query_text, scope, token)
        execution_time = time.time() - start_time
        
        # Get token usage immediately after the call completes
        token_usage = get_token_usage()
        logger.info(f"Thread completed query for database: {db_name} in {execution_time:.2f}s")
        
        # End query stage if debug mode is enabled
        if debug_mode:
            process_monitor.end_stage(query_stage_name)
            process_monitor.update_stage_tokens(
                query_stage_name,
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                total_tokens=token_usage.get("total_tokens", 0),
                cost=token_usage.get("cost", 0.0)
            )
            
            # Add result details
            if scope == "metadata" and isinstance(result, list):
                process_monitor.add_stage_details(
                    query_stage_name,
                    result_count=len(result),
                    document_names=[item.get('document_name', 'Unnamed') for item in result[:10]],  # First 10 docs
                    has_more_documents=len(result) > 10
                )
            elif scope == "research" and isinstance(result, dict):
                process_monitor.add_stage_details(
                    query_stage_name,
                    status_summary=result.get('status_summary', 'No status provided'),
                    has_detailed_research=bool(result.get('detailed_research'))
                )
            
    except Exception as e:
        task_exception = e
        # Also capture token usage even if there was an error during the query itself
        token_usage = get_token_usage()
        logger.error(f"Thread error executing query for {db_name}: {str(e)}", exc_info=True)
        
        # End query stage with error if debug mode is enabled
        if debug_mode:
            process_monitor.end_stage(query_stage_name, "error")
            process_monitor.update_stage_tokens(
                query_stage_name,
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                total_tokens=token_usage.get("total_tokens", 0),
                cost=token_usage.get("cost", 0.0)
            )
            process_monitor.add_stage_details(
                query_stage_name,
                error=str(e)
            )

    return {
        "db_name": db_name,
        "query_text": query_text,
        "scope": scope,
        "db_display_name": db_display_name,
        "query_index": query_index,
        "total_queries": total_queries,
        "result": result,
        "exception": task_exception,
        "token_usage": token_usage
    }


# --- Main Synchronous Core Function ---
def _model_generator(conversation: Optional[Dict[str, Any]] = None,
                     html_callback: Optional[callable] = None,
                     debug_mode: bool = False) -> Generator[str, None, None]:
    """
    Core synchronous generator handling the agent workflow.
    (Internal function called by the synchronous wrapper)
    """
    # Import process monitor
    from ..initial_setup.process_monitor import enable_monitoring, get_process_monitor
    
    # Enable process monitoring if debug mode is enabled
    if debug_mode:
        enable_monitoring(True)
        
    # Get process monitor instance
    process_monitor = get_process_monitor()
    
    # Initialize legacy debug tracking for backward compatibility
    debug_data = None
    if debug_mode:
        debug_data = {
            "decisions": [],
            "tokens": {
                "prompt": 0, "completion": 0, "total": 0, "cost": 0.0, # Overall accumulated
                "stages": { # Per-stage accumulated usage
                    "router": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                    "clarifier": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                    "planner": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                    "database_query": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}, # Accumulated across all parallel queries
                    "summary": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
                }
            },
            "start_timestamp": datetime.now().isoformat(),
            "error": None,
            "completed": False
        }

    # Reset global token usage tracking at the start
    reset_token_usage()

    # Import necessary modules
    from ..agents.agent_clarifier.clarifier import clarify_research_needs
    from ..agents.agent_direct_response.response_from_conversation import response_from_conversation
    from ..agents.agent_planner.planner import create_query_plan
    from ..agents.agent_router.router import get_routing_decision
    # TODO: Ensure generate_streaming_summary becomes async or is properly wrapped
    from ..agents.agent_summarizer.summarizer import generate_streaming_summary
    from ..conversation_setup.conversation import process_conversation
    from ..initial_setup.logging_config import configure_logging
    from ..initial_setup.oauth.oauth import setup_oauth
    from ..initial_setup.ssl.ssl import setup_ssl
    from .model_settings import SHOW_USAGE_SUMMARY

    logger = configure_logging() # Ensure logger is configured early

    try:
        logger.info("Initializing model setup (sync core)...")
        
        # Start SSL setup stage
        if debug_mode:
            process_monitor.start_stage("ssl_setup")
        
        cert_path = setup_ssl()
        
        # End SSL setup stage
        if debug_mode:
            process_monitor.end_stage("ssl_setup")
            process_monitor.add_stage_details("ssl_setup", cert_path=cert_path)
        
        # Start OAuth setup stage
        if debug_mode:
            process_monitor.start_stage("oauth_setup")
        
        token = setup_oauth()
        
        # End OAuth setup stage
        if debug_mode:
            process_monitor.end_stage("oauth_setup")
            process_monitor.add_stage_details("oauth_setup", token_length=len(token) if token else 0)

        if not conversation or 'messages' not in conversation or not conversation['messages']:
            logger.warning("No conversation provided or conversation is empty.")
            yield "Model initialized, but no conversation provided to process."
            return

        # Start conversation processing stage
        if debug_mode:
            process_monitor.start_stage("conversation_processing")
            
        logger.info("Processing input conversation...")
        processed_conversation = process_conversation(conversation)
        logger.info(f"Conversation processed: {len(processed_conversation['messages'])} messages")
        
        # End conversation processing stage
        if debug_mode:
            process_monitor.end_stage("conversation_processing")
            process_monitor.add_stage_details(
                "conversation_processing", 
                message_count=len(processed_conversation['messages'])
            )
        
        # Start router stage
        if debug_mode:
            process_monitor.start_stage("router")
            
        logger.info("Getting routing decision...")
        routing_decision = get_routing_decision(processed_conversation, token)
        
        # Get token usage for router
        token_usage = get_token_usage()
        
        # End router stage
        if debug_mode:
            process_monitor.end_stage("router")
            process_monitor.update_stage_tokens(
                "router",
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                total_tokens=token_usage.get("total_tokens", 0),
                cost=token_usage.get("cost", 0.0)
            )
            process_monitor.add_stage_details(
                "router", 
                function_name=routing_decision.get("function_name"),
                decision=routing_decision
            )
            
        # --- Debug: Record Router Decision (legacy) ---
        if debug_mode and debug_data is not None:
            debug_data["tokens"]["stages"]["router"] = token_usage.copy()
            debug_data["decisions"].append({
                "stage": "router", "decision": routing_decision,
                "timestamp": datetime.now().isoformat(), "token_usage": token_usage.copy()
            })
            reset_token_usage()
        # --- End Debug ---

        # --- Direct Response Path ---
        if routing_decision["function_name"] == "response_from_conversation":
            logger.info("Using direct response path based on routing decision")
            
            # Start direct response stage
            if debug_mode:
                process_monitor.start_stage("direct_response")
            
            # Assuming sync generator
            for chunk in response_from_conversation(processed_conversation, token):
                yield chunk
            
            # Get token usage for direct response
            direct_response_token_usage = get_token_usage()
            
            # End direct response stage
            if debug_mode:
                process_monitor.end_stage("direct_response")
                process_monitor.update_stage_tokens(
                    "direct_response",
                    prompt_tokens=direct_response_token_usage.get("prompt_tokens", 0),
                    completion_tokens=direct_response_token_usage.get("completion_tokens", 0),
                    total_tokens=direct_response_token_usage.get("total_tokens", 0),
                    cost=direct_response_token_usage.get("cost", 0.0)
                )
                
                # End overall monitoring and yield summary if debug mode is enabled
                process_monitor.end_monitoring()
                yield process_monitor.format_summary()
            
            # --- Legacy Debug: Add Usage Summary ---
            elif SHOW_USAGE_SUMMARY:
                final_token_usage = get_token_usage()
                start_time = debug_data["start_timestamp"] if debug_data else None
                usage_summary = format_usage_summary(final_token_usage, start_time)
                yield usage_summary
            # --- End Debug ---

        # --- Research Path ---
        elif routing_decision["function_name"] == "research_from_database":
            logger.info("Using research path based on routing decision")

            # Step 1: Clarify research needs (assuming sync)
            
            # Start clarifier stage
            if debug_mode:
                process_monitor.start_stage("clarifier")
                
            logger.info("Clarifying research needs...")
            clarifier_decision = clarify_research_needs(processed_conversation, token)
            
            # Get token usage for clarifier
            clarifier_token_usage = get_token_usage()
            
            # End clarifier stage
            if debug_mode:
                process_monitor.end_stage("clarifier")
                process_monitor.update_stage_tokens(
                    "clarifier",
                    prompt_tokens=clarifier_token_usage.get("prompt_tokens", 0),
                    completion_tokens=clarifier_token_usage.get("completion_tokens", 0),
                    total_tokens=clarifier_token_usage.get("total_tokens", 0),
                    cost=clarifier_token_usage.get("cost", 0.0)
                )
                process_monitor.add_stage_details(
                    "clarifier",
                    action=clarifier_decision.get("action"),
                    scope=clarifier_decision.get("scope"),
                    is_continuation=clarifier_decision.get("is_continuation", False),
                    decision=clarifier_decision
                )

            # --- Legacy Debug: Record Clarifier Decision ---
            if debug_mode and debug_data is not None:
                debug_data["tokens"]["stages"]["clarifier"] = clarifier_token_usage.copy()
                debug_data["decisions"].append({
                    "stage": "clarifier", "decision": clarifier_decision,
                    "timestamp": datetime.now().isoformat(), "token_usage": clarifier_token_usage.copy()
                })
                reset_token_usage()
            # --- End Debug ---

            if clarifier_decision["action"] == "request_essential_context":
                logger.info("Essential context needed, returning context questions")
                questions = clarifier_decision["output"].strip()
                questions_text = "Before proceeding with research, please clarify:\n\n" + questions
                yield questions_text

            else: # create_research_statement
                logger.info("Creating research statement, proceeding with research")
                research_statement = clarifier_decision["output"]
                scope = clarifier_decision.get("scope")
                is_continuation = clarifier_decision.get("is_continuation", False)

                if not scope:
                     logger.error("Scope missing from clarifier decision.")
                     yield "Error: Internal configuration error - missing research scope."
                     return

                logger.info(f"Research scope determined: {scope}")

                # Step 2: Create query plan (assuming sync)
                
                # Start planner stage
                if debug_mode:
                    process_monitor.start_stage("planner")
                
                logger.info("Creating database query plan...")
                query_plan = create_query_plan(research_statement, token, is_continuation)
                logger.info(f"Query plan created with {len(query_plan['queries'])} queries")
                
                # Get token usage for planner
                planner_token_usage = get_token_usage()
                
                # End planner stage
                if debug_mode:
                    process_monitor.end_stage("planner")
                    process_monitor.update_stage_tokens(
                        "planner",
                        prompt_tokens=planner_token_usage.get("prompt_tokens", 0),
                        completion_tokens=planner_token_usage.get("completion_tokens", 0),
                        total_tokens=planner_token_usage.get("total_tokens", 0),
                        cost=planner_token_usage.get("cost", 0.0)
                    )
                    process_monitor.add_stage_details(
                        "planner",
                        query_count=len(query_plan.get('queries', [])),
                        databases=[q.get('database') for q in query_plan.get('queries', [])],
                        decision=query_plan
                    )

                # --- Legacy Debug: Record Planner Decision ---
                if debug_mode and debug_data is not None:
                    debug_data["tokens"]["stages"]["planner"] = planner_token_usage.copy()
                    debug_data["decisions"].append({
                        "stage": "planner", "decision": query_plan,
                        "timestamp": datetime.now().isoformat(), "token_usage": planner_token_usage.copy()
                    })
                    reset_token_usage()
                # --- End Debug ---

                # --- Display Updated Research/Search Plan ---
                available_databases = get_available_databases()
                if scope == "metadata":
                    yield "---\n# 🔍 File Search Plan\n\n"
                    yield f"## Search Criteria\n{research_statement}\n\n"
                else: # scope == "research"
                    yield "---\n# 📋 Research Plan\n\n"
                    yield f"## Research Statement\n{research_statement}\n\n"

                # Get unique database names using a set to avoid duplicates
                unique_db_names_in_plan = list(set([
                    available_databases.get(q["database"], {}).get("name", q["database"])
                    for q in query_plan["queries"]
                ]))
                if unique_db_names_in_plan:
                    if len(unique_db_names_in_plan) == 1: names_str = unique_db_names_in_plan[0]
                    elif len(unique_db_names_in_plan) == 2: names_str = f"{unique_db_names_in_plan[0]} and {unique_db_names_in_plan[1]}"
                    else: names_str = ", ".join(unique_db_names_in_plan[:-1]) + f", and {unique_db_names_in_plan[-1]}"
                    yield f"Searching the following databases: {names_str}.\n\n---\n"
                else:
                    yield "No databases selected for search.\n\n---\n"
                logger.info("Displayed simplified research plan.")
                # --- End Plan Display ---

                # --- Parallel Query Execution ---
                tasks_with_details = [] # Store tasks along with their details
                if not query_plan["queries"]:
                     logger.warning("Query plan is empty, skipping database search.")
                else:
                    # --- Concurrent Query Execution using ThreadPoolExecutor ---
                    logger.info(f"Starting {len(query_plan['queries'])} database queries concurrently...")
                    aggregated_detailed_research = {}
                    metadata_results_by_db: Dict[str, List[Dict[str, Any]]] = {}
                    total_metadata_items = 0
                    futures = []
                    db_stage_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for i, query_dict in enumerate(query_plan["queries"]):
                            db_name = query_dict["database"]
                            query_text = query_dict["query"]
                            db_display_name = available_databases.get(db_name, {}).get("name", db_name)
                            # Submit the worker function to the executor
                            future = executor.submit(
                                _execute_query_worker,
                                db_name, query_text, scope, token,
                                db_display_name, i, len(query_plan["queries"]),
                                debug_mode
                            )
                            futures.append(future)

                        logger.info(f"Submitted {len(futures)} queries to thread pool.")

                        # Process results as they complete
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                result_data = future.result() # Get result from the completed future
                            except Exception as exc:
                                # This catches errors in the future.result() call itself, unlikely if worker handles exceptions
                                logger.error(f"Error retrieving result from future: {exc}", exc_info=True)
                                # Skip yielding status for this specific failed future to avoid interrupting the flow for other successful queries.
                                continue # Skip processing this future

                            # Extract data from the worker's return dictionary
                            db_name = result_data["db_name"]
                            query_text = result_data["query_text"]
                            db_display_name = result_data["db_display_name"]
                            task_exception = result_data["exception"]
                            result = result_data["result"]
                            query_token_usage = result_data["token_usage"]
                            scope = result_data["scope"] # Get scope back from result

                            # --- Accumulate Token Usage (from this specific query) ---
                            db_stage_token_usage["prompt_tokens"] += query_token_usage.get("prompt_tokens", 0)
                            db_stage_token_usage["completion_tokens"] += query_token_usage.get("completion_tokens", 0)
                            db_stage_token_usage["total_tokens"] += query_token_usage.get("total_tokens", 0)
                            db_stage_token_usage["cost"] += query_token_usage.get("cost", 0.0)
                            # --- End Token Accumulation ---

                            # --- Debug: Record Individual Query Completion/Error ---
                            if debug_mode and debug_data is not None:
                                decision_info = {
                                    "database": db_name, "scope": scope,
                                    "result_type": type(result).__name__ if result else None,
                                    "error": str(task_exception) if task_exception else None
                                }
                                stage_name = "database_query_complete" if not task_exception else "database_query_error"
                                debug_data["decisions"].append({
                                    "stage": stage_name,
                                    "decision": decision_info,
                                    "timestamp": datetime.now().isoformat(),
                                    "token_usage": query_token_usage # Log usage for this specific query
                                })
                            # --- End Debug ---

                            # --- Yield Status Update and Aggregate Results ---
                            # Initialize status_summary earlier
                            status_summary = "❓ Unknown status (Processing error)."

                            if task_exception:
                                status_summary = f"❌ Error: {str(task_exception)}"
                                # Store error message for potential later use
                                if scope == "research":
                                    aggregated_detailed_research[db_name] = f"Error during query execution: {str(task_exception)}"
                                elif scope == "metadata":
                                    if db_name not in metadata_results_by_db: metadata_results_by_db[db_name] = []
                                    metadata_results_by_db[db_name].append({"error": str(task_exception)})
                            elif result is not None:
                                # Process successful result
                                if scope == "research":
                                    if isinstance(result, dict) and "detailed_research" in result and "status_summary" in result:
                                        status_summary = result["status_summary"]
                                        detailed_research = result["detailed_research"]
                                        aggregated_detailed_research[db_name] = detailed_research
                                    else:
                                        logger.error(f"Unexpected result type '{type(result).__name__}' for research scope from {db_name}. Expected Dict.")
                                        status_summary = "❌ Error: Received unexpected result format."
                                        aggregated_detailed_research[db_name] = f"Error: Unexpected result format: {str(result)[:200]}..."
                                elif scope == "metadata":
                                    if isinstance(result, list):
                                        logger.info(f"Received {len(result)} metadata items from {db_name}.")
                                        if db_name not in metadata_results_by_db: metadata_results_by_db[db_name] = []
                                        metadata_results_by_db[db_name].extend(result)
                                        total_metadata_items += len(result)
                                        status_summary = f"✅ Found {len(result)} items."
                                    else:
                                        logger.error(f"Unexpected result type '{type(result).__name__}' for metadata scope from {db_name}. Expected List.")
                                        status_summary = "❌ Error: Received unexpected result format."
                                        if db_name not in metadata_results_by_db: metadata_results_by_db[db_name] = []
                                        metadata_results_by_db[db_name].append({"error": "Unexpected result format"})
                            # No final 'else' needed as status_summary is initialized above

                            # Yield the status block regardless of success/failure
                            status_block = f"\n\n---\n**Database:** {db_display_name}\n**Query:** `{query_text}`\n**Status:** {status_summary}\n---"
                            yield status_block
                            # --- End Yield and Aggregation ---

                    logger.info("All concurrent database queries completed processing.")

                    # --- Debug: Store Aggregated DB Token Usage ---
                    if debug_mode and debug_data is not None:
                        # Store the total accumulated usage for the DB stage
                        debug_data["tokens"]["stages"]["database_query"] = db_stage_token_usage.copy()
                        # Add a marker decision indicating all DB queries finished processing
                        debug_data["decisions"].append({
                            "stage": "database_queries_all_completed",
                            "decision": {"total_queries": len(query_plan['queries'])},
                            "timestamp": datetime.now().isoformat(),
                            "token_usage": db_stage_token_usage.copy() # Log total usage for this stage
                        })
                    # --- End Debug ---

                    # Ensure all planned DBs have an entry in the metadata results dict if scope is metadata, even if empty or errored
                    if scope == "metadata":
                        for query_dict in query_plan["queries"]:
                            db_name = query_dict["database"]
                            if db_name not in metadata_results_by_db:
                                metadata_results_by_db[db_name] = [] # Initialize if completely missing (e.g., future.result() failed)
                # --- End Concurrent Query Execution ---

                # --- Final Summarization / Metadata Return ---
                if scope == "research":
                    if aggregated_detailed_research:
                        yield "\n\n## 📊 Research Summary\n"
                        # Start summary stage
                        if debug_mode:
                            process_monitor.start_stage("summary")
                            process_monitor.add_stage_details(
                                "summary",
                                scope=scope,
                                num_results=len(aggregated_detailed_research),
                                sources=list(aggregated_detailed_research.keys())
                            )
                        
                        # --- Legacy Debug: Record Summary Start ---
                        if debug_mode and debug_data is not None:
                            reset_token_usage()
                            debug_data["decisions"].append({"stage": "summary", "decision": {"action": "start_summary", "scope": scope, "num_results": len(aggregated_detailed_research)}, "timestamp": datetime.now().isoformat()})
                        # --- End Debug ---

                        # Assuming generate_streaming_summary is still sync generator
                        try:
                            logger.info("Calling generate_streaming_summary (assuming sync generator)")
                            summary_stream = generate_streaming_summary(aggregated_detailed_research, scope, token, original_query_plan=query_plan)
                            for summary_chunk in summary_stream:
                                 yield summary_chunk
                                 
                            # Get token usage for summary
                            summary_token_usage = get_token_usage()
                            
                            # End summary stage
                            if debug_mode:
                                process_monitor.end_stage("summary")
                                process_monitor.update_stage_tokens(
                                    "summary",
                                    prompt_tokens=summary_token_usage.get("prompt_tokens", 0),
                                    completion_tokens=summary_token_usage.get("completion_tokens", 0),
                                    total_tokens=summary_token_usage.get("total_tokens", 0),
                                    cost=summary_token_usage.get("cost", 0.0)
                                )
                        except Exception as summary_exc:
                             logger.error(f"Error during summarization: {summary_exc}", exc_info=True)
                             yield f"\n\n**Error during final summarization:** {str(summary_exc)}"
                             
                             # End summary stage with error
                             if debug_mode:
                                process_monitor.end_stage("summary", "error")
                                process_monitor.add_stage_details("summary", error=str(summary_exc))

                        # --- Legacy Debug: Record Summary Completion ---
                        if debug_mode and debug_data is not None:
                            token_usage = get_token_usage()
                            debug_data["tokens"]["stages"]["summary"] = token_usage.copy()
                            debug_data["decisions"].append({"stage": "summary", "decision": {"action": "complete_summary", "scope": scope}, "timestamp": datetime.now().isoformat(), "token_usage": token_usage.copy()})
                        # --- End Debug ---
                        yield "\n\n---"

                    completion_message = f"\nCompleted processing {len(query_plan['queries'])} database queries for scope '{scope}'.\n"
                    yield completion_message
                    logger.info(f"Completed process for scope '{scope}'")

                elif scope == "metadata":
                    # Track unique items for accurate counting
                    seen_documents = {}
                    unique_item_count = 0
                    
                    # First pass to count unique items
                    for db_name, items_list in metadata_results_by_db.items():
                        if db_name not in seen_documents:
                            seen_documents[db_name] = set()
                        
                        for item in items_list:
                            # Count error items
                            if isinstance(item, dict) and "error" in item:
                                unique_item_count += 1
                            else:
                                doc_name = item.get('document_name', 'Unknown Document')
                                # Only count if we haven't seen this document before for this database
                                if doc_name not in seen_documents[db_name]:
                                    seen_documents[db_name].add(doc_name)
                                    unique_item_count += 1
                    
                    yield f"\n\nCompleted metadata search across {len(query_plan['queries'])} databases. Found {unique_item_count} unique relevant items:\n"
                    
                    # Reset tracking for display pass
                    seen_documents = {}
                    
                    for db_name, items_list in metadata_results_by_db.items():
                        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
                        yield f"\n**{db_display_name}:**\n"
                        
                        if items_list:
                            # Initialize tracking for this database if not already done
                            if db_name not in seen_documents:
                                seen_documents[db_name] = set()
                                
                            displayed_items = 0
                            for item in items_list:
                                # Check if item is an error marker
                                if isinstance(item, dict) and "error" in item:
                                    yield f"- Error processing query for this database: {item['error']}\n"
                                    displayed_items += 1
                                else:
                                    doc_name = item.get('document_name', 'Unknown Document')
                                    # Only display if we haven't seen this document before for this database
                                    if doc_name not in seen_documents[db_name]:
                                        seen_documents[db_name].add(doc_name)
                                        doc_desc = item.get('document_description', 'No description available')
                                        yield f"- **{doc_name}:** {doc_desc}\n"
                                        displayed_items += 1
                                        
                            if displayed_items == 0:
                                yield "- No unique items found.\n"
                        else:
                            yield "- No relevant items found.\n"
                    yield "\n---" # Add a separator at the end
                    logger.info(f"Completed process for scope '{scope}', returning {total_metadata_items} items internally.")


                # --- Debug: Add Final Usage Summary ---
                if debug_mode:
                    # End overall monitoring and yield summary
                    process_monitor.end_monitoring()
                    yield process_monitor.format_summary()
                elif SHOW_USAGE_SUMMARY:
                    # Legacy usage summary if debug mode is not enabled
                    start_time = debug_data["start_timestamp"] if debug_data else None
                    final_agent_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}
                    if debug_data:
                         for stage_usage in debug_data["tokens"]["stages"].values():
                             final_agent_usage["prompt_tokens"] += stage_usage.get("prompt", 0)
                             final_agent_usage["completion_tokens"] += stage_usage.get("completion", 0)
                             final_agent_usage["total_tokens"] += stage_usage.get("total", 0)
                             final_agent_usage["cost"] += stage_usage.get("cost", 0.0)
                         # Get any usage accumulated *after* the last stage (e.g., formatting the summary itself)
                         final_usage_after_stages = get_token_usage()
                         final_agent_usage["prompt_tokens"] += final_usage_after_stages.get("prompt_tokens", 0)
                         final_agent_usage["completion_tokens"] += final_usage_after_stages.get("completion_tokens", 0)
                         final_agent_usage["total_tokens"] += final_usage_after_stages.get("total_tokens", 0)
                         final_agent_usage["cost"] += final_usage_after_stages.get("cost", 0.0)
                    else:
                         # If debug data not available, just get whatever the current global usage is
                         final_agent_usage = get_token_usage()
                    usage_summary = format_usage_summary(final_agent_usage, start_time)
                    yield usage_summary
                # --- End Debug ---

        else: # Unknown routing decision
            logger.error(f"Unknown routing function: {routing_decision['function_name']}")
            yield "Error: Unable to process query due to internal routing error."

    except Exception as e:
        error_msg = f"Critical error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Record error in process monitor
        if debug_mode:
            process_monitor.end_monitoring()
            # Add global error
            process_monitor.add_stage_details("_global", error=error_msg)
            # Yield process monitor summary
            yield process_monitor.format_summary()

        # --- Legacy Debug: Record Error ---
        if debug_mode and debug_data is not None:
            debug_data["error"] = error_msg
            debug_data["completed"] = False
            # Try to capture total usage up to the point of error
            token_usage = get_token_usage() # Get current usage
            # Sum up stage usage recorded so far
            prompt_total = sum(s.get("prompt", 0) for s in debug_data["tokens"]["stages"].values())
            completion_total = sum(s.get("completion", 0) for s in debug_data["tokens"]["stages"].values())
            cost_total = sum(s.get("cost", 0.0) for s in debug_data["tokens"]["stages"].values())
            # Add current usage (might double count last stage if error was within it, but better than nothing)
            debug_data["tokens"]["prompt"] = prompt_total + token_usage.get("prompt_tokens", 0)
            debug_data["tokens"]["completion"] = completion_total + token_usage.get("completion_tokens", 0)
            debug_data["tokens"]["total"] = debug_data["tokens"]["prompt"] + debug_data["tokens"]["completion"]
            debug_data["cost"] = cost_total + token_usage.get("cost", 0.0)
            debug_data["end_timestamp"] = datetime.now().isoformat()
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"
        # --- End Debug ---

        yield f"**Error:** {error_msg}"

    finally:
        # --- Ensure process monitoring is properly ended in all cases ---
        if debug_mode and process_monitor.enabled:
            if not hasattr(process_monitor, "end_time") or not process_monitor.end_time:
                process_monitor.end_monitoring()

        # --- Legacy Debug: Final Yield ---
        if debug_mode and debug_data is not None and not debug_data.get("error"):
            debug_data["completed"] = True
            # Calculate final totals from stages if not already done by error block
            if "end_timestamp" not in debug_data: # Check if error block already calculated totals
                final_agent_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}
                for stage_usage in debug_data["tokens"]["stages"].values():
                     final_agent_usage["prompt_tokens"] += stage_usage.get("prompt", 0)
                     final_agent_usage["completion_tokens"] += stage_usage.get("completion", 0)
                     final_agent_usage["total_tokens"] += stage_usage.get("total", 0)
                     final_agent_usage["cost"] += stage_usage.get("cost", 0.0)
                # Add any final usage after last stage
                final_usage_after_stages = get_token_usage()
                final_agent_usage["prompt_tokens"] += final_usage_after_stages.get("prompt_tokens", 0)
                final_agent_usage["completion_tokens"] += final_usage_after_stages.get("completion_tokens", 0)
                final_agent_usage["total_tokens"] += final_usage_after_stages.get("total_tokens", 0)
                final_agent_usage["cost"] += final_usage_after_stages.get("cost", 0.0)

                debug_data["tokens"]["prompt"] = final_agent_usage["prompt_tokens"]
                debug_data["tokens"]["completion"] = final_agent_usage["completion_tokens"]
                debug_data["tokens"]["total"] = final_agent_usage["total_tokens"]
                debug_data["cost"] = final_agent_usage["cost"]
                debug_data["end_timestamp"] = datetime.now().isoformat()
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"
        # --- End Legacy Debug ---

        reset_token_usage()


# --- Synchronous Wrapper Function ---
def model(conversation: Optional[Dict[str, Any]] = None,
          html_callback: Optional[callable] = None,
           debug_mode: bool = False) -> Generator[str, None, None]:
    """
    Synchronous wrapper for the model generator.

    This function runs the `_model_generator` and yields its results,
    making it compatible with synchronous calling code.

    Args:
        conversation (dict, optional): Conversation in OpenAI format.
        html_callback (callable, optional): Unused callback.
        debug_mode (bool, optional): Enables debug data tracking.

    Returns:
        generator: A standard generator yielding response chunks as strings.
    """
    logger = logging.getLogger(__name__) # Ensure logger is available
    logger.debug("Entering synchronous model wrapper.")

    # Directly iterate over the synchronous generator
    try:
        sync_gen = _model_generator(conversation, html_callback, debug_mode)
        for chunk in sync_gen:
            yield chunk
        logger.debug("Synchronous generator completed.")
    except Exception as e:
        # Catch any exceptions raised during the generator's execution
        error_msg = f"Error during synchronous model execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield f"**Error:** {error_msg}"


# --- Helper Function (Remains Synchronous) ---
def format_remaining_queries(remaining_queries: List[Dict[str, Any]]) -> str:
    """Format remaining queries for display to the user."""
    # ... (implementation remains the same) ...
    if not remaining_queries:
        return "" # Return empty string if none remain

    available_databases = get_available_databases()
    message = "## ⏸️ Remaining Queries\n\n"
    message += "The following database queries were not processed:\n\n"
    for i, query in enumerate(remaining_queries, 1):
        db_name = query["database"]
        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
        message += f"**{i}.** {db_display_name}: {query['query']}\n\n"

    message += "\nPlease let me know if you would like to continue with these remaining database queries in a new search."
    return message
