# Conversation Setup (`iris/src/conversation_setup/`)

This directory contains modules responsible for processing and managing conversation histories for use with language models within the IRIS system. It standardizes conversation formats, filters messages by role, and manages conversation history length to ensure consistent and relevant input to the agents.

## Key Components

* **`conversation.py`**: Implements the core conversation processing logic. The main function `process_conversation` filters and formats raw conversation data, supporting multiple input formats. It extracts only required fields (role and content), filters messages based on allowed roles and system message inclusion settings, and limits the conversation history to a configured maximum length.
* **`conversation_settings.py`**: Contains configuration settings for conversation processing, including allowed roles, whether to include system messages, and maximum history length.
* **`__init__.py`**: Marks the directory as a Python package.

## Workflow (`process_conversation` in `conversation.py`)

1. **Input Validation and Wrapping**:
   * Accepts raw conversation data, either as a list of messages or a dictionary with a "messages" key.
   * Validates the format and raises errors for invalid input.

2. **Message Filtering**:
   * Filters messages to include only those with allowed roles or system messages if configured.
   * Extracts only the "role" and "content" fields from each message.

3. **History Truncation**:
   * Limits the conversation history to the most recent messages based on the configured maximum history length.

4. **Output Formatting**:
   * Returns the filtered and truncated conversation in a standardized dictionary format with a "messages" key.

5. **Error Handling**:
   * Logs and raises errors encountered during processing.

## Conversation Setup Role and Design

The conversation setup modules are designed to:

* Ensure consistent and clean conversation data is provided to the IRIS agents.
* Support multiple input formats for flexibility.
* Filter and limit conversation history to maintain relevance and performance.
* Provide clear error reporting and logging for troubleshooting.

## Dependencies

* `logging` and `typing` modules for internal logic and type annotations.
* Configuration constants imported from `conversation_settings.py`.

## Error Handling

* Raises `ValueError` for invalid conversation formats.
* Logs warnings for messages missing required fields.
* Logs and raises errors for unexpected exceptions during processing.

---

Refer to the main project README and other module READMEs for details on how conversation setup integrates with the IRIS system.
