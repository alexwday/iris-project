# Agent Clarifier (`iris/src/agents/agent_clarifier/`)

The Clarifier Agent assesses the sufficiency of context in user queries to determine whether research can proceed or if additional essential context must be requested from the user. It acts as the first step in the research path after the Router decides that research is needed.

## Overview

The Clarifier Agent performs intelligent context assessment by analyzing conversation history and query content to determine if sufficient information exists for effective database research. It uses the CO-STAR framework for structured prompt engineering and employs a sophisticated decision framework that balances proceeding with research versus requesting essential context. The agent can determine query scope (metadata vs research), detect follow-up requests, and respect user override instructions to skip clarification.

## Key Components

* **`clarifier.py`**: Implements the core clarification logic with the main function `clarify_research_needs`. Uses LLM tool calling to analyze conversation context and determine if research can proceed or if essential context is needed. Returns a tuple containing clarification decision and usage details.
* **`clarifier_settings.py`**: Defines sophisticated configuration using the CO-STAR framework and integrates all global prompt components. Uses 'large' model capability for complex context analysis. Provides detailed decision criteria, scope determination, and user override handling.

## Core Functions/Classes

### `clarify_research_needs(conversation, token)`

#### Purpose
Analyzes user queries and conversation history to determine if sufficient context exists for database research or if essential information must be requested from the user first.

#### Parameters
* **`conversation`** (dict): Dictionary with 'messages' key containing conversation history
* **`token`** (str): Authentication token for API access (OAuth token in RBC environment, API key in local environment)

#### Returns
* **Tuple[Dict[str, Any], Optional[Dict[str, Any]]]**: 
  - First element: Clarifier decision dictionary with 'action', 'output', 'scope', and 'is_continuation'
  - Second element: Usage details dictionary with token usage, cost, and timing information (or None on error)

#### Workflow
1. **System Prompt Preparation**: Constructs system message using CO-STAR framework prompt from clarifier_settings
2. **Message Assembly**: Combines system prompt with conversation history for comprehensive context
3. **LLM Tool Call**: Invokes LLM with forced tool choice for `make_clarifier_decision` function
4. **Response Validation**: Validates tool call presence and extracts decision parameters
5. **Decision Extraction**: Parses JSON arguments to get action, output, scope, and continuation flag
6. **Scope Validation**: Ensures scope is provided when creating research statements and contains valid values

#### Error Handling
* **ClarifierError**: Raised for invalid responses, missing tool calls, or malformed JSON
* **Scope validation**: Specific handling for missing or invalid scope values when required
* **Exception logging**: Comprehensive error logging with stack traces via exc_info
* **Warning logging**: Logs warnings when scope is provided but not applicable

### `ClarifierError` (Exception Class)

#### Purpose
Custom exception class for clarifier-specific errors, providing clear error context for clarification failures.

## Configuration

Settings used from `clarifier_settings.py`:

* **`MODEL_CAPABILITY`**: "large" - Uses advanced model for complex context analysis
* **`MAX_TOKENS`**: 4096 - Maximum tokens for comprehensive context analysis
* **`TEMPERATURE`**: 0.0 - Ensures deterministic, consistent clarification decisions
* **`TOOL_DEFINITIONS`**: Defines `make_clarifier_decision` tool with action, output, scope, is_continuation, and request_external_confirmation parameters

## Usage Examples

### Basic Usage
```python
from iris.src.agents.agent_clarifier.clarifier import clarify_research_needs

# Query with sufficient context
conversation = {
    "messages": [
        {"role": "user", "content": "How does IFRS 15 handle contract modifications?"}
    ]
}

# Clarifier recognizes specific standard reference
decision, usage = clarify_research_needs(conversation, auth_token)
# Returns: ({
#     "action": "create_research_statement",
#     "output": "Accounting Query: Research focusing on IFRS 15 regarding...",
#     "scope": "research",
#     "is_continuation": False
# }, usage_details)
```

### Advanced Usage
```python
# Query requiring clarification
conversation = {
    "messages": [
        {"role": "user", "content": "What's the accounting treatment for this?"}
    ]
}

# Clarifier requests essential context
decision, usage = clarify_research_needs(conversation, auth_token)
# Returns: ({
#     "action": "request_essential_context",
#     "output": "1. What specific transaction...\n2. Which accounting standard...",
#     "scope": None,
#     "is_continuation": False
# }, usage_details)

# Override instruction example
conversation = {
    "messages": [
        {"role": "user", "content": "Tell me about revenue, no more clarification"}
    ]
}

# Clarifier respects override and proceeds
decision, usage = clarify_research_needs(conversation, auth_token)
# Returns: ({
#     "action": "create_research_statement",
#     "output": "Accounting Query: Research focusing on IFRS regarding revenue...",
#     "scope": "research",
#     "is_continuation": False
# }, usage_details)
```

## Integration Points

How the Clarifier Agent integrates with other IRIS components:

* **Router Agent**: Receives queries after Router determines research path is needed
* **Planner Agent**: Provides research statements that guide database query development
* **Chat Model**: Returns clarification requests to user or passes research statements to Planner
* **Global Prompts**: Incorporates all four global prompt components for comprehensive context

## Dependencies

* **`json`**: JSON parsing for tool call arguments
* **`logging`**: Comprehensive operation logging and error tracking
* **`typing`**: Type hints for function signatures and return values
* **Internal modules**: 
  - `env_config`: Model configuration and capability settings
  - `rbc_openai`: LLM connector for OpenAI API calls
  - `global_prompts`: All four global prompt components (project, fiscal, database, restrictions)
  - `clarifier_settings`: CO-STAR framework configuration and tool definitions

## Error Handling

Comprehensive error handling approach:

* **Invalid LLM responses**: Raises ClarifierError with detailed context about missing or malformed responses
* **Tool call validation**: Ensures correct function name (`make_clarifier_decision`) and valid parameters
* **JSON parsing errors**: Catches and re-raises with context about malformed arguments
* **Scope validation**: Ensures scope is provided when required and contains only valid values ("metadata" or "research")
* **Decision validation**: Validates all required fields are present in tool call arguments
* **Logging**: All errors logged with full stack traces using exc_info=True

## Security Considerations

* **Token handling**: Authentication tokens passed through without storage or logging
* **Input validation**: Validates conversation structure before processing
* **No data persistence**: Clarifier makes stateless decisions without storing conversation data
* **Error sanitization**: Error messages avoid exposing sensitive token information
* **Research statement sanitization**: Ensures no PII or sensitive data included in research statements

## Performance Notes

* **Model selection**: Uses large model capability for nuanced context analysis
* **Deterministic output**: Temperature=0.0 ensures consistent clarification decisions
* **Token optimization**: CO-STAR framework prompt cached via construct_system_prompt()
* **Non-streaming response**: Immediate decision return without streaming overhead
* **Decision efficiency**: Priority override rules enable fast-path processing for user overrides

---

Refer to the [agents-overview.md](./agents-overview.md) for details on how the Clarifier Agent fits into the overall IRIS system pipeline.