# IRIS Agents (`iris/src/agents/`)

This directory contains the core AI agents that form the processing pipeline for user queries within the IRIS system. It also houses the specialized subagents responsible for interacting with specific data sources.

## Agent Pipeline

The main agents orchestrate the flow of a query:

1.  **`agent_router/`**: Determines if a query requires database research or can be answered directly from the conversation history.
2.  **`agent_clarifier/`**: Refines the user's query into a clear research goal and scope, potentially interacting with the user for clarification.
3.  **`agent_planner/`**: Creates a strategic plan outlining which database subagents should be invoked based on the clarified research goal.
4.  **`database_subagents/`**: Contains the router (`database_router.py`) that manages concurrent execution of individual database subagents, and the subagents themselves, each tailored to a specific internal or external data source. (See the `database_subagents/README.md` for more details).
5.  **`agent_summarizer/`**: Synthesizes the findings gathered by the database subagents into a coherent, consolidated response.
6.  **`agent_direct_response/`**: Formulates a direct answer based on conversation history when the `agent_router` determines database research is unnecessary.

Each agent directory typically contains:
*   `__init__.py`: Marks the directory as a Python package.
*   `agent_name.py`: The main logic for the agent.
*   `agent_name_settings.py`: Configuration settings specific to the agent (e.g., prompts, model parameters).

## Database Subagents

The `database_subagents/` directory holds the logic for querying specific data sources. See its dedicated [README.md](./database_subagents/README.md) for details on individual subagents and their functions.
