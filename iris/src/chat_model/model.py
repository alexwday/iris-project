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
import uuid # Import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Generator

# ... (Keep existing imports) ...
from ..global_prompts.database_statement import get_available_databases
# Import the connector, but not the removed usage functions
from ..llm_connectors.rbc_openai import call_llm # Assuming this is the correct import now

# Import sync version of route_query
from ..agents.database_subagents.database_router import route_query_sync


# --- Formatting Function (Remains Synchronous) ---
# This function might need adjustment later if debug_data structure changes significantly
def format_usage_summary(
    agent_token_usage: Dict[str, Any], start_time: Optional[str] = None
) -> str:
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
            logging.getLogger().warning(
                f"Could not parse start_time for duration calculation: {start_time}"
            )
            duration = None

    usage_summary = "\n\n---\n"
    usage_summary += "## Agent Usage Statistics\n\n"
    usage_summary += (
        f"- Overall Input tokens: {agent_token_usage.get('prompt_tokens', 0)}\n"
    )
    usage_summary += (
        f"- Overall Output tokens: {agent_token_usage.get('completion_tokens', 0)}\n"
    )
    usage_summary += (
        f"- Overall Total tokens: {agent_token_usage.get('total_tokens', 0)}\n"
    )
    usage_summary += f"- Overall Cost: ${agent_token_usage.get('cost', 0.0):.6f}\n"
    if duration is not None:
        usage_summary += f"- Total Time: {duration:.2f} seconds\n"

    return usage_summary


# --- Worker Function for Threaded Query Execution ---
def _execute_query_worker(
    db_name: str,
    query_text: str,
    scope: str,
    token: str,
    db_display_name: str,
    query_index: int,
    total_queries: int,
    # debug_mode: bool = False, # Removed
) -> Dict[str, Any]:
    """
    Worker function executed by each thread to run a single database query. Always monitors.
    """
    logger = logging.getLogger(__name__)
    result = None
    task_exception = None

    from ..initial_setup.process_monitor import get_process_monitor
    process_monitor = get_process_monitor()
    query_stage_name = f"db_query_{db_name}_{query_index}"

    process_monitor.start_stage(query_stage_name)
    process_monitor.add_stage_details(
        query_stage_name,
        db_name=db_name,
        db_display_name=db_display_name,
        query_text=query_text,
        scope=scope,
        query_index=query_index,
        total_queries=total_queries,
    )

    try:
        logger.info(
            f"Thread executing query {query_index + 1}/{total_queries} for database: {db_name}"
        )
        # Assume route_query_sync handles its own LLM calls and logging internally
        # It now returns a tuple: (result, doc_ids)
        # Pass the process_monitor instance and the specific stage name to the router
        result_tuple = route_query_sync(db_name, query_text, scope, token, process_monitor=process_monitor, query_stage_name=query_stage_name) # ADDED query_stage_name
        result, doc_ids = result_tuple # Unpack the tuple
        logger.info(f"Thread completed query for database: {db_name}")
        # End the stage for this specific query worker instance successfully
        process_monitor.end_stage(query_stage_name) # RESTORED end_stage call here

        # Add result details
        if scope == "metadata" and isinstance(result, list):
            process_monitor.add_stage_details(
                query_stage_name,
                result_count=len(result),
                document_names=[item.get("document_name", "Unnamed") for item in result[:10]],
                has_more_documents=len(result) > 10,
            )
        elif scope == "research" and isinstance(result, dict):
            process_monitor.add_stage_details(
                query_stage_name,
                status_summary=result.get("status_summary", "No status provided"),
                has_detailed_research=bool(result.get("detailed_research")),
            )
        # Add document IDs to details if they were returned
        if doc_ids is not None: # Check if doc_ids is not None (could be empty list)
             process_monitor.add_stage_details(query_stage_name, document_ids=doc_ids)

    except Exception as e:
        task_exception = e
        logger.error(
            f"Thread error executing query for {db_name}: {str(e)}", exc_info=True
        )
        # Ensure stage is ended with error status in case of exception
        process_monitor.end_stage(query_stage_name, "error") # Ensure this is called on error
        process_monitor.add_stage_details(query_stage_name, error=str(e))

    # Return dictionary without token_usage
    return {
        "db_name": db_name,
        "query_text": query_text,
        "scope": scope,
        "db_display_name": db_display_name,
        "query_index": query_index,
        "total_queries": total_queries,
        "result": result,
        "exception": task_exception,
    }


# --- Main Synchronous Core Function ---
def _model_generator(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[callable] = None,
    debug_mode: bool = False, # Keep debug_mode for legacy debug dict
) -> Generator[str, None, None]:
    """
    Core synchronous generator handling the agent workflow.
    """
    from ..initial_setup.process_monitor import enable_monitoring, get_process_monitor
    
    # Add more logging around the process monitoring setup
    logger = logging.getLogger(__name__)
    logger.info("Setting up process monitoring")
    
    enable_monitoring(True)
    process_monitor = get_process_monitor()
    
    # Check if process_monitor is enabled
    logger.info(f"Process monitor enabled after enable_monitoring call: {process_monitor.enabled}")
    
    run_uuid_val = uuid.uuid4()
    logger.info(f"Generated run UUID: {run_uuid_val}")
    
    process_monitor.set_run_uuid(run_uuid_val)
    logger.info(f"Set run UUID. Current run UUID: {process_monitor.run_uuid}")
    
    process_monitor.start_monitoring()
    logger.info(f"Started monitoring. Start time: {process_monitor.start_time}")

    # Initialize legacy debug tracking (structure might be inaccurate now)
    debug_data = None
    if debug_mode:
        # This legacy structure is likely inaccurate now and should be reviewed/removed later
        debug_data = {
            "decisions": [], "tokens": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0, "stages": {}},
            "start_timestamp": datetime.now().isoformat(), "error": None, "completed": False,
        }

    from ..agents.agent_clarifier.clarifier import clarify_research_needs
    from ..agents.agent_direct_response.response_from_conversation import response_from_conversation
    from ..agents.agent_planner.planner import create_database_selection_plan
    from ..agents.agent_router.router import get_routing_decision
    from ..agents.agent_summarizer.summarizer import generate_streaming_summary
    from ..conversation_setup.conversation import process_conversation
    from ..initial_setup.logging_config import configure_logging
    from ..initial_setup.oauth.oauth import setup_oauth
    from ..initial_setup.ssl.ssl import setup_ssl
    from .model_settings import SHOW_USAGE_SUMMARY
    # Import DB connection utility (assuming it exists and named get_db_connection)
    from ..initial_setup.db_config import connect_to_db, ENVIRONMENT # Import necessary items

    logger = configure_logging()
    db_conn = None
    db_cursor = None

    try:
        logger.info("Initializing model setup (sync core)...")

        process_monitor.start_stage("ssl_setup")
        cert_path = setup_ssl()
        process_monitor.end_stage("ssl_setup")
        process_monitor.add_stage_details("ssl_setup", cert_path=cert_path)

        process_monitor.start_stage("oauth_setup")
        token = setup_oauth()
        process_monitor.end_stage("oauth_setup")
        process_monitor.add_stage_details("oauth_setup", token_length=len(token) if token else 0)

        if not conversation:
            logger.warning("No conversation provided.")
            yield "Model initialized, but no conversation provided to process."
            return

        process_monitor.start_stage("conversation_processing")
        try:
            processed_conversation = process_conversation(conversation)
            logger.info(f"Conversation processed: {len(processed_conversation['messages'])} messages")
        except ValueError as e:
            logger.warning(f"Invalid conversation format: {str(e)}")
            yield f"Model initialized, but conversation format is invalid: {str(e)}"
            return
        except Exception as e:
            logger.error(f"Error processing conversation: {str(e)}")
            yield f"Error processing conversation: {str(e)}"
            return

        if not processed_conversation["messages"]:
            logger.warning("Processed conversation is empty.")
            yield "Model initialized, but processed conversation is empty."
            return

        process_monitor.end_stage("conversation_processing")
        process_monitor.add_stage_details("conversation_processing", message_count=len(processed_conversation["messages"]))

        process_monitor.start_stage("router")
        logger.info("Getting routing decision...")
        # TODO: Update get_routing_decision to return (decision, usage_details)
        routing_decision, router_usage_details = get_routing_decision(processed_conversation, token)
        process_monitor.end_stage("router")
        if router_usage_details:
            process_monitor.add_llm_call_details_to_stage("router", router_usage_details)
        process_monitor.add_stage_details("router", function_name=routing_decision.get("function_name"), decision=routing_decision)

        # --- Legacy Debug Block Removed ---

        if routing_decision["function_name"] == "response_from_conversation":
            logger.info("Using direct response path based on routing decision")
            process_monitor.start_stage("direct_response")
            # TODO: Update response_from_conversation to yield usage details at the end
            direct_response_usage_details = None
            stream_iterator = response_from_conversation(processed_conversation, token)
            for chunk in stream_iterator:
                if isinstance(chunk, dict) and 'usage_details' in chunk:
                    direct_response_usage_details = chunk['usage_details']
                else:
                    yield chunk
            process_monitor.end_stage("direct_response")
            if direct_response_usage_details:
                 process_monitor.add_llm_call_details_to_stage("direct_response", direct_response_usage_details)
            else:
                 logger.warning("No usage details received from direct_response stream.")

            # --- Legacy Debug Block Removed ---

        elif routing_decision["function_name"] == "research_from_database":
            logger.info("Using research path based on routing decision")
            process_monitor.start_stage("clarifier")
            logger.info("Clarifying research needs...")
            # TODO: Update clarify_research_needs to return (decision, usage_details)
            clarifier_decision, clarifier_usage_details = clarify_research_needs(processed_conversation, token)
            process_monitor.end_stage("clarifier")
            if clarifier_usage_details:
                 process_monitor.add_llm_call_details_to_stage("clarifier", clarifier_usage_details)
            process_monitor.add_stage_details("clarifier", action=clarifier_decision.get("action"), scope=clarifier_decision.get("scope"), is_continuation=clarifier_decision.get("is_continuation", False), decision=clarifier_decision)

            # --- Legacy Debug Block Removed ---

            if clarifier_decision["action"] == "request_essential_context":
                logger.info("Essential context needed, returning context questions")
                questions = clarifier_decision["output"].strip()
                yield "Before proceeding with research, please clarify:\n\n" + questions
            else:
                research_statement = clarifier_decision.get("output", "")
                scope = clarifier_decision.get("scope")
                is_continuation = clarifier_decision.get("is_continuation", False)
                if not scope:
                    logger.error("Scope missing from clarifier decision.")
                    yield "Error: Internal configuration error - missing research scope."
                    return

                logger.info(f"Research scope determined: {scope}")
                process_monitor.start_stage("planner")
                logger.info("Creating database selection plan...")
                # TODO: Update create_database_selection_plan to return (plan, usage_details)
                db_selection_plan, planner_usage_details = create_database_selection_plan(research_statement, token, is_continuation)
                selected_databases = db_selection_plan.get("databases", [])
                logger.info(f"Database selection plan created with {len(selected_databases)} databases: {selected_databases}")
                process_monitor.end_stage("planner")
                if planner_usage_details:
                     process_monitor.add_llm_call_details_to_stage("planner", planner_usage_details)
                process_monitor.add_stage_details("planner", database_count=len(selected_databases), selected_databases=selected_databases, decision=db_selection_plan)

                # --- Legacy Debug Block Removed ---

                # Display plan...
                available_databases = get_available_databases()
                if scope == "metadata": yield "---\n# 🔍 File Search Plan\n\n"; yield f"## Search Criteria\n{research_statement}\n\n"
                else: yield "---\n# 📋 Research Plan\n\n"; yield f"## Research Statement\n{research_statement}\n\n"
                selected_db_display_names = [available_databases.get(db_name, {}).get("name", db_name) for db_name in selected_databases]
                if selected_db_display_names:
                    if len(selected_db_display_names) == 1: names_str = selected_db_display_names[0]
                    elif len(selected_db_display_names) == 2: names_str = f"{selected_db_display_names[0]} and {selected_db_display_names[1]}"
                    else: names_str = ", ".join(selected_db_display_names[:-1]) + f", and {selected_db_display_names[-1]}"
                    yield f"Searching the following databases using the full research statement: {names_str}.\n\n---\n"
                else: yield "No databases selected for search.\n\n---\n"
                logger.info("Displayed database selection plan.")

                if not selected_databases:
                    logger.warning("Database selection plan is empty, skipping database search.")
                else:
                    logger.info(f"Starting {len(selected_databases)} database queries concurrently...")
                    aggregated_detailed_research = {}
                    metadata_results_by_db: Dict[str, List[Dict[str, Any]]] = {}
                    total_metadata_items = 0
                    futures = []

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for i, db_name in enumerate(selected_databases):
                            query_text = research_statement
                            db_display_name = available_databases.get(db_name, {}).get("name", db_name)
                            if i > 0: time.sleep(1)
                            future = executor.submit(_execute_query_worker, db_name, query_text, scope, token, db_display_name, i, len(selected_databases))
                            futures.append(future)
                        logger.info(f"Submitted {len(futures)} queries to thread pool.")

                        for future in concurrent.futures.as_completed(futures):
                            try: result_data = future.result()
                            except Exception as exc: logger.error(f"Error retrieving result from future: {exc}", exc_info=True); continue
                            db_name = result_data["db_name"]
                            db_display_name = result_data["db_display_name"]
                            task_exception = result_data["exception"]
                            result = result_data["result"]
                            scope = result_data["scope"]

                            # --- Legacy Debug Block Removed ---

                            # Aggregate results and yield status...
                            status_summary = "❓ Unknown status (Processing error)."
                            if task_exception:
                                status_summary = f"❌ Error: {str(task_exception)}"
                                if scope == "research": aggregated_detailed_research[db_name] = f"Error: {str(task_exception)}"
                                elif scope == "metadata": metadata_results_by_db.setdefault(db_name, []).append({"error": str(task_exception)})
                            elif result is not None:
                                if scope == "research":
                                    if isinstance(result, dict) and "detailed_research" in result and "status_summary" in result:
                                        status_summary = result["status_summary"]; aggregated_detailed_research[db_name] = result["detailed_research"]
                                    else: status_summary = "❌ Error: Unexpected result format."; aggregated_detailed_research[db_name] = f"Error: {str(result)[:200]}..."
                                elif scope == "metadata":
                                    if isinstance(result, list):
                                        metadata_results_by_db.setdefault(db_name, []).extend(result); total_metadata_items += len(result); status_summary = f"✅ Found {len(result)} items."
                                    else: status_summary = "❌ Error: Unexpected result format."; metadata_results_by_db.setdefault(db_name, []).append({"error": "Unexpected format"})
                            status_block = f"**Database:** {db_display_name}\n**Status:** {status_summary}\n---\n"
                            yield status_block

                    logger.info("All concurrent database queries completed processing.")
                    # --- Legacy Debug Block Removed ---
                    if scope == "metadata":
                        for db_name in selected_databases: metadata_results_by_db.setdefault(db_name, [])

                if scope == "research":
                    if aggregated_detailed_research:
                        yield "\n\n---\n"; yield "\n\n## 📊 Research Summary\n"
                        process_monitor.start_stage("summary")
                        process_monitor.add_stage_details("summary", scope=scope, num_results=len(aggregated_detailed_research), sources=list(aggregated_detailed_research.keys()))
                        # --- Legacy Debug Block Removed ---
                        try:
                            logger.info("Calling generate_streaming_summary")
                            # TODO: Update generate_streaming_summary to yield usage details
                            summary_usage_details = None
                            summary_stream = generate_streaming_summary(aggregated_detailed_research, scope, token)
                            for chunk in summary_stream:
                                if isinstance(chunk, dict) and 'usage_details' in chunk: summary_usage_details = chunk['usage_details']
                                else: yield chunk
                            process_monitor.end_stage("summary")
                            if summary_usage_details: process_monitor.add_llm_call_details_to_stage("summary", summary_usage_details)
                            else: logger.warning("No usage details received from summary stream.")
                        except Exception as summary_exc:
                            logger.error(f"Error during summarization: {summary_exc}", exc_info=True)
                            yield f"\n\n**Error during final summarization:** {str(summary_exc)}"
                            process_monitor.end_stage("summary", "error")
                            process_monitor.add_stage_details("summary", error=str(summary_exc))
                        # --- Legacy Debug Block Removed ---
                        yield "\n\n---"
                    completion_message = f"\nCompleted processing {len(selected_databases)} database queries for scope '{scope}'.\n"
                    yield completion_message
                    logger.info(f"Completed process for scope '{scope}'")
                elif scope == "metadata":
                    # Metadata display logic...
                    seen_documents = {}; unique_item_count = 0
                    for db_name, items_list in metadata_results_by_db.items():
                        seen_documents.setdefault(db_name, set())
                        for item in items_list:
                            if isinstance(item, dict) and "error" in item: unique_item_count += 1
                            else: doc_name = item.get("document_name", "Unknown");
                            if doc_name not in seen_documents[db_name]: seen_documents[db_name].add(doc_name); unique_item_count += 1
                    yield f"\n\nCompleted metadata search across {len(selected_databases)} databases. Found {unique_item_count} unique relevant items:\n"
                    seen_documents = {}
                    for db_name, items_list in metadata_results_by_db.items():
                        db_display_name = available_databases.get(db_name, {}).get("name", db_name); yield f"\n**{db_display_name}:**\n"
                        if items_list:
                            seen_documents.setdefault(db_name, set()); displayed_items = 0
                            for item in items_list:
                                if isinstance(item, dict) and "error" in item: yield f"- Error: {item['error']}\n"; displayed_items += 1
                                else: doc_name = item.get("document_name", "Unknown");
                                if doc_name not in seen_documents[db_name]:
                                    seen_documents[db_name].add(doc_name); doc_desc = item.get("document_description", "No description"); yield f"- **{doc_name}:** {doc_desc}\n"; displayed_items += 1
                            if displayed_items == 0: yield "- No unique items found.\n"
                        else: yield "- No relevant items found.\n"
                    yield "\n---"
                    logger.info(f"Completed process for scope '{scope}', returning {total_metadata_items} items internally.")

                # --- Legacy Debug Block Removed ---
        else:
            logger.error(f"Unknown routing function: {routing_decision['function_name']}")
            yield "Error: Unable to process query due to internal routing error."

    except Exception as e:
        error_msg = f"Critical error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if process_monitor.enabled and (not hasattr(process_monitor, "end_time") or not process_monitor.end_time):
            process_monitor.end_monitoring()
        process_monitor.add_stage_details("_global", error=error_msg)
        # --- Legacy Debug Block Removed ---
        yield f"**Error:** {error_msg}"

    finally:
        if process_monitor.enabled and (not hasattr(process_monitor, "end_time") or not process_monitor.end_time):
             logger.warning("Process monitoring end_time was not set before finally block, setting now.")
             process_monitor.end_monitoring()

        # --- Database Logging Call ---
        if process_monitor.enabled:
            try:
                # Use the imported connect_to_db function
                logger.info(f"Attempting to log process monitor data to database for run {process_monitor.run_uuid}")
                logger.info(f"Total stages to log: {len(process_monitor.stages)}")
                # Show ENVIRONMENT value
                logger.info(f"Using environment: {ENVIRONMENT}")
                
                db_conn = connect_to_db(ENVIRONMENT)
                if db_conn:
                    logger.info("Database connection established")
                    # Check if table exists
                    with db_conn.cursor() as check_cursor:
                        check_cursor.execute("""
                            SELECT EXISTS (
                               SELECT FROM information_schema.tables 
                               WHERE table_schema = 'public'
                               AND table_name = 'process_monitor_logs'
                            );
                        """)
                        table_exists = check_cursor.fetchone()[0]
                        logger.info(f"process_monitor_logs table exists: {table_exists}")
                    
                    # Try to log to the database
                    with db_conn.cursor() as db_cursor:
                        process_monitor.log_to_database(db_cursor)
                        db_conn.commit() # Commit transaction
                    logger.info("Process monitor data logged to database.")
                else:
                    logger.error(f"Failed to get database connection for logging process monitor data. Environment: {ENVIRONMENT}")
            except Exception as log_exc:
                logger.error(f"Failed to log process monitor data to database: {log_exc}", exc_info=True)
                # Rollback if connection object available
                if db_conn:
                    try: db_conn.rollback()
                    except Exception as rb_exc: logger.error(f"Error during DB rollback: {rb_exc}")
            finally:
                # Close connection if obtained
                if db_conn:
                    try: db_conn.close()
                    except Exception as close_exc: logger.error(f"Error closing DB connection: {close_exc}")

        # --- Legacy Debug: Final Yield ---
        if debug_mode and debug_data is not None and not debug_data.get("error"):
            # This legacy data is likely inaccurate now
            debug_data["completed"] = True
            if "end_timestamp" not in debug_data:
                # Simplified calculation based on potentially incomplete stage data
                final_agent_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}
                # This loop might fail if stages structure changed
                try:
                    for stage_usage in debug_data.get("tokens", {}).get("stages", {}).values():
                        final_agent_usage["prompt_tokens"] += stage_usage.get("prompt", 0)
                        final_agent_usage["completion_tokens"] += stage_usage.get("completion", 0)
                        final_agent_usage["total_tokens"] += stage_usage.get("total", 0)
                        final_agent_usage["cost"] += stage_usage.get("cost", 0.0)
                    debug_data["tokens"]["prompt"] = final_agent_usage["prompt_tokens"]
                    debug_data["tokens"]["completion"] = final_agent_usage["completion_tokens"]
                    debug_data["tokens"]["total"] = final_agent_usage["total_tokens"]
                    debug_data["cost"] = final_agent_usage["cost"]
                except Exception:
                    logger.warning("Could not calculate legacy debug token totals.")
                debug_data["end_timestamp"] = datetime.now().isoformat()
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"
        # --- End Legacy Debug ---

        # reset_token_usage() # Removed


# --- Synchronous Wrapper Function ---
def model(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[callable] = None,
    debug_mode: bool = False, # Keep debug_mode for legacy dict
) -> Generator[str, None, None]:
    """
    Synchronous wrapper for the model generator.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Entering synchronous model wrapper.")
    try:
        sync_gen = _model_generator(conversation, html_callback, debug_mode)
        for chunk in sync_gen:
            yield chunk
        logger.debug("Synchronous generator completed.")
    except Exception as e:
        error_msg = f"Error during synchronous model execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield f"**Error:** {error_msg}"


# --- Helper Function (Remains Synchronous) ---
def format_remaining_queries(remaining_queries: List[Dict[str, Any]]) -> str:
    """Format remaining queries for display to the user."""
    if not remaining_queries: return ""
    available_databases = get_available_databases()
    message = "## ⏸️ Remaining Queries\n\n"
    message += "The following database queries were not processed:\n\n"
    for i, query in enumerate(remaining_queries, 1):
        db_name = query["database"]
        db_display_name = available_databases.get(db_name, {}).get("name", db_name)
        message += f"**{i}.** {db_display_name}: {query['query']}\n\n"
    message += "\nPlease let me know if you would like to continue with these remaining database queries in a new search."
    return message
