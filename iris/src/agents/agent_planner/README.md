# Agent Planner (`iris/src/agents/agent_planner/`)

This directory contains the Planner Agent, which is responsible for creating strategic database research query plans based on research statements from the Clarifier Agent. It determines which databases to query and what specific queries to run, optimizing the research process.

## Key Components

* **`planner.py`**: Implements the core logic of the Planner Agent. The main function `create_database_selection_plan` analyzes the research statement and selects the most relevant databases (1-5) to query. It supports continuation of previous research and validates database selections. It interacts with the LLM via tool calling to enforce structured output.
* **`planner_settings.py`**: Defines configuration settings for the Planner Agent, including model capabilities, prompt engineering using the CO-STAR framework (Context, Objective, Style, Tone, Audience, Response), system prompts, temperature, token limits, available databases, and tool definitions. It incorporates advanced prompt engineering techniques to guide the LLM's database selection behavior precisely.

## Workflow (`create_database_selection_plan` in `planner.py`)

1. **Input Processing**:
   * Receives the research statement from the Clarifier, an authentication token, and an optional continuation flag.
   * Prepares system and user messages using the detailed system prompt defined in `planner_settings.py`.

2. **LLM Invocation**:
   * Calls the LLM with the prepared messages, model configuration, and tool definitions.
   * Uses function calling to enforce structured output from the LLM, specifically the `submit_database_selection_plan` function.

3. **Decision Extraction**:
   * Parses the LLM response to extract the tool call arguments, which include the list of selected databases.
   * Validates that the selected databases are known and appropriate.

4. **Error Handling**:
   * Validates the response structure and content.
   * Raises `PlannerError` for any inconsistencies, missing fields, or invalid database selections.
   * Logs errors with detailed traceback for troubleshooting.

5. **Output**:
   * Returns a tuple containing the database selection plan dictionary and usage details for the LLM call.

## Planner Agent Role and Design

The Planner Agent is designed to:

* Analyze the research statement to identify key accounting concepts and information needs.
* Select the most relevant internal and external databases (1-5) based on the research statement's scope and content.
* Prioritize internal databases, especially core accounting-related ones.
* Incorporate user preferences for including external sources.
* Scale the number of selected databases based on the complexity and breadth of the research statement.
* Support continuation of previous research by selecting databases that address remaining gaps.
* Provide clear, professional, and efficient database selection to optimize research quality and performance.
* Interact with the LLM via the OpenAI connector using structured tool calling to enforce decision consistency.

## Dependencies

* `json`, `logging`, and typing modules for internal logic.
* `get_model_config` from `chat_model.model_settings` for model configuration.
* `call_llm` from `llm_connectors.rbc_openai` for LLM interaction.
* Global prompt components from `global_prompts` for constructing the system prompt.

## Error Handling

The agent raises `PlannerError` for any issues during database selection planning, including invalid LLM responses, missing fields, or invalid database names. Errors are logged with full traceback for debugging.

---

Refer to the main project README and other agent READMEs for details on how the Planner Agent fits into the overall IRIS system pipeline.
