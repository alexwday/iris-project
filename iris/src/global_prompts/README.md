# Global Prompts (`iris/src/global_prompts/`)

This directory contains global prompt utilities and statements used across the IRIS system to provide consistent context, instructions, and knowledge source descriptions to the various agents.

## Key Components

* **`project_statement.py`**: Generates a detailed project context statement with XML-style delimiters. This statement provides essential information about the project's purpose, knowledge sources (internal and external), and system goals. It is prefixed to system prompts to ensure agents have a shared understanding of the project scope.
* **`database_statement.py`**: Provides centralized descriptions of all available databases used in the system. It serves as the single source of truth for database information, including names, descriptions, content types, query types, and usage guidance. It formats this information with XML-style delimiters for inclusion in agent prompts.
* **`fiscal_calendar.py`**, **`restrictions_statement.py`**, and other prompt files: Contain additional global statements and instructions relevant to fiscal periods, usage restrictions, and project-specific guidelines.
* **`__init__.py`**: Marks the directory as a Python package.

## Workflow

1. **Project Context Generation**:
   * The `get_project_statement` function in `project_statement.py` generates a comprehensive project context statement that is included in system prompts to provide agents with background on the IRIS system and its knowledge sources.

2. **Database Information Provision**:
   * The `get_database_statement` function in `database_statement.py` returns a formatted statement describing all available internal and external databases, their purposes, and usage strategies. This ensures agents query the appropriate sources effectively.

3. **Additional Global Prompts**:
   * Other prompt files provide standardized instructions and constraints that are incorporated into agent prompts to maintain consistency and compliance.

## Global Prompts Role and Design

The global prompts serve to:

* Provide a unified and consistent context across all agents.
* Centralize knowledge about data sources and project scope.
* Facilitate prompt engineering by structuring instructions and information with XML-style delimiters.
* Ensure agents operate with aligned understanding and guidelines.

## Dependencies

* Standard Python logging for error handling and debugging.
* Modular prompt components imported and combined as needed.

## Error Handling

* Functions include basic error handling and logging to ensure robustness in prompt generation.

---

Refer to the main project README and other module READMEs for details on how global prompts integrate with the IRIS system.
