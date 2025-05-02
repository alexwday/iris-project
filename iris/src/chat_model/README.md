# Chat Model Orchestration (`iris/src/chat_model/`)

This directory contains the core orchestration logic for the IRIS system. It defines how the different agents in the pipeline interact to process a user query, manage environment settings, and generate a response, including handling concurrent database operations and process monitoring.

## Key Components

*   **`model.py`**: This is the central script that orchestrates the entire agent pipeline. It provides a synchronous generator interface (`model`) wrapping a core synchronous generator (`_model_generator`). It manages the flow from initial setup (SSL, OAuth, logging, process monitoring) through agent invocation (Router, Clarifier, Planner, Database Router/Subagents, Summarizer/Direct Response) to final output generation and logging. It handles concurrent execution of database queries using `ThreadPoolExecutor`.
*   **`model_settings.py`**: Contains configuration settings for the IRIS system, primarily focused on environment management (local vs. RBC). It defines API endpoints, model configurations (names, costs for 'small', 'large', 'embedding' capabilities), environment flags (`IS_RBC_ENV`), request parameters (timeout, retries), and usage display settings (`SHOW_USAGE_SUMMARY`). It provides the `get_model_config` function to retrieve settings based on capability and environment.

## Workflow (`_model_generator` in `model.py`)

The `_model_generator` function executes the main workflow:

1.  **Initialization & Setup**:
    *   Configures logging (`logging_config`).
    *   Sets up SSL certificates if required (`setup_ssl`).
    *   Performs OAuth authentication if required (`setup_oauth`).
    *   Initializes and starts process monitoring (`enable_monitoring`, `get_process_monitor`, `start_monitoring`). A unique run UUID is generated.
    *   Processes the input `conversation` using `process_conversation`.

2.  **Routing**:
    *   Invokes the `agent_router` (`get_routing_decision`) to determine the query type based on the conversation. The router returns a function name (`response_from_conversation` or `research_from_database`) and usage details.
    *   Logs the routing decision and LLM usage to the process monitor.

3.  **Execution Paths**:

    *   **Direct Response Path** (if router decides `response_from_conversation`):
        *   Invokes the `agent_direct_response` (`response_from_conversation`) which streams the response directly based on the conversation history.
        *   Yields response chunks.
        *   Logs the agent's execution and LLM usage to the process monitor.

    *   **Research Path** (if router decides `research_from_database`):
        *   **Clarification**: Invokes the `agent_clarifier` (`clarify_research_needs`) to refine the research goal and determine the scope ('metadata' or 'research'). Logs decision and usage.
            *   If essential context is missing, yields clarification questions to the user and stops.
        *   **Planning**: Invokes the `agent_planner` (`create_database_selection_plan`) using the clarified research statement to get a list of relevant databases. Logs plan and usage. Yields the plan to the user.
        *   **Concurrent Database Querying**:
            *   If databases are selected in the plan:
                *   Iterates through the selected databases.
                *   Submits tasks to a `ThreadPoolExecutor`, where each thread runs the `_execute_query_worker` function.
                *   `_execute_query_worker`:
                    *   Starts a specific stage in the process monitor for the query.
                    *   Calls the synchronous database router (`route_query_sync` from `database_router.py`) for the specific database, passing the query, scope, token, and process monitor details. `route_query_sync` handles the actual subagent invocation and LLM calls internally.
                    *   Logs results (or errors) and document IDs to the process monitor stage.
                    *   Ends the process monitor stage.
                    *   Returns results (or exception).
                *   As each thread completes, yields a status update (success, error, items found) for that database to the user interface.
        *   **Result Aggregation & Summarization/Display**:
            *   **Research Scope**: Aggregates the `detailed_research` results from all successful database queries. Invokes the `agent_summarizer` (`generate_streaming_summary`) to synthesize the findings and streams the summary. Logs summary agent execution and usage.
            *   **Metadata Scope**: Aggregates metadata items (like document names/descriptions) from all successful queries. Formats and yields a list of unique items found per database.
        *   Yields a completion message.

4.  **Finalization & Logging**:
    *   Ensures process monitoring is stopped (`end_monitoring`).
    *   Attempts to log the complete process monitor data (all stages, details, timings, LLM usage) to the configured PostgreSQL database (`log_to_database` via `db_config.connect_to_db`). Handles connection and potential logging errors.
    *   (Legacy) Optionally yields a final `DEBUG_DATA` JSON blob if `debug_mode` is enabled.

## Helper Functions (`model.py`)

*   **`format_usage_summary(agent_token_usage, start_time)`**: Formats overall token usage and timing into a markdown string (Note: Relies on legacy `debug_data` structure, may be less accurate with current process monitoring).
*   **`format_remaining_queries(remaining_queries)`**: Formats a list of queries that were planned but not executed (e.g., due to errors or interruptions) for user display.
*   **`model(...)`**: The main synchronous wrapper function that simply calls and yields from `_model_generator`.

Refer to the main project README and the specific agent READMEs (e.g., `iris/src/agents/README.md`) for more details on the individual agents involved in the pipeline.
