# Agent Clarifier (`iris/src/agents/agent_clarifier/`)

This directory contains the Clarifier Agent, which is responsible for assessing the sufficiency of context in a user query to determine whether research can proceed or if additional essential context must be requested from the user. It acts as the first step in the research path after the Router agent decides that research is needed.

## Key Components

* **`clarifier.py`**: Implements the core logic of the Clarifier Agent. The main function `clarify_research_needs` analyzes the conversation history and decides whether to request missing critical context or to create a comprehensive research statement for the Planner agent. It interacts with the LLM via the OpenAI connector, using tool calling to enforce structured decision-making.
* **`clarifier_settings.py`**: Defines configuration settings for the Clarifier Agent, including model capabilities, prompt engineering using the CO-STAR framework (Context, Objective, Style, Tone, Audience, Response), system prompts, temperature, token limits, and tool definitions. It incorporates advanced prompt engineering techniques to guide the LLM's behavior precisely.

## Workflow (`clarify_research_needs` in `clarifier.py`)

1. **Input Processing**:
   * Receives the conversation history and an authentication token (OAuth token or API key depending on environment).
   * Prepares a system message using the detailed system prompt defined in `clarifier_settings.py`.

2. **LLM Invocation**:
   * Calls the LLM with the prepared messages, model configuration, and tool definitions.
   * Uses function calling to enforce structured output from the LLM, specifically the `make_clarifier_decision` function.

3. **Decision Extraction**:
   * Parses the LLM response to extract the tool call arguments, which include:
     - `action`: Either `request_essential_context` or `create_research_statement`.
     - `output`: Either a numbered list of context questions or a comprehensive research statement.
     - `scope`: The scope of the request (`metadata` or `research`), required if action is `create_research_statement`.
     - `is_continuation`: Boolean indicating if this is a continuation of previous research.
     - `request_external_confirmation`: Optional boolean flag to request user confirmation for including external sources (set for accounting-related queries).

4. **Error Handling**:
   * Validates the response structure and content.
   * Raises `ClarifierError` for any inconsistencies or missing required fields.
   * Logs errors with detailed traceback for troubleshooting.

5. **Output**:
   * Returns a tuple containing the clarifier decision dictionary and usage details for the LLM call.

## Clarifier Agent Role and Design

The Clarifier Agent is designed to:

* Analyze the conversation to determine if sufficient context exists to proceed with database research.
* Request only truly necessary information when critical context is missing, avoiding unnecessary or generic questions.
* Create a precise, database-aware research statement that guides the Planner agent in selecting relevant databases and queries.
* Identify the scope of the user's request as either `metadata` (catalog lookup) or `research` (content analysis).
* Detect continuation of previous research to maintain context across interactions.
* Apply advanced prompt engineering techniques using the CO-STAR framework to ensure clarity, professionalism, and precision in its outputs.
* Interact with the LLM via the OpenAI connector using structured tool calling to enforce decision consistency.

## Dependencies

* `json`, `logging`, and typing modules for internal logic.
* `get_model_config` from `chat_model.model_settings` for model configuration.
* `call_llm` from `llm_connectors.rbc_openai` for LLM interaction.
* Global prompt components from `global_prompts` for constructing the system prompt.

## Error Handling

The agent raises `ClarifierError` for any issues during the clarification process, including invalid LLM responses, missing fields, or JSON parsing errors. Errors are logged with full traceback for debugging.

---

Refer to the main project README and other agent READMEs for details on how the Clarifier Agent fits into the overall IRIS system pipeline.
