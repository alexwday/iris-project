# OpenAI Connector (`iris/src/llm_connectors/rbc_openai.py`)

This module provides a single connector to the OpenAI API that handles all types of calls including streaming, non-streaming, tool calls, and embeddings. It works in both RBC and local environments with comprehensive error handling, retry logic, and usage tracking.

## Overview

This module serves as the central OpenAI API interface for the IRIS system, providing a unified connector that handles all types of LLM interactions. It supports both RBC enterprise environments and local development setups, with comprehensive error handling, automatic retry logic, and detailed usage tracking. The connector manages streaming and non-streaming chat completions, tool calls, and embeddings while ensuring security through token masking and parameter filtering.

## Key Components

* **`rbc_openai.py`**: Main connector module containing all OpenAI API interaction functionality
* **`OpenAIConnectorError`**: Custom exception class for connector-specific errors

## Core Functions/Classes

### `call_llm(oauth_token, **params)`

#### Purpose
Makes unified calls to the OpenAI API handling all types of requests including streaming, non-streaming, tool calls, and embeddings with comprehensive error handling and retry logic.

#### Parameters
* **`oauth_token`** (str): Authentication token (OAuth token for RBC environment, OpenAI API key for local)
* **`prompt_token_cost`** (float, optional): Cost per 1K prompt tokens in USD (default: 0)
* **`completion_token_cost`** (float, optional): Cost per 1K completion tokens in USD (default: 0)
* **`database_name`** (str, optional): Database identifier for compatibility (default: None)
* **`**params`**: OpenAI API parameters including model, messages, and optional parameters like stream, tools, temperature, etc.

#### Returns
* **Varies by request type**: 
  - Non-streaming: Tuple of (api_response, usage_details)
  - Streaming: Iterator yielding chunks and final usage_details dict
  - Embeddings: Response object directly

#### Workflow
1. **Initialize OpenAI Client**: Create client with token and configure base URL from environment
2. **Process Parameters**: Set defaults, handle embedding flag, configure streaming options
3. **Execute Retry Loop**: Attempt API call up to MAX_RETRY_ATTEMPTS with delay between retries
4. **Make API Call**: Route to appropriate endpoint (chat completions or embeddings)
5. **Process Response**: Calculate usage details and return appropriate format based on request type
6. **Handle Errors**: Log detailed error information and raise OpenAIConnectorError if all retries fail

#### Error Handling
* **OpenAIConnectorError**: Raised when all retry attempts fail with detailed error context

### `_stream_wrapper(stream_iterator, model_name, prompt_token_cost, completion_token_cost, call_start_time)`

#### Purpose
Wraps OpenAI stream iterator to provide usage details as the final yielded item while maintaining full streaming functionality.

#### Parameters
* **`stream_iterator`** (Iterator): The OpenAI stream iterator
* **`model_name`** (str): Model name for usage tracking
* **`prompt_token_cost`** (float): Cost per 1K prompt tokens
* **`completion_token_cost`** (float): Cost per 1K completion tokens
* **`call_start_time`** (float): Overall start time for duration calculation

#### Returns
* **Iterator**: Yields stream chunks followed by final usage_details dictionary

#### Workflow
1. **Process Stream Chunks**: Yield each chunk from the OpenAI stream iterator
2. **Capture Usage Data**: Extract usage information from final chunk with `chunk.usage`
3. **Calculate Duration**: Measure total time from initial call start to stream completion
4. **Format Usage Details**: Create standardized usage details dictionary with cost calculation
5. **Yield Final Details**: Provide usage details as final item in `{'usage_details': {...}}` format

#### Error Handling
* **Missing Usage Data**: Yields error usage details dictionary if no usage data found in stream
* **Stream Consumption**: Ensures stream is fully consumed before yielding final details

### `calculate_cost(prompt_tokens, completion_tokens, prompt_token_cost, completion_token_cost)`

#### Purpose
Calculates total cost based on token usage and per-token costs using standard pricing formulas.

#### Parameters
* **`prompt_tokens`** (int): Number of prompt tokens used
* **`completion_tokens`** (int): Number of completion tokens used
* **`prompt_token_cost`** (float): Cost per 1K prompt tokens in USD
* **`completion_token_cost`** (float): Cost per 1K completion tokens in USD

#### Returns
* **float**: Total cost in USD

#### Workflow
1. **Calculate Prompt Cost**: (prompt_tokens / 1000) * prompt_token_cost
2. **Calculate Completion Cost**: (completion_tokens / 1000) * completion_token_cost
3. **Sum Total Cost**: Return combined prompt and completion costs

#### Error Handling
* No explicit error handling - function performs simple arithmetic calculations

## Configuration

Settings loaded from `env_config` module:

* **`BASE_URL`**: API base URL for OpenAI client (configured for RBC or local environment)
* **`MAX_RETRY_ATTEMPTS`**: Maximum number of retry attempts on API failures (default: 3)
* **`REQUEST_TIMEOUT`**: Request timeout in seconds for API calls (default: 180)
* **`RETRY_DELAY_SECONDS`**: Delay between retry attempts in seconds (default: 2)
* **`TOKEN_PREVIEW_LENGTH`**: Characters to show in token preview for secure logging (default: 7)

## Usage Examples

### Non-Streaming Chat Completion
```python
from iris.src.llm_connectors.rbc_openai import call_llm

response, usage = call_llm(
    oauth_token="your_token",
    model="gpt-4o-mini-2024-07-18",
    messages=[{"role": "user", "content": "Hello"}],
    prompt_token_cost=0.00016238,
    completion_token_cost=0.00065175,
    temperature=0.7,
    max_tokens=100
)

print(f"Response: {response.choices[0].message.content}")
print(f"Cost: ${usage['cost']:.6f}")
```

### Streaming Chat Completion
```python
stream = call_llm(
    oauth_token="your_token",
    model="gpt-4o-mini-2024-07-18",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
    prompt_token_cost=0.00016238,
    completion_token_cost=0.00065175
)

for chunk in stream:
    if isinstance(chunk, dict) and 'usage_details' in chunk:
        # Final usage details
        usage = chunk['usage_details']
        print(f"Total cost: ${usage['cost']:.6f}")
    else:
        # Regular content chunk
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='')
```

### Tool Calling
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
}]

response, usage = call_llm(
    oauth_token="your_token",
    model="gpt-4o-mini-2024-07-18",
    messages=[{"role": "user", "content": "What's the weather in Toronto?"}],
    tools=tools,
    tool_choice={"type": "function", "function": {"name": "get_weather"}},
    prompt_token_cost=0.00016238,
    completion_token_cost=0.00065175
)
```

### Embedding Request
```python
embedding_response = call_llm(
    oauth_token="your_token",
    model="text-embedding-3-large",
    input="Text to embed",
    is_embedding=True,
    dimensions=1024
)

embedding_vector = embedding_response.data[0].embedding
```

## Error Handling

The connector provides comprehensive error handling:

* **Network Errors**: Automatic retries with exponential backoff
* **API Errors**: Detailed logging with error context
* **Authentication Errors**: Clear error messages for token issues
* **Timeout Errors**: Configurable timeout with retry logic
* **Parameter Validation**: Basic validation of required parameters

## Integration Points

This connector is used throughout the IRIS system:
* **Agent Pipeline**: All agents use this connector for LLM calls
* **Database Subagents**: Tool calling and content synthesis
* **Direct Response**: Streaming and non-streaming responses
* **Router/Clarifier/Planner**: Decision-making tool calls
* **Summarizer**: Content synthesis and streaming

## Dependencies

* **openai**: Official OpenAI Python client library
* **logging**: For detailed operational logging
* **time**: For timing and retry delay functionality
* **typing**: For type hints and documentation
* **env_config**: For configuration settings

## Error Handling

Comprehensive error handling approach:

* **Retry Logic**: Automatic retries up to MAX_RETRY_ATTEMPTS with configurable delays between attempts
* **OpenAIConnectorError**: Custom exception raised when all retry attempts fail with detailed error context
* **Detailed Logging**: Comprehensive logging of errors, retry attempts, and timing information
* **Safe Parameter Logging**: Excludes sensitive message content from logs while preserving debugging information
* **Stream Error Handling**: Ensures streaming responses are properly handled even when usage data is missing
* **Graceful Degradation**: Provides fallback behavior for missing usage data in streams

## Security Considerations

* **Token Masking**: Shows only first few characters of authentication tokens in logs for security
* **Parameter Filtering**: Excludes message content and sensitive parameters from operational logging
* **Secure Base URL**: Uses configured RBC base URL for enterprise environments with proper authentication
* **Error Information**: Detailed error logging without exposing sensitive data or credentials
* **Safe Logging**: Prevents accidental exposure of user queries or responses in log files

## Performance Notes

* **Retry Strategy**: Configurable retry attempts with exponential backoff to handle transient failures
* **Timeout Management**: Configurable request timeouts to prevent indefinite blocking
* **Streaming Efficiency**: Proper stream handling with minimal memory overhead for large responses
* **Usage Tracking**: Efficient token counting and cost calculation without impacting response times
* **Connection Reuse**: OpenAI client instances configured for optimal connection management

---

This connector provides reliable, secure, and comprehensive OpenAI API access for all IRIS LLM operations with detailed usage tracking and error handling.