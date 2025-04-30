# Chat Model Orchestration (`iris/src/chat_model/`)

This directory contains the core orchestration logic for the IRIS system. It defines how the different agents in the pipeline interact to process a user query and generate a response.

## Key Components

*   **`model.py`**: This is the central script that orchestrates the entire agent pipeline. It takes a user query (often as part of a conversation history) and manages the flow through the Router, Clarifier, Planner, Database Router/Subagents, and Summarizer/Direct Response agents to produce the final output. It integrates the various agent components and manages the state of the query processing.
*   **`model_settings.py`**: Contains configuration settings related to the main orchestration model, potentially including parameters for controlling the overall flow, timeouts, or specific model choices for the orchestration layer itself (if applicable).

## Workflow

The `model.py` script typically executes the following high-level steps:

1.  Receives the user input and conversation context.
2.  Invokes the `agent_router` to determine the query type.
3.  Based on the router's decision:
    *   If direct response: Invokes the `agent_direct_response`.
    *   If research needed:
        *   Invokes the `agent_clarifier`.
        *   Invokes the `agent_planner`.
        *   Invokes the `database_router` (which manages subagents).
        *   Invokes the `agent_summarizer`.
4.  Returns the final generated response.

Refer to the main project README and the `iris/src/agents/README.md` for more details on the individual agents involved in the pipeline.
