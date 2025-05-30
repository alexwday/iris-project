# Agent Router (`iris/src/agents/agent_router/`)

The Router Agent serves as the entry point and decision-making hub for the IRIS system pipeline. It analyzes user queries and determines the optimal processing path - either direct response from conversation context or database research - using advanced prompt engineering and LLM tool calling.

## Overview

The Router Agent is the first component in the IRIS workflow that processes every user query. It performs intelligent routing decisions by analyzing conversation context and query content to determine whether sufficient information exists for a direct response or if database research is required. The agent uses the CO-STAR framework (Context, Objective, Style, Tone, Audience, Response) for structured prompt engineering and enforces routing through LLM tool calling for consistent, deterministic decisions.

## Key Components

* **`router.py`**: Implements the core routing logic with the main function `get_routing_decision`. Uses LLM tool calling to analyze conversation context and make structured routing decisions. Returns a tuple containing the routing decision and usage details.
* **`router_settings.py`**: Defines comprehensive configuration using the CO-STAR framework. Integrates all global prompt components (project, fiscal, database, restrictions) and provides detailed routing criteria with examples. Constructs the complete system prompt dynamically.

## Core Functions/Classes

### `get_routing_decision(conversation, token)`

#### Purpose
Analyzes user queries and conversation history to determine the optimal processing path through the IRIS system, returning either `response_from_conversation` or `research_from_database`.

#### Parameters
* **`conversation`** (dict): Dictionary with 'messages' key containing conversation history
* **`token`** (str): Authentication token for API access (OAuth token in RBC environment, API key in local environment)

#### Returns
* **Tuple[Dict[str, Any], Optional[Dict[str, Any]]]**: 
  - First element: Routing decision dictionary with 'function_name' key containing either "response_from_conversation" or "research_from_database"
  - Second element: Usage details dictionary with token usage, cost, and timing information (or None on error)

#### Workflow
1. **System Prompt Preparation**: Constructs system message using CO-STAR framework prompt from router_settings
2. **Message Assembly**: Combines system prompt with conversation history for context
3. **LLM Tool Call**: Invokes LLM with forced tool choice for `route_query` function
4. **Response Validation**: Validates tool call presence and extracts routing decision
5. **Decision Extraction**: Parses JSON arguments to get function_name
6. **Usage Tracking**: Captures and returns token usage and cost metrics

#### Error Handling
* **RouterError**: Raised for invalid responses, missing tool calls, or malformed JSON
* **Exception logging**: Comprehensive error logging with stack traces via exc_info
* **Validation failures**: Specific handling for missing or incorrect function names

### `RouterError` (Exception Class)

#### Purpose
Custom exception class for router-specific errors, providing clear error context for routing failures.

## Configuration

Settings used from `router_settings.py`:

* **`MODEL_CAPABILITY`**: "small" - Uses efficient model for quick routing decisions
* **`MAX_TOKENS`**: 4096 - Maximum tokens for comprehensive context analysis
* **`TEMPERATURE`**: 0.0 - Ensures deterministic, consistent routing decisions
* **`TOOL_DEFINITIONS`**: Defines `route_query` tool with two valid enum options

## Usage Examples

### Basic Usage
```python
from iris.src.agents.agent_router.router import get_routing_decision

# Prepare conversation with user query
conversation = {
    "messages": [
        {"role": "user", "content": "What does IFRS 15 say about revenue recognition?"}
    ]
}

# Get routing decision
decision, usage = get_routing_decision(conversation, auth_token)
# Returns: ({"function_name": "research_from_database"}, usage_details)
```

### Advanced Usage
```python
# Multi-turn conversation with context
conversation = {
    "messages": [
        {"role": "user", "content": "What is revenue recognition?"},
        {"role": "assistant", "content": "[Previous research results about revenue recognition]"},
        {"role": "user", "content": "Can you summarize what we just discussed?"}
    ]
}

# Router recognizes sufficient context exists
decision, usage = get_routing_decision(conversation, auth_token)
# Returns: ({"function_name": "response_from_conversation"}, usage_details)
```

## Integration Points

How the Router Agent integrates with other IRIS components:

* **Chat Model**: Receives queries from the main chat interface and returns routing decisions
* **Direct Response Agent**: Triggered when `response_from_conversation` is selected
* **Research Pipeline**: Initiates Clarifier → Planner → Database → Summarizer flow when `research_from_database` is selected
* **Global Prompts**: Incorporates all four global prompt components for comprehensive context

## Dependencies

* **`json`**: JSON parsing for tool call arguments
* **`logging`**: Comprehensive operation logging and error tracking
* **`typing`**: Type hints for function signatures and return values
* **Internal modules**: 
  - `env_config`: Model configuration and capability settings
  - `rbc_openai`: LLM connector for OpenAI API calls
  - `global_prompts`: All four global prompt components (project, fiscal, database, restrictions)
  - `router_settings`: CO-STAR framework configuration and tool definitions

## Error Handling

Comprehensive error handling approach:

* **Invalid LLM responses**: Raises RouterError with detailed context about missing or malformed responses
* **Tool call validation**: Ensures correct function name (`route_query`) and valid parameters
* **JSON parsing errors**: Catches and re-raises with context about malformed arguments
* **Fallback behavior**: For ambiguous queries, always defaults to `research_from_database` for safety
* **Logging**: All errors logged with full stack traces using exc_info=True

## Security Considerations

* **Token handling**: Authentication tokens passed through without storage or logging
* **Input validation**: Validates conversation structure before processing
* **No data persistence**: Router makes stateless decisions without storing conversation data
* **Error sanitization**: Error messages avoid exposing sensitive token information

## Performance Notes

* **Model efficiency**: Uses small model capability for fast routing decisions (typically <1 second)
* **Deterministic output**: Temperature=0.0 ensures consistent routing for identical queries
* **Token optimization**: CO-STAR framework prompt cached via construct_system_prompt()
* **Non-streaming response**: Immediate decision return without streaming overhead

---

Refer to the [agents-overview.md](./agents-overview.md) for details on how the Router Agent fits into the overall IRIS system pipeline.
