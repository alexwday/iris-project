"""Chat model orchestration for routing, research, and summarization."""

import concurrent.futures
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional

from sqlalchemy import text

from ..agent.tools.database_router import route_query_with_cascading_retrieval
from ..agent.tools.research_types import Finding, FindingsList, IndexedFinding, IndexedFindingsList
from ..connections.postgres import get_database_session
from ..utils.reference_processor import (
    finalize_reference_replacements,
    process_streaming_reference_buffer,
)


def format_usage_summary_markdown(
    agent_token_usage: Dict[str, Any], start_time: Optional[str] = None
) -> str:
    """Return token usage and timing as markdown.

    Args:
        agent_token_usage (Dict[str, Any]): Accumulated token usage metrics with keys
            such as prompt_tokens, completion_tokens, total_tokens, and cost.
        start_time (Optional[str]): ISO 8601 timestamp marking when processing started.

    Returns:
        str: Markdown summary of usage and timing details.
    """
    duration = None
    if start_time:
        try:
            end_dt = datetime.now()
            start_dt = datetime.fromisoformat(start_time)
            duration = (end_dt - start_dt).total_seconds()
        except ValueError:
            logging.getLogger().warning(
                "Could not parse start_time for duration calculation: %s", start_time
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


def consolidate_findings_with_refs(
    all_findings: FindingsList,
) -> tuple[IndexedFindingsList, Dict[str, Dict[str, Any]]]:
    """Consolidate findings from all databases and assign reference IDs.

    Takes the combined findings from all database queries and:
    1. Assigns sequential ref_ids starting from 1
    2. Builds a master reference index for the streaming processor

    Args:
        all_findings: Combined list of Finding objects from all databases.

    Returns:
        Tuple of:
        - IndexedFindingsList: Findings with ref_id assigned
        - Dict: Master reference index for href link generation
    """
    indexed_findings: IndexedFindingsList = []
    master_reference_index: Dict[str, Dict[str, Any]] = {}

    ref_counter = 1
    for finding in all_findings:
        ref_id = str(ref_counter)

        # Create IndexedFinding by adding ref_id
        indexed_finding: IndexedFinding = {
            **finding,
            "ref_id": ref_id,
        }
        indexed_findings.append(indexed_finding)

        # Build reference index entry for href generation
        master_reference_index[ref_id] = {
            "doc_name": finding["document_name"],
            "file_link": finding["file_link"],
            "file_name": finding["file_name"],
            "page": finding["page"] or 1,
            "page_reference": str(finding["page"] or 1),
            "chapter_number": "",
            "source_filename": finding["file_name"] or finding["document_name"],
            "highlight_text": "",
            "source_db": finding["db_source"],
        }

        ref_counter += 1

    return indexed_findings, master_reference_index


def format_findings_for_summarizer(
    indexed_findings: IndexedFindingsList,
) -> Dict[str, str]:
    """Format indexed findings into research text for the summarizer.

    Groups findings by database and formats them with [REF:X] markers
    that will be replaced with clickable links during streaming.

    Args:
        indexed_findings: Findings with ref_ids assigned.

    Returns:
        Dict mapping db_source to formatted research text.
    """
    from collections import defaultdict

    # Group findings by database
    findings_by_db: Dict[str, List[IndexedFinding]] = defaultdict(list)
    for finding in indexed_findings:
        findings_by_db[finding["db_source"]].append(finding)

    formatted_research: Dict[str, str] = {}

    for db_source, db_findings in findings_by_db.items():
        # Group by document within each database
        findings_by_doc: Dict[str, List[IndexedFinding]] = defaultdict(list)
        for finding in db_findings:
            findings_by_doc[finding["document_name"]].append(finding)

        parts = []
        for doc_name, doc_findings in findings_by_doc.items():
            parts.append(f"## {doc_name}\n")

            # Sort by page number
            sorted_findings = sorted(
                doc_findings, key=lambda f: f["page"] or 0
            )

            for finding in sorted_findings:
                page = finding["page"] or "N/A"
                ref_id = finding["ref_id"]
                content = finding["finding"]

                parts.append(f"**Page {page}:** {content} [REF:{ref_id}]\n")

            parts.append("")

        formatted_research[db_source] = "\n".join(parts)

    return formatted_research


def _execute_database_query_task(
    db_name: str,
    query_text: str,
    token: str,
    db_display_name: str,
    query_index: int,
    total_queries: int,
    query_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a single database query in a thread pool worker.

    Uses unified cascading retrieval architecture where metadata subagent makes
    per-document decisions (answered/irrelevant/needs_deep_research), triggering file
    research only for documents that need it.

    Args:
        db_name (str): Internal name of the database.
        query_text (str): The search query to execute.
        token (str): OAuth token for API authentication.
        db_display_name (str): Human-readable database name for display.
        query_index (int): Index of this query in the batch (0-based).
        total_queries (int): Total number of queries being executed.
        query_context (Optional[Dict[str, Any]]): Context containing research_statement
            and query_embedding.

    Returns:
        Dict[str, Any]: Query results with findings, status_summary, path info.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    router_result = None
    task_exception = None

    from ..utils.process_monitoring import get_process_monitor_instance

    process_monitor = get_process_monitor_instance()
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
            "Thread executing query %d/%d for database: %s",
            query_index + 1,
            total_queries,
            db_name,
        )
        if query_context is None:
            query_context = {
                "research_statement": query_text,
            }

        router_result = route_query_with_cascading_retrieval(
            database=db_name,
            token=token,
            process_monitor=process_monitor,
            query_stage_name=query_stage_name,
            query_context=query_context,
        )

        logger.info("Thread completed query for database: %s", db_name)
        process_monitor.end_stage(query_stage_name)

        process_monitor.add_stage_details(
            query_stage_name,
            status_summary=router_result.get("status_summary", "No status provided"),
            findings_count=len(router_result.get("findings", [])),
            path=router_result.get("path", "unknown"),
        )

    except Exception as e:
        task_exception = e
        logger.error(
            "Thread error executing query for %s: %s", db_name, e, exc_info=True
        )
        process_monitor.end_stage(query_stage_name, "error")
        process_monitor.add_stage_details(query_stage_name, error=str(e))

    finally:
        try:
            import gc

            gc.collect()
        except Exception as cleanup_exc:
            logger.warning("Error during worker cleanup: %s", cleanup_exc)

    return {
        "db_name": db_name,
        "query_text": query_text,
        "db_display_name": db_display_name,
        "query_index": query_index,
        "total_queries": total_queries,
        "router_result": router_result,
        "exception": task_exception,
    }


def _stream_model_workflow(
    conversation: Optional[Dict[str, Any]] = None,
    _html_callback: Optional[Callable] = None,
    debug_mode: bool = False,
    db_names: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """Run the agent workflow synchronously and yield streaming chunks.

    Orchestrates conversation processing, routing decisions, research planning,
    parallel database queries, and response generation. Implements process monitoring
    for performance tracking and debugging.

    Args:
        conversation (Optional[Dict[str, Any]]): Conversation dictionary containing
            a messages list.
        html_callback (Optional[Callable]): Optional callback for HTML rendering
            (deprecated).
        debug_mode (bool): When True, yields legacy DEBUG_DATA JSON at the end.
        db_names (Optional[List[str]]): Databases to restrict queries to.

    Yields:
        str: Streaming response chunks including research plans, status updates, and
            final synthesized answers.

    Raises:
        Exception: Critical errors are caught, logged, and yielded as error messages.
    """
    from ..utils.process_monitoring import (
        get_process_monitor_instance,
        set_process_monitoring_enabled,
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    set_process_monitoring_enabled(True)
    process_monitor = get_process_monitor_instance()
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

    from ..agent.clarifier import generate_clarifier_decision
    from ..agent.direct_response import stream_direct_response_from_conversation
    from ..agent.planner import generate_database_selection_plan
    from ..agent.router import generate_routing_decision
    from ..agent.summarizer import stream_research_summary
    from ..agent.tools.database_metadata import fetch_available_databases
    from ..utils.input_sanitizer import sanitize_conversation_history
    from ..utils.logging_format import configure_root_logger
    from ..connections.oauth import fetch_oauth_token
    from ..utils.rbc_security import configure_rbc_security_certs

    logger = configure_root_logger()

    try:
        logger.info("Initializing model...")

        process_monitor.start_stage("ssl_setup")
        cert_path = configure_rbc_security_certs()
        process_monitor.end_stage("ssl_setup")
        process_monitor.add_stage_details("ssl_setup", cert_path=cert_path)

        process_monitor.start_stage("oauth_setup")
        token = fetch_oauth_token()
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
            processed_conversation = sanitize_conversation_history(conversation)
            logger.info(
                "Conversation processed: %d messages",
                len(processed_conversation["messages"]),
            )
        except ValueError as e:
            logger.warning("Invalid conversation format: %s", e)
            process_monitor.end_stage("conversation_processing", "error")
            yield f"Model initialized, but conversation format is invalid: {str(e)}"
            return
        except Exception as e:
            logger.error("Error processing conversation: %s", e)
            process_monitor.end_stage("conversation_processing", "error")
            yield f"Error processing conversation: {str(e)}"
            return

        if not processed_conversation["messages"]:
            logger.warning("Processed conversation is empty.")
            process_monitor.end_stage("conversation_processing", "error")
            yield "Model initialized, but processed conversation is empty."
            return

        process_monitor.end_stage("conversation_processing")
        process_monitor.add_stage_details(
            "conversation_processing",
            message_count=len(processed_conversation["messages"]),
        )

        available_databases = fetch_available_databases()
        if db_names is not None:
            logger.info("Filtering databases to: %s", db_names)
            available_databases = {
                k: v for k, v in available_databases.items() if k in db_names
            }

        process_monitor.start_stage("router")
        logger.info("Getting routing decision...")
        routing_decision, router_usage_details = generate_routing_decision(
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

        if routing_decision["function_name"] == "direct_response":
            logger.info("Using direct response path")
            process_monitor.start_stage("direct_response")
            direct_response_usage_details = None
            stream_iterator = stream_direct_response_from_conversation(
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

        elif routing_decision["function_name"] == "database_research":
            logger.info("Using research path")
            process_monitor.start_stage("clarifier")
            logger.info("Clarifying research needs...")
            clarifier_decision, clarifier_usage_details = generate_clarifier_decision(
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

            if clarifier_decision["action"] == "ask_clarification":
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
                research_statement = clarifier_decision.get("output", "")
                is_db_wide = clarifier_decision.get("is_db_wide", False)
                deep_research_approved = clarifier_decision.get(
                    "deep_research_approved", False
                )

                logger.info(
                    "Research statement: %s... (is_db_wide=%s, "
                    "deep_research_approved=%s)",
                    research_statement[:100],
                    is_db_wide,
                    deep_research_approved,
                )

                process_monitor.start_stage("planner")
                logger.info("Creating database selection plan...")
                db_selection_plan, planner_usage_list = generate_database_selection_plan(
                    research_statement,
                    token,
                    available_databases,
                )
                selected_databases = db_selection_plan.get("databases", [])
                query_embedding = db_selection_plan.get("query_embedding")
                logger.info(
                    "Database selection plan created with %d databases: %s",
                    len(selected_databases),
                    selected_databases,
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

                logger.info("Querying databases: %s", selected_databases)
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
                        names_str = (
                            f"{selected_db_display_names[0]} and "
                            f"{selected_db_display_names[1]}"
                        )
                    else:
                        names_str = (
                            ", ".join(selected_db_display_names[:-1])
                            + f", and {selected_db_display_names[-1]}"
                        )
                    yield f"Searching {names_str}.\n\n"
                else:
                    yield "No databases selected for search.\n\n---\n"

                all_findings: FindingsList = []

                if not selected_databases:
                    logger.warning(
                        "Database selection plan is empty, skipping database search."
                    )
                else:
                    logger.info(
                        "Starting %d parallel queries...", len(selected_databases)
                    )
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
                                _execute_database_query_task,
                                db_name,
                                query_text,
                                token,
                                db_display_name,
                                i,
                                len(selected_databases),
                                query_context,
                            )
                            futures.append(future)
                        logger.info(
                            "Submitted %d queries to thread pool.", len(futures)
                        )

                        for future in concurrent.futures.as_completed(futures):
                            result_data = future.result()
                            db_name = result_data["db_name"]
                            db_display_name = result_data["db_display_name"]
                            task_exception = result_data["exception"]
                            router_result = result_data.get("router_result")

                            status_summary = "❓ Unknown status (Processing error)."
                            if task_exception:
                                status_summary = f"❌ Error: {str(task_exception)}"
                            elif router_result is not None:
                                status_summary = router_result.get(
                                    "status_summary", "No status"
                                )
                                # Collect findings from this database
                                db_findings = router_result.get("findings", [])
                                all_findings.extend(db_findings)
                                logger.info(
                                    "Collected %d findings from %s",
                                    len(db_findings),
                                    db_name,
                                )

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

                if all_findings:
                    yield "\n\n---\n"
                    yield "\n\n## 📊 Research Summary\n"
                    process_monitor.start_stage("summary")

                    # Consolidate findings and assign ref_ids
                    indexed_findings, master_reference_index = (
                        consolidate_findings_with_refs(all_findings)
                    )

                    # Format findings for summarizer
                    aggregated_detailed_research = format_findings_for_summarizer(
                        indexed_findings
                    )

                    process_monitor.add_stage_details(
                        "summary",
                        num_findings=len(indexed_findings),
                        sources=list(aggregated_detailed_research.keys()),
                    )

                    try:
                        logger.info("Generating summary...")
                        summary_usage_details = None
                        summary_context = {
                            "research_statement": research_statement,
                            "indexed_findings": indexed_findings,
                            "reference_index": master_reference_index,
                        }
                        summary_stream = stream_research_summary(
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
                                    yield from finalize_reference_replacements(
                                        buffer, master_reference_index
                                    )
                            else:
                                buffer += chunk
                                processed, buffer = process_streaming_reference_buffer(
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
                            "Error during summarization: %s",
                            summary_exc,
                            exc_info=True,
                        )
                        err_msg = str(summary_exc)
                        yield f"\n\n**Error during summarization:** {err_msg}"
                        process_monitor.end_stage("summary", "error")
                        process_monitor.add_stage_details(
                            "summary", error=str(summary_exc)
                        )
                    logger.info("Research completed")

                logger.debug("Research completed, ending monitoring")
                process_monitor.end_monitoring()

        else:
            logger.error(
                "Unknown routing function: %s", routing_decision["function_name"]
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
                    "Logging process monitor data for run %s", process_monitor.run_uuid
                )

                with get_database_session() as session:
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
                    "Failed to log process monitor data: %s",
                    log_exc,
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


def stream_model_response(
    conversation: Optional[Dict[str, Any]] = None,
    html_callback: Optional[Callable] = None,
    debug_mode: bool = False,
    db_names: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """Process conversations and yield streaming responses.

    Args:
        conversation (Optional[Dict[str, Any]]): Conversation history with a messages
            list.
        html_callback (Optional[Callable]): Deprecated HTML rendering callback.
        debug_mode (bool): When True, appends DEBUG_DATA JSON at the end of the stream.
        db_names (Optional[List[str]]): Databases to restrict queries to.

    Yields:
        str: Streaming research plans, database status updates, and final answers.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    try:
        yield from _stream_model_workflow(
            conversation, html_callback, debug_mode, db_names
        )
    except Exception as e:
        error_msg = f"Error during model execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield f"**Error:** {error_msg}"


async def process_conversation_request_async(
    conversation: List[Dict[str, str]],
    stream: bool = False,
    db_names: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Async wrapper for FastAPI that processes a conversation request.

    Runs the synchronous model in a thread pool executor to avoid blocking the event
    loop. Collects all streaming chunks and returns a complete response.

    Args:
        conversation (List[Dict[str, str]]): Conversation messages with role/content.
        stream (bool): Whether to enable streaming (reserved for future use).
        db_names (Optional[List[str]]): Databases to restrict queries to.

    Returns:
        Dict[str, Any]: Response text, agent_used, processing_time_ms, token_usage,
            and run_uuid when available.
    """
    import asyncio

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if "_stream" in kwargs:
        stream = kwargs.pop("_stream")

    logger.info("Processing async request: %d messages", len(conversation))

    start_time = time.time()

    def run_sync_model():
        try:
            conversation_dict = {"messages": conversation}
            response_chunks = []
            agent_used = None
            run_uuid = None
            token_usage = None

            for chunk in stream_model_response(
                conversation_dict, debug_mode=False, db_names=db_names
            ):
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
            logger.error("Error in sync model execution: %s", e, exc_info=True)
            return {
                "response": f"Error processing request: {str(e)}",
                "agent_used": None,
                "run_uuid": None,
                "token_usage": None,
            }

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_sync_model)

    processing_time_ms = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time_ms

    logger.info("Request completed: %dms", processing_time_ms)

    return result
