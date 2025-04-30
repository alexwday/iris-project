# Conversation Setup (`iris/src/conversation_setup/`)

This directory handles the management of the conversation context and history for interactions with the IRIS system. Maintaining the conversation state is crucial for agents like the `agent_direct_response` and for providing context to the LLM throughout the interaction.

## Key Components

*   **`conversation.py`**: This module likely contains the classes or functions responsible for storing, retrieving, and managing the sequence of user queries and system responses. It might handle aspects like conversation length limits, formatting the history for LLM input, and potentially summarizing older parts of the conversation.
*   **`conversation_settings.py`**: Holds configuration parameters related to conversation management, such as maximum history length, specific formatting rules, or settings for summarization if implemented.

## Role in the System

The conversation setup module provides the necessary context for the agents to understand the ongoing dialogue. This allows the system to:
*   Answer follow-up questions.
*   Refer to previous parts of the conversation.
*   Maintain user context across multiple turns.
*   Provide relevant history to the `agent_direct_response` and other agents as needed.
