# Agent Planner (`iris/src/agents/agent_planner/`)

The Planner Agent creates strategic database research query plans based on research statements from the Clarifier Agent. It determines which databases to query, optimizing the research process through intelligent database selection.

## Overview

The Planner Agent serves as the strategic decision-maker for database selection in the IRIS research workflow. It analyzes research statements to identify key accounting concepts, standards, and information needs, then selects 1-5 most relevant databases from the available options. The agent employs a sophisticated hierarchical selection framework that prioritizes user-requested databases, recognizes accounting query flags, and scales database count based on query complexity while respecting user preferences for external source inclusion.

## Key Components

* **`planner.py`**: Implements strategic database selection with the main function `create_database_selection_plan`. Validates all selections against available databases and handles continuation scenarios. Returns tuple with selection plan and usage details.
* **`planner_settings.py`**: Defines comprehensive CO-STAR framework configuration with sophisticated database selection logic. Uses 'small' model capability for efficiency. Integrates all global prompt components and provides detailed selection criteria.

## Core Functions/Classes

### `create_database_selection_plan(research_statement, token, is_continuation=False)`

#### Purpose
Creates a strategic plan of databases to query based on the research statement from the Clarifier Agent, optimizing for relevance and efficiency while respecting user preferences.

#### Parameters
* **`research_statement`** (str): The research statement from the Clarifier Agent containing the research needs
* **`token`** (str): Authentication token for API access (OAuth token in RBC environment, API key in local environment)
* **`is_continuation`** (bool, optional): Whether this is a continuation of previous research (default: False)

#### Returns
* **Tuple[Dict[str, Any], Optional[Dict[str, Any]]]**: 
  - First element: Database selection plan dictionary with 'databases' key containing list of selected database names
  - Second element: Usage details dictionary with token usage, cost, and timing information (or None on error)

#### Workflow
1. **System Prompt Preparation**: Constructs system message using CO-STAR framework prompt
2. **Continuation Handling**: Adds "[CONTINUATION REQUEST]" prefix to research statement if applicable
3. **LLM Tool Call**: Invokes LLM with forced tool choice for `submit_database_selection_plan` function
4. **Response Validation**: Validates tool call presence and extracts selected databases
5. **Database Validation**: Ensures each selected database exists in AVAILABLE_DATABASES dictionary
6. **Plan Compilation**: Returns validated list of 1-5 database names

#### Error Handling
* **PlannerError**: Raised for invalid responses, missing tool calls, or unknown databases
* **JSON validation**: Handles malformed tool call arguments
* **Database validation**: Ensures all selected databases are strings and exist in available list
* **Empty selection handling**: Raises error if no databases selected

### `PlannerError` (Exception Class)

#### Purpose
Custom exception class for planner-specific errors, providing clear error context for database selection failures.

## Configuration

Settings used from `planner_settings.py`:

* **`MODEL_CAPABILITY`**: "small" - Uses efficient model for strategic database selection
* **`MAX_TOKENS`**: 4096 - Maximum tokens for comprehensive analysis
* **`TEMPERATURE`**: 0.0 - Ensures deterministic, consistent database selections
* **`AVAILABLE_DATABASES`**: Dictionary of available databases imported from global prompts
* **`TOOL_DEFINITIONS`**: Defines `submit_database_selection_plan` tool with 1-5 database array

## Usage Examples

### Basic Usage
```python
from iris.src.agents.agent_planner.planner import create_database_selection_plan

# Research statement from Clarifier
research_statement = "Accounting Query: Research focusing on IFRS 15 regarding revenue recognition for software contracts"

# Create database selection plan
plan, usage = create_database_selection_plan(research_statement, auth_token)
# Returns: ({"databases": ["internal_capm", "internal_wiki", "external_iasb"]}, usage_details)
```

### Advanced Usage
```python
# Continuation research with explicit database request
research_statement = "User requested search in wiki for lease accounting under IFRS 16"

# Planner respects explicit database request
plan, usage = create_database_selection_plan(
    research_statement, 
    auth_token, 
    is_continuation=True
)
# Returns: ({"databases": ["internal_wiki"]}, usage_details)

# Complex accounting query with external preference
research_statement = "Accounting Query: Research on hedge accounting requirements..."
# (Assumes include_external flag was True based on user confirmation)

plan, usage = create_database_selection_plan(research_statement, auth_token)
# Returns: ({"databases": ["internal_capm", "internal_memos", "external_ey", "external_pwc"]}, usage_details)
```

## Integration Points

How the Planner Agent integrates with other IRIS components:

* **Clarifier Agent**: Receives research statements that guide database selection
* **Database Subagents**: Selected databases are queried by respective subagents
* **Chat Model**: Manages the flow from Clarifier to Planner to database execution
* **Global Prompts**: Uses database information and all context components for informed selection

## Dependencies

* **`json`**: JSON parsing for tool call arguments
* **`logging`**: Comprehensive operation logging and error tracking
* **`typing`**: Type hints for function signatures and return values
* **Internal modules**: 
  - `env_config`: Model configuration and capability settings
  - `rbc_openai`: LLM connector for OpenAI API calls
  - `global_prompts`: All four global prompt components including database information
  - `planner_settings`: CO-STAR framework configuration, database lists, and tool definitions

## Error Handling

Comprehensive error handling approach:

* **Invalid LLM responses**: Raises PlannerError with detailed context about missing or malformed responses
* **Tool call validation**: Ensures correct function name (`submit_database_selection_plan`) and valid parameters
* **Database validation**: Each selected database validated against AVAILABLE_DATABASES dictionary
* **Type validation**: Ensures all database entries are strings
* **Selection count**: Enforces 1-5 database selection limit through tool definition
* **Logging**: All errors logged with full stack traces using exc_info=True

## Security Considerations

* **Token handling**: Authentication tokens passed through without storage or logging
* **Database access control**: Respects user-specific database availability from AVAILABLE_DATABASES
* **Input validation**: Validates research statement format and continuation flags
* **No direct database access**: Only returns database names, not actual query execution

## Performance Notes

* **Model efficiency**: Uses small model capability for fast database selection decisions
* **Deterministic selection**: Temperature=0.0 ensures consistent selections for identical research statements
* **Scalable selection**: Dynamically adjusts 1-5 databases based on query complexity
* **Validation efficiency**: Database validation against pre-loaded AVAILABLE_DATABASES dictionary
* **Non-streaming response**: Immediate plan return without streaming overhead

---

Refer to the [agents-overview.md](./agents-overview.md) for details on how the Planner Agent fits into the overall IRIS system pipeline.