# LLM Connectors (`iris/src/llm_connectors/`)

This directory contains connectors that interface with large language model (LLM) APIs, primarily the OpenAI API. These connectors abstract the details of API calls, handling streaming, non-streaming, and tool calls, and provide a unified interface for the rest of the IRIS system.

## Overview

The LLM connectors system provides unified interfaces for large language model API interactions within the IRIS system. These connectors abstract the complexities of different API implementations, handle authentication across environments (RBC vs local), manage streaming and non-streaming responses, implement retry logic, and provide comprehensive usage tracking. The system ensures reliable, secure, and efficient communication with LLM services while maintaining detailed operational monitoring.

## Key Components

* **`rbc_openai.py`**: Main OpenAI connector supporting all call types with authentication, retry logic, and usage tracking
* **`__init__.py`**: Marks the directory as a Python package

## Core Functions/Classes

### OpenAI Connector Module (`rbc_openai.py`)

#### Purpose
Provides unified interface for OpenAI API interactions supporting all call types including streaming, non-streaming, tool calls, and embeddings with comprehensive error handling and usage tracking.

#### Key Functions
* `call_llm()`: Main function handling all OpenAI API call types with retry logic and usage tracking
* `_stream_wrapper()`: Helper function wrapping streaming responses to provide usage details
* `calculate_cost()`: Calculates costs based on token usage and per-token pricing
* `OpenAIConnectorError`: Custom exception class for connector-specific errors

#### Integration
Central LLM interface used by all agents throughout the IRIS system for language model interactions

## Configuration

Settings loaded from environment configuration:

* **API Base URLs**: Environment-specific endpoints for RBC vs local environments
* **Retry Parameters**: Maximum retry attempts and delay settings between retries
* **Timeout Settings**: Request timeout configurations for API calls
* **Token Preview Length**: Characters shown in logs for secure token display
* **Usage Tracking**: Cost calculation parameters and usage monitoring settings

## Usage Examples

### Basic Chat Completion
```python
from iris.src.llm_connectors.rbc_openai import call_llm

response, usage = call_llm(
    oauth_token="your_token",
    model="gpt-4o-mini-2024-07-18",
    messages=[{"role": "user", "content": "Hello"}],
    prompt_token_cost=0.00016238,
    completion_token_cost=0.00065175
)
```

### Streaming Response
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
        usage = chunk['usage_details']
    else:
        # Process content chunk
        pass
```

### Tool Calling
```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}
    }
}]

response, usage = call_llm(
    oauth_token="your_token",
    model="gpt-4o-mini-2024-07-18", 
    messages=[{"role": "user", "content": "What's the weather?"}],
    tools=tools,
    tool_choice={"type": "function", "function": {"name": "get_weather"}}
)
```

## Integration Points

This module serves as the LLM interface for the entire IRIS system:

* **All Agent Types**: Router, Clarifier, Planner, Database Subagents, Summarizer, and Direct Response agents
* **Streaming Support**: Real-time response streaming for user interface integration
* **Tool Calling**: Function calling capabilities for agent decision-making and data retrieval
* **Embedding Generation**: Vector embeddings for document similarity and search operations
* **Usage Monitoring**: Comprehensive token and cost tracking for operational monitoring

## Dependencies

* **openai**: Official OpenAI Python SDK for API interaction
* **logging**: Comprehensive operational logging throughout the connection lifecycle
* **time**: Timing measurements and retry delay functionality
* **typing**: Type hints for improved code documentation and IDE support
* **env_config**: Environment-specific configuration settings

## Error Handling

Robust error handling throughout the LLM interaction process:

* **Automatic Retries**: Configurable retry attempts with delays for transient failures
* **OpenAIConnectorError**: Custom exception for connector-specific failures with detailed context
* **Detailed Logging**: Comprehensive error logging for troubleshooting and monitoring
* **Stream Error Handling**: Proper handling of streaming response interruptions and failures
* **Authentication Errors**: Clear error reporting for token and authentication issues
* **Timeout Management**: Configurable timeouts with appropriate error handling

## Security Considerations

* **Token Masking**: Authentication tokens masked in logs showing only preview characters
* **Parameter Filtering**: Sensitive request content excluded from operational logs
* **Secure Base URLs**: Environment-specific API endpoints with proper authentication
* **Error Information**: Error logging designed to avoid exposing sensitive data or credentials
* **Connection Security**: Secure HTTPS connections with proper certificate validation

## Performance Notes

* **Connection Reuse**: Efficient OpenAI client configuration for optimal connection management
* **Retry Strategy**: Intelligent retry logic to handle transient API failures without excessive delays
* **Streaming Efficiency**: Low-latency streaming response handling with minimal memory overhead
* **Usage Tracking**: Efficient token counting and cost calculation without impacting response times
* **Timeout Optimization**: Balanced timeout settings to prevent hanging while allowing for model processing time

---

This LLM connectors system ensures reliable, secure, and efficient communication with language model APIs while providing comprehensive monitoring and error handling for all IRIS system interactions.
