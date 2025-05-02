# LLM Connectors (`iris/src/llm_connectors/`)

This directory contains connectors that interface with large language model (LLM) APIs, primarily the OpenAI API. These connectors abstract the details of API calls, handling streaming, non-streaming, and tool calls, and provide a unified interface for the rest of the IRIS system.

## Key Components

* **`rbc_openai.py`**: Implements the main OpenAI connector. It supports all types of calls including streaming, non-streaming, and tool calls. It handles authentication for both RBC and local environments, manages retries, logs usage and costs, and wraps streaming responses to yield usage statistics at the end.
* **`rbc_openai_settings.py`**: Contains configuration settings specific to the OpenAI connector, such as API base URLs, retry parameters, timeouts, and token preview lengths.
* **`__init__.py`**: Marks the directory as a Python package.

## Workflow (`call_llm` in `rbc_openai.py`)

1. **API Call Preparation**:
   * Accepts authentication tokens (OAuth or API key), model parameters, messages, and other OpenAI API parameters.
   * Determines call type: streaming, non-streaming, or embedding.
   * Configures API client with appropriate base URL and authentication.

2. **API Call Execution**:
   * Attempts the API call with retries on failure.
   * Logs key parameters and call attempts.
   * For streaming calls, returns an iterator that yields content chunks and finally usage details.
   * For non-streaming calls, returns the response object and usage details.

3. **Streaming Response Handling**:
   * Wraps the OpenAI streaming iterator to yield content chunks.
   * After stream completion, yields a final dictionary containing usage statistics including token counts, cost, and response time.

4. **Error Handling**:
   * Retries failed calls up to a configured maximum.
   * Logs warnings and errors with detailed information.
   * Raises `OpenAIConnectorError` if all retries fail.

## LLM Connector Role and Design

The LLM Connector is designed to:

* Provide a unified interface for making calls to the OpenAI API.
* Support various call types including chat completions, embeddings, and tool calls.
* Handle authentication seamlessly for different environments.
* Manage retries and error handling robustly.
* Log usage statistics and costs for monitoring and analysis.
* Support streaming responses with progressive content delivery and final usage reporting.

## Dependencies

* `openai` Python SDK for API interaction.
* `logging` and `time` modules for logging and timing.
* Configuration constants from `chat_model.model_settings`.

## Error Handling

The connector raises `OpenAIConnectorError` for unrecoverable API call failures after all retry attempts. It logs detailed information about each attempt and failure for troubleshooting.

---

Refer to the main project README and other module READMEs for details on how the LLM Connector integrates with the IRIS system.
