# LLM Connectors (`iris/src/llm_connectors/`)

This directory contains modules responsible for establishing connections and interacting with the underlying Large Language Models (LLMs) used by the IRIS agents.

## Purpose

The connectors abstract the specific details of interacting with different LLM APIs or services. This allows agents to request text generation or analysis without needing to know the intricacies of a particular LLM provider's interface.

## Key Components

*   **`rbc_openai.py`**: This module specifically handles the connection and interaction logic for an OpenAI model, potentially accessed through an RBC-specific endpoint or configuration (as suggested by the name). It likely wraps the OpenAI API client, manages authentication (API keys), handles request formatting, and processes responses.
*   **`rbc_openai_settings.py`**: Contains configuration settings specific to the RBC OpenAI connector, such as API endpoints, model names (e.g., `gpt-4`, `gpt-3.5-turbo`), API keys or authentication details (though keys should ideally be stored securely, e.g., in environment variables), and potentially parameters like temperature or max tokens.
*   **`__init__.py`**: Marks the directory as a Python package.

## Usage

Agents that require LLM capabilities (e.g., `agent_clarifier`, `agent_planner`, `agent_summarizer`, `database_subagents` for synthesis) will import and use the functions or classes provided by `rbc_openai.py` to send prompts and receive generated text.
