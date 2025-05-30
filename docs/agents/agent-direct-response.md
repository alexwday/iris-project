# Agent Direct Response (`iris/src/agents/agent_direct_response/`)

The Direct Response Agent generates comprehensive answers based solely on conversation context without requiring additional database research. It is activated by the Router agent when sufficient information exists in the conversation history.

## Overview

The Direct Response Agent serves as the conversation-based response generator in the IRIS workflow. It analyzes conversation history to extract relevant information and formulate clear, structured responses without accessing databases. The agent employs the CO-STAR framework for sophisticated natural language generation and implements strict anti-hallucination measures to ensure responses are based only on explicitly available conversation context. It uses streaming response delivery for better user experience.

## Key Components

* **`response_from_conversation.py`**: Implements streaming direct response generation with the main function `response_from_conversation`. Processes conversation history to generate contextual responses. Yields content chunks progressively followed by usage details.
* **`response_settings.py`**: Defines sophisticated CO-STAR framework configuration with detailed response structuring guidelines. Uses 'large' model capability with higher temperature (0.7) for natural conversation. Provides extensive response structure templates.

## Core Functions/Classes

### `response_from_conversation(conversation, token)`

#### Purpose
Generates comprehensive, well-structured responses based solely on information present in the conversation history, using streaming delivery for progressive content display.

#### Parameters
* **`conversation`** (dict): Dictionary with 'messages' key containing conversation history
* **`token`** (str): Authentication token for API access (OAuth token in RBC environment, API key in local environment)

#### Returns
* **Generator[Any, None, None]**: Yields multiple items:
  - Content chunks (str): Progressive response content as it's generated
  - Final usage details (dict): Last yielded item containing usage information
    ```python
    {'usage_details': {
        'model': str,
        'prompt_tokens': int,
        'completion_tokens': int,
        'cost': float,
        'response_time_ms': int
    }}
    ```

#### Workflow
1. **System Prompt Preparation**: Constructs system message using CO-STAR framework prompt
2. **Message Assembly**: Combines system prompt with conversation history
3. **Streaming LLM Call**: Invokes LLM with streaming enabled for progressive delivery
4. **Content Chunk Processing**: Yields content strings as they arrive from the stream
5. **Usage Details Capture**: Detects and captures final usage details from stream
6. **Final Yield**: Yields usage details dictionary as last generator item

#### Error Handling
* **DirectResponseError**: Raised for streaming failures or processing errors
* **Stream interruption**: Handles incomplete streams gracefully
* **Usage data fallback**: Provides error usage details if stream data missing
* **Exception logging**: Comprehensive error logging with stack traces via exc_info

### `DirectResponseError` (Exception Class)

#### Purpose
Custom exception class for direct response generation failures, providing clear error context for streaming and content generation issues.

## Configuration

Settings used from `response_settings.py`:

* **`MODEL_CAPABILITY`**: "large" - Uses advanced model for sophisticated natural language generation
* **`MAX_TOKENS`**: 4096 - Maximum tokens for comprehensive response generation
* **`TEMPERATURE`**: 0.7 - Higher temperature for natural, conversational responses
* **`SYSTEM_PROMPT`**: Comprehensive CO-STAR framework prompt with response templates

## Usage Examples

### Basic Usage
```python
from iris.src.agents.agent_direct_response.response_from_conversation import response_from_conversation

# Query with sufficient conversation context
conversation = {
    "messages": [
        {"role": "user", "content": "What is IFRS 15?"},
        {"role": "assistant", "content": "[Previous research about IFRS 15...]"},
        {"role": "user", "content": "Can you summarize the key points?"}
    ]
}

# Stream the response
for chunk in response_from_conversation(conversation, auth_token):
    if isinstance(chunk, dict) and 'usage_details' in chunk:
        # Final usage details
        usage = chunk['usage_details']
    else:
        # Content chunk
        print(chunk, end='', flush=True)
```

### Advanced Usage
```python
# Handle insufficient context scenario
conversation = {
    "messages": [
        {"role": "user", "content": "What are the depreciation methods?"}
    ]
}

# Agent will acknowledge limited context
for chunk in response_from_conversation(conversation, auth_token):
    if isinstance(chunk, str):
        # Will yield content acknowledging need for research
        print(chunk, end='')
    else:
        # Process usage details
        pass
```

## Integration Points

How the Direct Response Agent integrates with other IRIS components:

* **Router Agent**: Activated when Router determines sufficient conversation context exists
* **Chat Model**: Receives conversation history and returns streaming response
* **Global Prompts**: Incorporates all four global prompt components for context awareness
* **Streaming Infrastructure**: Uses RBC OpenAI connector's streaming capabilities

## Dependencies

* **`logging`**: Comprehensive operation logging and error tracking
* **`typing`**: Type hints for generator functions and return values
* **Internal modules**: 
  - `env_config`: Model configuration and capability settings
  - `rbc_openai`: LLM connector for streaming OpenAI API calls
  - `global_prompts`: All four global prompt components for comprehensive context
  - `response_settings`: CO-STAR framework configuration and response structure templates

## Error Handling

Comprehensive error handling approach:

* **Stream processing errors**: Handles streaming interruptions and malformed chunks
* **Usage data extraction**: Manages missing or malformed usage details from stream
* **Content validation**: Ensures proper chunk format before yielding
* **Fallback mechanisms**: Provides error usage details when stream data unavailable
* **Exception propagation**: Re-raises as DirectResponseError with context
* **Logging**: All errors logged with full stack traces using exc_info=True

## Security Considerations

* **Token handling**: Authentication tokens passed through without storage or logging
* **Context isolation**: Strictly uses only conversation history, no external data access
* **Anti-hallucination**: Enforces conversation-only information sourcing
* **No database access**: Completely isolated from database systems
* **PII protection**: No persistence of conversation data or responses

## Performance Notes

* **Streaming efficiency**: Progressive content delivery improves perceived responsiveness
* **Model selection**: Large model provides nuanced, context-aware responses
* **Temperature tuning**: 0.7 balances coherence with natural variation
* **Token optimization**: CO-STAR framework prompt cached via construct_system_prompt()
* **Generator pattern**: Memory-efficient streaming without buffering entire response

---

Refer to the [agents-overview.md](./agents-overview.md) for details on how the Direct Response Agent fits into the overall IRIS system pipeline.