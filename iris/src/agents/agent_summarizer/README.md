# Agent Summarizer (`iris/src/agents/agent_summarizer/`)

This directory contains the Summarizer Agent, which is responsible for generating the final research summary based on aggregated detailed research findings from various databases. It synthesizes information into a coherent, comprehensive response for the user.

## Key Components

* **`summarizer.py`**: Implements the core logic of the Summarizer Agent. The main function `generate_streaming_summary` asynchronously generates a streaming summary based on aggregated detailed research. It yields content chunks progressively and finally yields usage details. It handles different scopes, primarily focusing on 'research', and manages errors with detailed logging.
* **`summarizer_settings.py`**: Defines configuration settings for the Summarizer Agent, including model capabilities, prompt engineering using the CO-STAR framework (Context, Objective, Style, Tone, Audience, Response), system prompts, temperature, token limits, available databases, and tool definitions. It guides the LLM to produce clear, professional, and accurate summaries.

## Workflow (`generate_streaming_summary` in `summarizer.py`)

1. **Input Processing**:
   * Receives aggregated detailed research findings from multiple databases, the scope of the request, an authentication token, and optionally the original query plan.
   * Prepares system and context messages using the detailed system prompt defined in `summarizer_settings.py`.

2. **LLM Invocation**:
   * Calls the LLM with the prepared messages, model configuration, and streaming enabled.
   * Streams the summary content chunks as they are generated.

3. **Streaming Response Handling**:
   * Yields content chunks (strings) progressively to the caller.
   * Detects and yields the final usage details dictionary once the stream ends.

4. **Scope Handling**:
   * Primarily handles 'research' scope by generating detailed summaries.
   * Provides simplified handling for 'metadata' scope (no active summary generation).
   * Raises errors for invalid scopes.

5. **Error Handling**:
   * Logs errors with detailed traceback.
   * Raises `SummarizerError` for any issues during summary generation.

## Summarizer Agent Role and Design

The Summarizer Agent is designed to:

* Synthesize detailed research findings from multiple sources into a single coherent summary.
* Provide clear, concise, and comprehensive responses tailored to the user's research scope.
* Stream responses progressively for efficient delivery.
* Handle different scopes appropriately, focusing on content-rich research summaries.
* Maintain a professional and helpful tone suitable for accounting and financial contexts.
* Manage errors gracefully with informative logging.
* Interact with the LLM via the OpenAI connector using streaming calls for progressive summary generation.

## Dependencies

* `logging`, `json`, and typing modules for internal logic.
* `get_model_config` from `chat_model.model_settings` for model configuration.
* `call_llm` from `llm_connectors.rbc_openai` for LLM interaction.
* Global prompt components from `global_prompts` for constructing the system prompt.

## Error Handling

The agent raises `SummarizerError` for any issues during summary generation, including streaming errors or invalid LLM responses. Errors are logged with full traceback for debugging.

---

Refer to the main project README and other agent READMEs for details on how the Summarizer Agent fits into the overall IRIS system pipeline.
