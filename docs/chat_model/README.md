# Chat Model Orchestration (`iris/src/chat_model/`)

This directory contains the core orchestration logic for the IRIS system. It defines how the different agents in the pipeline interact to process a user query, manage environment settings, and generate a response, including handling concurrent database operations and process monitoring.

## Overview

The chat model system serves as the central orchestration layer for the IRIS system, managing the complete agent pipeline from user query to final response. It coordinates the entire workflow including initial setup (SSL, OAuth, logging, process monitoring), agent invocation (Router, Clarifier, Planner, Database Router/Subagents, Summarizer/Direct Response), concurrent database operations, and final output generation. The system provides both synchronous generator interfaces for compatibility and async wrappers for FastAPI integration.

## Key Components

* **`model.py`**: Central orchestration script managing the entire agent pipeline with synchronous and async interfaces
* **`model_settings.py`**: Configuration settings for environment management (local vs. RBC) and model configurations

## Core Functions/Classes

### Main Orchestration Module (`model.py`)

#### Purpose
Central orchestration script that manages the entire IRIS agent pipeline from user query to final response, handling both direct response and database research paths.

#### Key Functions
* `model()`: Synchronous wrapper providing generator interface for compatibility
* `_model_generator()`: Core synchronous generator handling the complete agent workflow
* `process_request_async()`: Async wrapper for FastAPI integration
* `_execute_query_worker()`: Worker function for concurrent database query execution
* `format_usage_summary()`: Formats token usage and timing information
* `format_remaining_queries()`: Formats unprocessed database queries for display

#### Integration
Central entry point for all IRIS system interactions, coordinates all agents and manages the complete processing pipeline

### Model Settings Module (`model_settings.py`)

#### Purpose
Contains configuration settings for environment management (local vs. RBC) and model configurations for different capabilities.

#### Key Functions
* `get_model_config()`: Retrieves settings based on capability and environment
* Environment flags and API endpoint definitions
* Model configuration management for 'small', 'large', 'embedding' capabilities

## Configuration

Settings managed through model_settings.py and environment configuration:

* **Environment Management**: Local vs. RBC environment detection and configuration
* **Model Configurations**: Names, costs, and capabilities for 'small', 'large', 'embedding' models  
* **API Endpoints**: Environment-specific endpoint configurations
* **Usage Display**: Settings for showing usage summaries (SHOW_USAGE_SUMMARY)
* **Request Parameters**: Timeout, retry, and other request-specific configurations

## Usage Examples

### Basic Model Usage
```python
from iris.src.chat_model.model import model

conversation_dict = {
    "messages": [
        {"role": "user", "content": "What is the current accounting policy for revenue recognition?"}
    ]
}

# Process conversation through agent pipeline
for chunk in model(conversation_dict):
    print(chunk, end='')
```

### Async FastAPI Usage
```python
from iris.src.chat_model.model import process_request_async

async def handle_request(conversation_list):
    result = await process_request_async(conversation_list, stream=False)
    return {
        "response": result["response"],
        "processing_time": result["processing_time_ms"],
        "agent_used": result["agent_used"]
    }
```

## Integration Points

This module serves as the central integration point for the entire IRIS system:

* **All Agent Types**: Coordinates Router, Clarifier, Planner, Database Subagents, Summarizer, and Direct Response agents
* **Process Monitoring**: Integrates with process monitoring system for execution tracking
* **Database Operations**: Manages concurrent database queries through ThreadPoolExecutor
* **FastAPI Integration**: Provides async wrappers for web API compatibility
* **Setup Systems**: Coordinates SSL, OAuth, logging, and conversation processing

## Dependencies

* **concurrent.futures**: For concurrent database query execution using ThreadPoolExecutor
* **logging**: For comprehensive operational logging throughout the pipeline
* **time** and **datetime**: For timing and timestamp management
* **uuid**: For unique run identification
* **json**: For debug data serialization
* **typing**: For type hints and documentation
* **All IRIS modules**: Agents, setup modules, global prompts, and LLM connectors

## Error Handling

Comprehensive error handling throughout the orchestration pipeline:

* **Agent Failures**: Individual agent failures are caught and logged without stopping the pipeline
* **Database Query Errors**: Concurrent query failures are isolated and reported per database
* **Setup Failures**: SSL, OAuth, and configuration failures are handled with appropriate fallbacks
* **Process Monitoring Resilience**: Monitoring failures do not impact core functionality
* **Exception Isolation**: Thread pool exceptions are caught and processed individually
* **Database Logging Failures**: Database connection and logging errors are handled gracefully

## Security Considerations

* **OAuth Token Management**: Secure handling of authentication tokens with proper masking in logs
* **SSL Certificate Setup**: Proper SSL certificate validation and configuration
* **Process Monitoring Security**: Sensitive information filtered from process monitoring logs
* **Database Security**: Secure database connection handling with proper credential management
* **Error Information**: Error logging designed to avoid exposing sensitive system details

## Performance Notes

* **Concurrent Processing**: ThreadPoolExecutor enables parallel database queries for improved performance
* **Streaming Support**: Generator-based architecture supports real-time response streaming
* **Process Monitoring Optimization**: Monitoring designed to have minimal impact on processing performance
* **Memory Management**: Efficient handling of large response datasets through streaming
* **Connection Management**: Proper database connection lifecycle management to prevent resource leaks
* **Async Compatibility**: Async wrappers enable non-blocking FastAPI integration

---

This chat model orchestration system ensures efficient, secure, and reliable coordination of all IRIS system components while providing both synchronous and asynchronous interfaces for different integration requirements.
