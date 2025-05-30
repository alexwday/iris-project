# Conversation Setup (`iris/src/initial_setup/conversation_setup.py`)

The conversation setup module handles processing and filtering of conversation histories for language models. It standardizes different conversation formats, filters by role, and manages history length to optimize LLM processing and API efficiency.

## Overview

This module provides essential preprocessing for all conversation data flowing through the IRIS system. It normalizes various input formats into a standardized structure, applies role-based filtering, and manages conversation history length to ensure optimal performance with language model APIs.

## Key Components

* **`conversation_setup.py`**: Contains the main conversation processing logic with filtering, validation, and standardization functions

## Core Functions/Classes

### `process_conversation(conversation)`

#### Purpose
Processes and filters conversation history based on configured settings, extracting only required fields and applying role-based filtering.

#### Parameters
* **`conversation`** (Any): Raw conversation data in flexible formats - either a list of messages or a dictionary with "messages" key

#### Returns
* **Dict[str, List[Dict[str, str]]]**: Filtered conversation data with standardized message structure containing only "role" and "content" fields

#### Workflow
1. **Input Normalization**: Accepts flexible input formats and normalizes to standard dictionary with "messages" array
2. **Format Validation**: Validates conversation structure and ensures "messages" key exists
3. **Message Validation**: Checks each message for required "role" and "content" fields
4. **Role Filtering**: Filters messages based on `ALLOWED_ROLES` configuration and optional system message inclusion
5. **Field Extraction**: Creates new message objects containing only required fields to reduce payload size
6. **History Management**: Limits conversation to most recent `MAX_HISTORY_LENGTH` messages
7. **Statistics Logging**: Logs processing statistics showing original vs. filtered message counts

#### Error Handling
* **ValueError**: Raised for invalid conversation formats or missing required fields
* **Exception**: General exception handling with comprehensive error logging
* **Graceful Degradation**: Skips invalid messages rather than failing completely

## Configuration

Settings used from `env_config`:

* **`ALLOWED_ROLES`**: List of message roles to include in filtered output (default: ["user", "assistant"])
* **`INCLUDE_SYSTEM_MESSAGES`**: Boolean flag to include system messages regardless of role filtering
* **`MAX_HISTORY_LENGTH`**: Maximum number of recent messages to retain for processing

## Usage Examples

### Basic Conversation Processing
```python
from iris.src.initial_setup.conversation_setup import process_conversation

conversation = [
    {"role": "user", "content": "What is Python?"},
    {"role": "assistant", "content": "Python is a programming language."}
]

filtered_conversation = process_conversation(conversation)
# Returns: {"messages": [{"role": "user", "content": "What is Python?"}, ...]}
```

### Dictionary Format Input
```python
conversation_dict = {
    "messages": [
        {"role": "user", "content": "Hello", "timestamp": "2024-01-01"},
        {"role": "assistant", "content": "Hi there!", "metadata": {"model": "gpt-4"}}
    ]
}

filtered = process_conversation(conversation_dict)
# Returns only role and content fields, filtering out extra metadata
```

## Integration Points

How this module integrates with other IRIS components:

* **Chat Model**: Provides preprocessed conversation data for LLM API calls
* **Agent Router**: Ensures consistent conversation format across all agent interactions
* **API Endpoints**: Standardizes conversation data from various client input formats
* **Process Monitor**: Logs conversation processing statistics for performance tracking

## Dependencies

* **`logging`**: Comprehensive logging of processing steps and statistics
* **`typing`**: Type hints for function signatures and return values
* **Internal modules**: `env_config` for configuration settings

## Error Handling

Comprehensive error handling approach:

* **Format Validation**: Validates input conversation structure before processing
* **Required Field Checking**: Ensures all messages have mandatory "role" and "content" fields
* **Graceful Message Skipping**: Logs warnings for invalid messages but continues processing
* **Exception Propagation**: Re-raises exceptions after logging for proper error handling upstream

## Security Considerations

* **Data Sanitization**: Extracts only required fields to prevent sensitive metadata leakage
* **Input Validation**: Validates conversation structure to prevent injection attacks
* **Logging Safety**: Careful logging to avoid exposing sensitive conversation content
* **Memory Management**: Limits history length to prevent memory exhaustion attacks

## Performance Notes

* **Payload Optimization**: Reduces message payload size by extracting only required fields
* **Memory Efficiency**: Limits conversation history to prevent excessive memory usage
* **Processing Speed**: Efficient filtering and validation with minimal overhead
* **API Optimization**: Standardized format reduces API processing time and token usage

---

[Related Documentation: Environment Configuration (`env_config.py`), Chat Model (`model.py`)]