# Agent Router (`iris/src/agents/agent_router/`)

This directory contains the Router Agent, which is responsible for analyzing user queries and determining the appropriate processing path within the IRIS system pipeline. It decides whether a query should be handled by the Direct Response Agent or routed for further research.

## Key Components

* **`router.py`**: Implements the core logic of the Router Agent. The main function `get_routing_decision` analyzes the conversation context and uses a tool call to the LLM to decide the routing path. It expects a structured response indicating the function name to invoke next (`response_from_conversation` or `research_from_database`). It handles errors and logs relevant information.
* **`router_settings.py`**: Defines configuration settings for the Router Agent, including model capabilities, prompt engineering using the CO-STAR framework (Context, Objective, Style, Tone, Audience, Response), system prompts, temperature, token limits, and tool definitions. It ensures the agent produces clear, professional, and accurate routing decisions.

## Workflow (`get_routing_decision` in `router.py`)

1. **Input Processing**:
   * Receives the conversation history and an authentication token (OAuth token or API key depending on environment).
   * Prepares a system message using the detailed system prompt defined in `router_settings.py`.

2. **LLM Invocation**:
   * Calls the LLM with the prepared messages, model configuration, and tool definitions.
   * Uses function calling to enforce structured output from the LLM, specifically the `route_query` function.

3. **Decision Extraction**:
   * Parses the LLM response to extract the tool call arguments, which include the routing function name.
   * Validates that the function name is present and recognized.

4. **Error Handling**:
   * Logs errors with detailed traceback.
   * Raises `RouterError` for any issues during routing decision making.

5. **Output**:
   * Returns a tuple containing the routing decision dictionary and usage details for the LLM call.

## Router Agent Role and Design

The Router Agent is designed to:

* Analyze the conversation context to determine the best processing path for a user query.
* Decide between direct response generation or initiating a research workflow.
* Provide clear, structured routing decisions to guide subsequent agents.
* Maintain a professional and efficient approach to query handling.
* Interact with the LLM via the OpenAI connector using structured tool calling to enforce decision consistency.

## Dependencies

* `json`, `logging`, and typing modules for internal logic.
* `get_model_config` from `chat_model.model_settings` for model configuration.
* `call_llm` from `llm_connectors.rbc_openai` for LLM interaction.
* Global prompt components from `global_prompts` for constructing the system prompt.

## Error Handling

The agent raises `RouterError` for any issues during routing decision making, including invalid LLM responses or missing fields. Errors are logged with full traceback for debugging.

---

Refer to the main project README and other agent READMEs for details on how the Router Agent fits into the overall IRIS system pipeline.
