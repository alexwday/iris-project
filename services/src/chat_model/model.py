"""
Model Initialization and Setup Module.

This module serves as the main entry point for the IRIS application,
handling conversation processing, agent orchestration, and response generation.
Uses synchronous core with multi-threaded database queries for optimal performance.

Functions:
    model: Main entry point that processes conversations and yields streaming responses.
    _model_generator: Core generator handling the agent workflow.
    _execute_query_worker: Worker function for parallel database queries.
    format_usage_summary: Formats token usage and timing information.
    process_request_async: Async wrapper for FastAPI integration.

Architecture:
    - Router: Determines whether to use direct response or research path
    - Clarifier: Refines research requirements and checks for missing context
    - Planner: Selects which databases to query based on research needs
    - Database Subagents: Execute queries using cascading retrieval architecture
    - Summarizer: Synthesizes results from multiple databases into coherent response

Dependencies:
    - SSL certificate setup and OAuth authentication
    - PostgreSQL for process monitoring and document storage
    - OpenAI API for LLM interactions
    - Cascading retrieval architecture (Metadata -> File Research)
"""

import concurrent.futures
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Generator, Callable, Tuple

from ..agent.tools.database_metadata import get_available_databases
from ..agent.tools.database_router import route_query_cascading
from ..utils.env_config import config
from ..utils.reference_processor import (
    build_master_reference_index,
    process_final_references,
    process_reference_buffer,
)
from sqlalchemy import text
from ..connections.postgres import get_session


def format_usage_summary(
    agent_token_usage: Dict[str, Any], start_time: Optional[str] = None
) -> str:
    """
    Format token usage and timing information into a markdown summary.

    Args:
        agent_token_usage: Accumulated token usage dictionary with keys like
            'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost'.
        start_time: ISO format timestamp of when processing started.

    Returns:
        Formatted usage summary as markdown string.
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


def _execute_query_worker(
    db_name: str,
    query_text: str,
    token: str,
    db_display_name: str,
    query_index: int,
    total_queries: int,
    query_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a single database query in a thread pool worker.

    Uses unified cascading retrieval architecture where metadata subagent makes
    3-way per-document decisions (answered/irrelevant/needs_deep_research),
    triggering file research only for documents that need it.

    Args:
        db_name: Internal name of the database.
        query_text: The search query to execute.
        token: OAuth token for API authentication.
        db_display_name: Human-readable database name for display.
        query_index: Index of this query in the batch (0-based).
        total_queries: Total number of queries being executed.
        query_context: Context dict containing research_statement, query_embedding.

    Returns:
        Dictionary containing query results, exceptions, file links, references, and metadata.
        Keys include: db_name, query_text, result, exception, file_links, page_section_refs,
        section_content_map, reference_index.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    result = None
    task_exception = None

    from ..utils.process_monitoring import get_process_monitor

    process_monitor = get_process_monitor()
    query_stage_name = f"db_query_{db_name}_{query_index}"

    process_monitor.start_stage(query_stage_name)
    process_monitor.add_stage_details(
        query_stage_name,
        db_name=db_name,
        db_display_name=db_display_name,
        query_text=query_text,
        query_index=query_index,
        total_queries=total_queries,
    )

    try:
        logger.info(
            f"Thread executing query {query_index + 1}/{total_queries} for database: {db_name}"
        )
        if query_context is None:
            query_context = {
                "research_statement": query_text,
            }

        result_tuple = route_query_cascading(
            database=db_name,
            token=token,
            process_monitor=process_monitor,
            query_stage_name=query_stage_name,
            query_context=query_context,
        )

        if len(result_tuple) == 6:
            (
                result,
                doc_ids,
                file_links,
                page_section_refs,
                section_content_map,
                reference_index,
            ) = result_tuple
        elif len(result_tuple) == 5:
            result, doc_ids, file_links, page_section_refs, section_content_map = (
                result_tuple
            )
            reference_index = None
        elif len(result_tuple) == 4:
            result, doc_ids, file_links, page_section_refs = result_tuple
            section_content_map = None
            reference_index = None
        elif len(result_tuple) == 3:
            result, doc_ids, file_links = result_tuple
            page_section_refs = None
            section_content_map = None
            reference_index = None
        elif len(result_tuple) == 2:
            result, doc_ids = result_tuple
            file_links = None
            page_section_refs = None
            section_content_map = None
            reference_index = None
        else:
            logger.error(
                f"Unexpected tuple length {len(result_tuple)} from route_query_cascading for {db_name}"
            )
            if len(result_tuple) > 0:
                result = result_tuple[0]
            else:
                result = {
                    "detailed_research": f"Error: Invalid response format from {db_name}",
                    "status_summary": f"❌ Error: Query failed for '{db_name}'.",
                }
            doc_ids = None
            file_links = None
            page_section_refs = None
            section_content_map = None
            reference_index = None
        logger.info(f"Thread completed query for database: {db_name}")
        process_monitor.end_stage(query_stage_name)

        if isinstance(result, dict):
            process_monitor.add_stage_details(
                query_stage_name,
                status_summary=result.get("status_summary", "No status provided"),
                has_detailed_research=bool(result.get("detailed_research")),
            )
        if doc_ids is not None:
            process_monitor.add_stage_details(query_stage_name, document_ids=doc_ids)

    except Exception as e:
        task_exception = e
        logger.error(
            f"Thread error executing query for {db_name}: {str(e)}", exc_info=True
        )
        process_monitor.end_stage(query_stage_name, "error")
        process_monitor.add_stage_details(query_stage_name, error=str(e))

    finally:
        try:
            import gc

            gc.collect()
        except Exception as cleanup_exc:
            logger.warning(f"Error during worker cleanup: {cleanup_exc}")

    return {
        "db_name": db_name,
        "query_text": query_text,
        "db_display_name": db_display_name,
        "query_index": query_index,
        "total_queries": total_queries,
        "result": result,
        "exception": task_exception,
        "file_links": file_links if "file_links" in locals() else None,
        "page_section_refs": (
            page_section_refs if "page_section_refs" in locals() else None
        ),
        "section_content_map": (
            section_content_map if "section_content_map" in locals() else None
        ),
        "reference_index": reference_index if "reference_index" in locals() else None,
    }


def _model_generator(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[Callable] = None,
    debug_mode: bool = False,
    db_names: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """
    Core synchronous generator handling the complete agent workflow.

    Orchestrates the full IRIS pipeline: conversation processing, routing decisions,
    research planning, parallel database queries, and response generation. Implements
    process monitoring for performance tracking and debugging.

    Args:
        conversation: Dictionary with 'messages' key containing conversation history.
        html_callback: Optional callback for HTML rendering (deprecated).
        debug_mode: If True, yields legacy debug data at end of stream.
        db_names: Optional list of database names to filter/restrict queries to.

    Yields:
        String chunks of the streaming response, including research plans, status updates,
        and final synthesized answers. If debug_mode is True, yields DEBUG_DATA JSON at end.

    Raises:
        Exception: Critical errors are caught, logged, and yielded as error messages.
    """
    from ..utils.process_monitoring import (
        enable_monitoring,
        get_process_monitor,
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    enable_monitoring(True)
    process_monitor = get_process_monitor()
    run_uuid_val = uuid.uuid4()
    process_monitor.set_run_uuid(run_uuid_val)
    process_monitor.start_monitoring()

    debug_data = None
    if debug_mode:
        debug_data = {
            "decisions": [],
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0,
                "cost": 0.0,
                "stages": {},
            },
            "start_timestamp": datetime.now().isoformat(),
            "error": None,
            "completed": False,
        }

    from ..agent.clarifier import clarify_research_needs
    from ..agent.direct_response import response_from_conversation
    from ..agent.planner import create_database_selection_plan
    from ..agent.router import get_routing_decision
    from ..agent.summarizer import generate_streaming_summary
    from ..utils.input_sanitizer import process_conversation
    from ..utils.logging_format import configure_logging
    from ..connections.oauth import setup_oauth
    from ..utils.rbc_security import setup_ssl

    SHOW_USAGE_SUMMARY = config.SHOW_USAGE_SUMMARY
    logger = configure_logging()

    try:
        logger.info("Initializing model...")

        process_monitor.start_stage("ssl_setup")
        cert_path = setup_ssl()
        process_monitor.end_stage("ssl_setup")
        process_monitor.add_stage_details("ssl_setup", cert_path=cert_path)

        process_monitor.start_stage("oauth_setup")
        token = setup_oauth()
        process_monitor.end_stage("oauth_setup")
        process_monitor.add_stage_details(
            "oauth_setup", token_length=len(token) if token else 0
        )

        if not conversation:
            logger.warning("No conversation provided.")
            yield "Model initialized, but no conversation provided to process."
            return

        process_monitor.start_stage("conversation_processing")
        try:
            processed_conversation = process_conversation(conversation)
            logger.info(
                f"Conversation processed: {len(processed_conversation['messages'])} messages"
            )
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
        process_monitor.add_stage_details(
            "conversation_processing",
            message_count=len(processed_conversation["messages"]),
        )

        from ..agent.tools.database_metadata import get_available_databases

        available_databases = get_available_databases()
        if db_names is not None:
            logger.info(f"Filtering databases to: {db_names}")
            available_databases = {
                k: v for k, v in available_databases.items() if k in db_names
            }

        process_monitor.start_stage("router")
        logger.info("Getting routing decision...")
        routing_decision, router_usage_details = get_routing_decision(
            processed_conversation, token, available_databases
        )
        process_monitor.end_stage("router")
        if router_usage_details:
            process_monitor.add_llm_call_details_to_stage(
                "router", router_usage_details
            )
        process_monitor.add_stage_details(
            "router",
            function_name=routing_decision.get("function_name"),
            decision=routing_decision,
        )

        if routing_decision["function_name"] == "response_from_conversation":
            logger.info("Using direct response path")
            process_monitor.start_stage("direct_response")
            direct_response_usage_details = None
            stream_iterator = response_from_conversation(
                processed_conversation, token, available_databases
            )
            for chunk in stream_iterator:
                if isinstance(chunk, dict) and "usage_details" in chunk:
                    direct_response_usage_details = chunk["usage_details"]
                else:
                    yield chunk
            process_monitor.end_stage("direct_response")
            if direct_response_usage_details:
                process_monitor.add_llm_call_details_to_stage(
                    "direct_response", direct_response_usage_details
                )
            else:
                logger.debug("No usage details received from direct_response stream")

            logger.debug("Direct response completed, ending monitoring")
            process_monitor.end_monitoring()

        elif routing_decision["function_name"] == "research_from_database":
            logger.info("Using research path")
            process_monitor.start_stage("clarifier")
            logger.info("Clarifying research needs...")
            clarifier_decision, clarifier_usage_details = clarify_research_needs(
                processed_conversation, token, available_databases
            )
            process_monitor.end_stage("clarifier")
            if clarifier_usage_details:
                process_monitor.add_llm_call_details_to_stage(
                    "clarifier", clarifier_usage_details
                )
            process_monitor.add_stage_details(
                "clarifier",
                action=clarifier_decision.get("action"),
                decision=clarifier_decision,
            )

            if clarifier_decision["action"] == "request_essential_context":
                logger.info("Essential context needed")
                questions = clarifier_decision["output"].strip()
                yield "Before proceeding with research, please clarify:\n\n" + questions

                logger.debug("Context request completed, ending monitoring")
                process_monitor.end_monitoring()

            elif clarifier_decision["action"] == "request_deep_research_approval":
                logger.info("DB-wide query detected, requesting approval")
                approval_message = clarifier_decision["output"].strip()
                yield approval_message

                logger.debug("Approval request completed, ending monitoring")
                process_monitor.end_monitoring()

            else:
                # action == "create_research_statement"
                research_statement = clarifier_decision.get("output", "")
                is_db_wide = clarifier_decision.get("is_db_wide", False)
                deep_research_approved = clarifier_decision.get(
                    "deep_research_approved", False
                )

                logger.info(
                    f"Research statement: {research_statement[:100]}... "
                    f"(is_db_wide={is_db_wide}, deep_research_approved={deep_research_approved})"
                )

                process_monitor.start_stage("planner")
                logger.info("Creating database selection plan...")
                db_selection_plan, planner_usage_list = create_database_selection_plan(
                    research_statement,
                    token,
                    available_databases,
                )
                selected_databases = db_selection_plan.get("databases", [])
                query_embedding = db_selection_plan.get("query_embedding")
                logger.info(
                    f"Database selection plan created with {len(selected_databases)} databases: {selected_databases}"
                )
                process_monitor.end_stage("planner")
                for usage_details in planner_usage_list:
                    process_monitor.add_llm_call_details_to_stage(
                        "planner", usage_details
                    )
                process_monitor.add_stage_details(
                    "planner",
                    database_count=len(selected_databases),
                    selected_databases=selected_databases,
                    decision=db_selection_plan,
                )

                logger.info(f"Querying databases: {selected_databases}")
                yield "# 📋 Research Plan \n\n"
                yield f"{research_statement}\n\n"
                selected_db_display_names = [
                    available_databases.get(db_name, {}).get("name", db_name)
                    for db_name in selected_databases
                ]
                if selected_db_display_names:
                    if len(selected_db_display_names) == 1:
                        names_str = selected_db_display_names[0]
                    elif len(selected_db_display_names) == 2:
                        names_str = f"{selected_db_display_names[0]} and {selected_db_display_names[1]}"
                    else:
                        names_str = (
                            ", ".join(selected_db_display_names[:-1])
                            + f", and {selected_db_display_names[-1]}"
                        )
                    yield "\n\n"
                else:
                    yield "No databases selected for search.\n\n---\n"

                if not selected_databases:
                    logger.warning(
                        "Database selection plan is empty, skipping database search."
                    )
                else:
                    logger.info(
                        f"Starting {len(selected_databases)} parallel queries..."
                    )
                    aggregated_detailed_research = {}
                    all_file_links = []
                    all_page_section_refs = {}
                    all_section_content_maps = {}
                    all_reference_indices = {}
                    futures = []

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for i, db_name in enumerate(selected_databases):
                            query_text = research_statement
                            db_display_name = available_databases.get(db_name, {}).get(
                                "name", db_name
                            )
                            query_context = {
                                "research_statement": research_statement,
                                "query_embedding": query_embedding,
                                "is_db_wide": is_db_wide,
                                "deep_research_approved": deep_research_approved,
                            }
                            if i > 0:
                                time.sleep(1)
                            future = executor.submit(
                                _execute_query_worker,
                                db_name,
                                query_text,
                                token,
                                db_display_name,
                                i,
                                len(selected_databases),
                                query_context,
                            )
                            futures.append(future)
                        logger.info(f"Submitted {len(futures)} queries to thread pool.")

                        for future in concurrent.futures.as_completed(futures):
                            result_data = future.result()  # Re-raise if exception
                            db_name = result_data["db_name"]
                            db_display_name = result_data["db_display_name"]
                            task_exception = result_data["exception"]
                            result = result_data["result"]
                            file_links = result_data.get("file_links", None)
                            page_section_refs = result_data.get(
                                "page_section_refs", None
                            )
                            section_content_map = result_data.get(
                                "section_content_map", None
                            )
                            reference_index = result_data.get("reference_index", None)

                            status_summary = "❓ Unknown status (Processing error)."
                            if task_exception:
                                status_summary = f"❌ Error: {str(task_exception)}"
                                aggregated_detailed_research[db_name] = (
                                    f"Error: {str(task_exception)}"
                                )
                            elif result is not None:
                                if (
                                    isinstance(result, dict)
                                    and "detailed_research" in result
                                    and "status_summary" in result
                                ):
                                    status_summary = result["status_summary"]
                                    aggregated_detailed_research[db_name] = result[
                                        "detailed_research"
                                    ]
                                else:
                                    status_summary = (
                                        "❌ Error: Unexpected result format."
                                    )
                                    aggregated_detailed_research[db_name] = (
                                        f"Error: {str(result)[:200]}..."
                                    )

                            if file_links:
                                all_file_links.extend(file_links)

                            if page_section_refs:
                                all_page_section_refs[db_name] = page_section_refs
                            if section_content_map:
                                all_section_content_maps[db_name] = section_content_map

                            if reference_index:
                                all_reference_indices[db_name] = reference_index

                            status_summary = (
                                status_summary.replace("✅", "•")
                                .replace("📄", "•")
                                .replace("❌", "•")
                                .replace("ℹ️", "•")
                                .replace("⚠️", "•")
                                .replace("❓", "•")
                            )
                            status_block = f"{db_display_name}: {status_summary}\n\n"
                            yield status_block

                    logger.info("All database queries completed")

                if aggregated_detailed_research:
                    yield "\n\n---\n"
                    yield "\n\n## 📊 Research Summary\n"
                    process_monitor.start_stage("summary")
                    process_monitor.add_stage_details(
                        "summary",
                        num_results=len(aggregated_detailed_research),
                        sources=list(aggregated_detailed_research.keys()),
                    )

                    master_reference_index, aggregated_detailed_research = (
                        build_master_reference_index(
                            all_reference_indices,
                            aggregated_detailed_research,
                        )
                    )

                    try:
                        logger.info("Generating summary...")
                        summary_usage_details = None
                        summary_context = {
                            "research_statement": research_statement,
                            "reference_index": master_reference_index,
                        }
                        summary_stream = generate_streaming_summary(
                            aggregated_detailed_research,
                            token,
                            available_databases,
                            summary_context=summary_context,
                        )

                        buffer = ""

                        for chunk in summary_stream:
                            if isinstance(chunk, dict) and "usage_details" in chunk:
                                summary_usage_details = chunk["usage_details"]
                                if buffer:
                                    yield from process_final_references(
                                        buffer, master_reference_index
                                    )
                            else:
                                buffer += chunk
                                processed, buffer = process_reference_buffer(
                                    buffer, master_reference_index
                                )
                                if processed:
                                    yield processed
                        process_monitor.end_stage("summary")
                        if summary_usage_details:
                            process_monitor.add_llm_call_details_to_stage(
                                "summary", summary_usage_details
                            )
                        else:
                            logger.debug(
                                "No usage details received from summary stream"
                            )
                    except Exception as summary_exc:
                        logger.error(
                            f"Error during summarization: {summary_exc}",
                            exc_info=True,
                        )
                        yield f"\n\n**Error during final summarization:** {str(summary_exc)}"
                        process_monitor.end_stage("summary", "error")
                        process_monitor.add_stage_details(
                            "summary", error=str(summary_exc)
                        )
                    logger.info("Research completed")

                logger.debug("Research completed, ending monitoring")
                process_monitor.end_monitoring()

        else:
            logger.error(
                f"Unknown routing function: {routing_decision['function_name']}"
            )
            yield "Error: Unable to process query due to internal routing error."
            logger.debug("Ending monitoring due to routing error")
            process_monitor.end_monitoring()

    except Exception as e:
        error_msg = f"Critical error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if process_monitor.enabled and (
            not hasattr(process_monitor, "end_time") or not process_monitor.end_time
        ):
            process_monitor.end_monitoring()
        process_monitor.add_stage_details("_global", error=error_msg)
        yield f"**Error:** {error_msg}"

    finally:
        if process_monitor.enabled and (
            not hasattr(process_monitor, "end_time") or not process_monitor.end_time
        ):
            logger.debug("Setting process monitoring end_time in finally block")
            process_monitor.end_monitoring()

        if process_monitor.enabled:
            try:
                logger.info(
                    f"Logging process monitor data for run {process_monitor.run_uuid}"
                )

                with get_session() as session:
                    result = session.execute(
                        text(
                            """
                            SELECT EXISTS (
                               SELECT FROM information_schema.tables
                               WHERE table_schema = 'public'
                               AND table_name = 'process_monitor_logs'
                            )
                        """
                        )
                    )
                    table_exists = result.scalar()
                    if not table_exists:
                        logger.warning("process_monitor_logs table does not exist")

                    process_monitor.log_to_database(session)
                    logger.info("Process monitor data logged to database")

            except Exception as log_exc:
                logger.error(
                    f"Failed to log process monitor data: {log_exc}",
                    exc_info=True,
                )

            finally:
                import gc

                gc.collect()

        if debug_mode and debug_data is not None and not debug_data.get("error"):
            debug_data["completed"] = True
            if "end_timestamp" not in debug_data:
                final_agent_usage = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                }
                try:
                    for stage_usage in (
                        debug_data.get("tokens", {}).get("stages", {}).values()
                    ):
                        final_agent_usage["prompt_tokens"] += stage_usage.get(
                            "prompt", 0
                        )
                        final_agent_usage["completion_tokens"] += stage_usage.get(
                            "completion", 0
                        )
                        final_agent_usage["total_tokens"] += stage_usage.get("total", 0)
                        final_agent_usage["cost"] += stage_usage.get("cost", 0.0)
                    debug_data["tokens"]["prompt"] = final_agent_usage["prompt_tokens"]
                    debug_data["tokens"]["completion"] = final_agent_usage[
                        "completion_tokens"
                    ]
                    debug_data["tokens"]["total"] = final_agent_usage["total_tokens"]
                    debug_data["cost"] = final_agent_usage["cost"]
                except Exception:
                    logger.debug("Could not calculate legacy debug token totals")
                debug_data["end_timestamp"] = datetime.now().isoformat()
            yield f"\n\nDEBUG_DATA:{json.dumps(debug_data)}"


def model(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[Callable] = None,
    debug_mode: bool = False,
    db_names: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """
    Main entry point for processing conversations and generating responses.

    This is the primary synchronous interface for the IRIS system. It processes
    conversation history, routes to appropriate agents, and yields streaming responses.

    Args:
        conversation: Dictionary containing conversation history with 'messages' key.
            Each message should have 'role' and 'content' fields.
        html_callback: Optional callback for HTML rendering (deprecated, unused).
        debug_mode: If True, appends DEBUG_DATA JSON with token usage at end of stream.
        db_names: Optional list of database internal names to restrict queries to.
            If provided, only these databases will be available to agents.

    Yields:
        String chunks of the streaming response. For research queries, yields research
        plan, database status updates, and final summary. For direct responses, yields
        the conversational answer. If debug_mode is True, yields DEBUG_DATA JSON at end.

    Example:
        ```python
        conversation = {
            "messages": [
                {"role": "user", "content": "What is the CCAR framework?"}
            ]
        }

        for chunk in model(conversation, db_names=["internal_regulatory"]):
            print(chunk, end="", flush=True)
        ```
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    try:
        sync_gen = _model_generator(conversation, html_callback, debug_mode, db_names)
        for chunk in sync_gen:
            yield chunk
    except Exception as e:
        error_msg = f"Error during model execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield f"**Error:** {error_msg}"


async def process_request_async(
    conversation: List[Dict[str, str]],
    stream: bool = False,
    db_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Async wrapper for FastAPI that processes a conversation request.

    Runs the synchronous model in a thread pool executor to avoid blocking
    the async event loop. Collects all streaming chunks and returns as a
    complete response.

    Args:
        conversation: List of message dictionaries with 'role' and 'content'.
        stream: Whether to enable streaming (currently unused, reserved for future).
        db_names: Optional list of database internal names to restrict queries to.

    Returns:
        Dictionary with keys:
            - response: Complete response text
            - agent_used: Which agent handled the request (if available)
            - processing_time_ms: Total processing time in milliseconds
            - token_usage: Token usage statistics (if available)
            - run_uuid: Unique run identifier (if available)

    Example:
        ```python
        result = await process_request_async(
            conversation=[{"role": "user", "content": "What is CCAR?"}],
            db_names=["internal_regulatory"]
        )
        print(result["response"])
        print(f"Processed in {result['processing_time_ms']}ms")
        ```
    """
    import asyncio
    import time

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info(f"Processing async request: {len(conversation)} messages")

    start_time = time.time()

    def run_sync_model():
        try:
            conversation_dict = {"messages": conversation}
            response_chunks = []
            agent_used = None
            run_uuid = None
            token_usage = None

            for chunk in model(conversation_dict, debug_mode=False, db_names=db_names):
                if isinstance(chunk, str):
                    response_chunks.append(chunk)
                elif isinstance(chunk, dict):
                    if "agent_used" in chunk:
                        agent_used = chunk.get("agent_used")
                    if "run_uuid" in chunk:
                        run_uuid = chunk.get("run_uuid")
                    if "token_usage" in chunk:
                        token_usage = chunk.get("token_usage")

            full_response = "".join(response_chunks)

            return {
                "response": full_response,
                "agent_used": agent_used,
                "run_uuid": str(run_uuid) if run_uuid else None,
                "token_usage": token_usage,
            }

        except Exception as e:
            logger.error(f"Error in sync model execution: {str(e)}", exc_info=True)
            return {
                "response": f"Error processing request: {str(e)}",
                "agent_used": None,
                "run_uuid": None,
                "token_usage": None,
            }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_sync_model)

    processing_time_ms = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time_ms

    logger.info(f"Request completed: {processing_time_ms}ms")

    return result
