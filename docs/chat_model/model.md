# Model Orchestration (`iris/src/chat_model/model.py`)

Core orchestration module that serves as the main entry point for the IRIS application, managing the complete agent pipeline from user query to final response with both synchronous and asynchronous interfaces.

## Overview

The model.py module provides the central orchestration layer for the IRIS system, coordinating the entire workflow from initial setup through agent execution to final response generation. It uses an asynchronous core for parallel processing while maintaining a synchronous interface for compatibility with standard Python iteration patterns.

## Core Functions/Classes

### `model(conversation_dict)`

#### Purpose
Synchronous wrapper function that provides a generator interface for compatibility with existing systems while leveraging async processing internally.

#### Parameters
* **`conversation_dict`** (dict): Dictionary containing conversation messages and metadata

#### Returns
* **Generator[str]**: Yields response chunks as strings for real-time streaming

#### Workflow
1. **Validation**: Validates input conversation structure
2. **Async Execution**: Runs the async core function in a thread pool
3. **Streaming**: Yields response chunks as they become available
4. **Error Handling**: Catches and formats any processing errors

### `_model_generator(conversation_dict)`

#### Purpose
Core synchronous generator that handles the complete IRIS agent workflow, including setup, agent coordination, and response generation.

#### Parameters
* **`conversation_dict`** (dict): Dictionary containing conversation messages and metadata

#### Returns
* **Generator[str]**: Yields response chunks and processing updates

#### Workflow
1. **Initial Setup**: SSL certificates, OAuth authentication, logging configuration
2. **Agent Pipeline**: Router → Clarifier → Planner → Database Router/Subagents → Summarizer/Direct Response
3. **Concurrent Processing**: Parallel database query execution using ThreadPoolExecutor
4. **Response Generation**: Final response assembly and streaming
5. **Usage Reporting**: Token usage and timing information formatting

### `process_request_async(conversation_list, stream=False)`

#### Purpose
Async wrapper function designed for FastAPI integration, providing non-blocking request processing.

#### Parameters
* **`conversation_list`** (list): List of conversation dictionaries
* **`stream`** (bool, optional): Whether to return streaming response (default: False)

#### Returns
* **Dict**: Response dictionary containing result, timing, and metadata

#### Workflow
1. **Async Processing**: Non-blocking execution of the model pipeline
2. **Response Assembly**: Collects all response chunks into final result
3. **Metadata Collection**: Gathers timing, agent usage, and token information
4. **FastAPI Integration**: Returns structured response for web API consumption

### `_execute_query_worker(database_subagent_info, user_query, llm_call_log)`

#### Purpose
Worker function for concurrent database query execution, enabling parallel processing of multiple database subagents.

#### Parameters
* **`database_subagent_info`** (dict): Subagent configuration and routing information
* **`user_query`** (str): User's query to be processed by the subagent
* **`llm_call_log`** (list): Shared log for tracking LLM API calls

#### Returns
* **Tuple**: (database_name, result_dict) containing subagent results

#### Workflow
1. **Subagent Invocation**: Calls the appropriate database subagent
2. **Error Isolation**: Handles individual subagent failures without affecting others
3. **Result Assembly**: Formats and returns subagent response data
4. **Logging Integration**: Updates shared LLM call log for usage tracking

### `format_usage_summary(agent_token_usage, start_time=None)`

#### Purpose
Formats token usage and timing information into a human-readable summary for display and logging.

#### Parameters
* **`agent_token_usage`** (dict): Accumulated token usage with prompt/completion/total tokens and cost
* **`start_time`** (str, optional): Start timestamp for processing time calculation

#### Returns
* **str**: Formatted usage summary string

### `format_remaining_queries(remaining_queries)`

#### Purpose
Formats unprocessed database queries for display when some queries couldn't be completed.

#### Parameters
* **`remaining_queries`** (list): List of unprocessed query dictionaries

#### Returns
* **str**: Formatted string listing remaining queries

## Configuration

Settings managed through environment configuration and model settings:

* **`SHOW_USAGE_SUMMARY`**: Controls display of token usage information (default: True)
* **`MAX_WORKERS`**: ThreadPoolExecutor worker count for concurrent database queries
* **`TIMEOUT_SETTINGS`**: Request timeout configurations for various operations
* **`ENVIRONMENT_FLAGS`**: Local vs. RBC environment detection and configuration

## Usage Examples

### Basic Synchronous Usage
```python
from iris.src.chat_model.model import model

conversation_dict = {
    "messages": [
        {"role": "user", "content": "What is the revenue recognition policy?"}
    ]
}

# Stream response chunks
for chunk in model(conversation_dict):
    print(chunk, end='')
```

### Async FastAPI Integration
```python
from iris.src.chat_model.model import process_request_async

async def handle_chat_request(conversation_list):
    result = await process_request_async(conversation_list, stream=False)
    return {
        "response": result["response"],
        "processing_time": result["processing_time_ms"],
        "agent_used": result["agent_used"],
        "token_usage": result.get("token_usage", {})
    }
```

### Streaming Response
```python
# For real-time streaming in web applications
for chunk in model(conversation_dict):
    # Send chunk to client immediately
    yield f"data: {chunk}\n\n"
```

## Integration Points

This module serves as the central integration hub for the entire IRIS system:

* **All Agent Types**: Coordinates Router, Clarifier, Planner, Database Subagents, Summarizer, and Direct Response agents
* **Setup Systems**: Integrates SSL, OAuth, logging, and conversation processing setup
* **Database Operations**: Manages concurrent database queries through ThreadPoolExecutor
* **Process Monitoring**: Integrates with process monitoring for execution tracking and debugging
* **FastAPI Framework**: Provides async wrappers for web API compatibility
* **LLM Connectors**: Interfaces with RBC OpenAI connector for model API calls

## Dependencies

* **`concurrent.futures`**: ThreadPoolExecutor for parallel database query execution
* **`logging`**: Comprehensive operational logging throughout the pipeline
* **`time`** and **`datetime`**: Timing and timestamp management for performance tracking
* **`uuid`**: Unique run identification for debugging and monitoring
* **`json`**: Debug data serialization and structured logging
* **`typing`**: Type hints for better code documentation and IDE support
* **All IRIS modules**: Agents, setup modules, global prompts, and LLM connectors

## Error Handling

Comprehensive error handling ensures system resilience:

* **Agent Pipeline Failures**: Individual agent failures are caught and logged without stopping the entire pipeline
* **Database Query Errors**: Concurrent query failures are isolated per database and don't affect other subagents
* **Setup Failures**: SSL, OAuth, and configuration failures are handled with appropriate fallbacks
* **Threading Exceptions**: Thread pool exceptions are caught and processed individually
* **Process Monitoring Resilience**: Monitoring failures do not impact core functionality
* **API Call Failures**: LLM API failures are handled with retry logic and graceful degradation

## Security Considerations

* **OAuth Token Management**: Secure handling and masking of authentication tokens in logs
* **SSL Certificate Validation**: Proper SSL certificate setup and validation
* **Process Monitoring Security**: Sensitive information filtering in monitoring logs
* **Database Security**: Secure connection handling with proper credential management
* **Error Information Sanitization**: Error logging designed to avoid exposing sensitive system details
* **Request Validation**: Input validation to prevent injection attacks and malformed requests

## Performance Notes

* **Concurrent Processing**: ThreadPoolExecutor enables parallel database queries for significantly improved performance
* **Streaming Architecture**: Generator-based design supports real-time response streaming for better user experience
* **Memory Management**: Efficient handling of large response datasets through streaming to prevent memory issues
* **Connection Pooling**: Proper database connection lifecycle management to prevent resource leaks
* **Async Compatibility**: Async wrappers enable non-blocking FastAPI integration for high-concurrency scenarios
* **Process Monitoring Optimization**: Monitoring designed to have minimal impact on core processing performance

---

This model orchestration module ensures efficient, secure, and reliable coordination of all IRIS system components while providing both synchronous and asynchronous interfaces for different integration requirements.