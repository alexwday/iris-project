# Global Prompts (`iris/src/global_prompts/`)

This directory stores prompt templates or statements that are shared and potentially used by multiple agents across the IRIS system. Centralizing these prompts helps maintain consistency and makes them easier to update.

## Purpose

Global prompts often contain foundational information, instructions, or context that is relevant to various stages of the query processing pipeline. Examples include:

*   **System Persona/Role:** Defining how the AI should behave or respond.
*   **Core Instructions:** General guidelines applicable to multiple agents.
*   **Contextual Data:** Information like the current date, fiscal calendar details (`fiscal_calendar.py`), project scope (`project_statement.py`), general database information (`database_statement.py`), or operational constraints (`restrictions_statement.py`) that agents might need to consider.

## Usage

Agents or the main orchestration logic (`chat_model/model.py`) can import and utilize these prompts as needed, often incorporating them into the more specific prompts used for individual agent tasks.

## Files

*   **`database_statement.py`**: Provides general information about the available databases.
*   **`fiscal_calendar.py`**: Contains details about the relevant fiscal calendar.
*   **`project_statement.py`**: Defines the overall scope or purpose of the IRIS project.
*   **`restrictions_statement.py`**: Outlines any known limitations or restrictions for the system's operation or responses.
*   **`__init__.py`**: Marks the directory as a Python package.
