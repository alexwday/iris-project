# Database Subagents (`iris/src/agents/database_subagents/`)

The database subagents system provides specialized agents responsible for querying specific internal and external data sources in the IRIS system. The `database_router.py` module orchestrates concurrent execution of these subagents based on plans from the `agent_planner`.

## Overview

The database subagents architecture enables modular data source integration through specialized agents. Each subagent is tailored to a specific database or data source, understanding its schema, query patterns, and API interactions. The central router manages subagent execution, collecting and aggregating results for the `agent_summarizer`.

## Key Components

* **`database_router.py`**: Central routing module that manages subagent execution, handles query distribution, and collects aggregated results
* **External Subagents**: Connect to third-party databases and APIs (`external_ey`, `external_iasb`, `external_kpmg`, `external_pwc`)
* **Internal Subagents**: Connect to internal RBC databases and knowledge stores (13 total including `internal_capm`, `internal_wiki`, `internal_compliance`, etc.)

## Core Functions/Classes

### `route_query_sync(database, query, scope, token, process_monitor, query_stage_name)`

#### Purpose
Synchronously routes database queries to appropriate subagent modules with comprehensive error handling and process monitoring.

#### Parameters
* **`database`** (str): Database identifier from available databases configuration
* **`query`** (str): Search query to execute against the data source
* **`scope`** (str): Query scope - either 'metadata' or 'research'
* **`token`** (str, optional): Authentication token for API access
* **`process_monitor`** (optional): Process monitor instance for tracking execution and token usage
* **`query_stage_name`** (str, optional): Specific stage name for query tracking

#### Returns
* **SubagentResult**: Tuple containing query results, optional document IDs, and optional file links

#### Workflow
1. **Validation**: Checks database exists in available databases configuration
2. **Module Import**: Dynamically imports appropriate subagent module
3. **Function Inspection**: Verifies subagent has required `query_database_sync` function
4. **Parameter Mapping**: Maps process monitor and stage name parameters if supported
5. **Query Execution**: Executes subagent query with appropriate parameters
6. **Result Processing**: Handles backward compatibility for 2-element vs 3-element result tuples
7. **Monitor Updates**: Updates process monitor with document IDs, file links, and status

#### Error Handling
* **ValueError**: When database is not recognized in available databases
* **AttributeError**: When subagent module lacks required `query_database_sync` function
* **ImportError**: When subagent module cannot be loaded
* **Exception**: General exception handling for execution errors

## Configuration

Settings used from global configuration:

* **`AVAILABLE_DATABASES`**: List of available databases from `global_prompts.database_statement`
* **Module path pattern**: `.{database}.subagent` for dynamic import
* **Function signature**: `query_database_sync` required in all subagent modules

## Usage Examples

### Basic Query Routing
```python
from iris.src.agents.database_subagents.database_router import route_query_sync

result, doc_ids, file_links = route_query_sync(
    database="internal_capm",
    query="equity risk premium guidance",
    scope="research",
    token=auth_token
)
```

### With Process Monitoring
```python
result, doc_ids, file_links = route_query_sync(
    database="external_ey",
    query="IFRS updates",
    scope="metadata",
    process_monitor=monitor,
    query_stage_name="ey_query_stage_1"
)
```

## Integration Points

How this module integrates with other IRIS components:

* **Agent Planner**: Receives query plans and database selections for execution
* **Agent Summarizer**: Provides aggregated results from multiple subagents
* **Global Prompts**: Uses database configuration and available databases list
* **Process Monitor**: Tracks execution stages, token usage, and performance metrics
* **LLM Connectors**: Subagents utilize OpenAI connectors for API interactions

## Dependencies

* **`asyncio`**: Asynchronous operation support
* **`importlib`**: Dynamic module import for subagents
* **`inspect`**: Function signature analysis for parameter mapping
* **`logging`**: Comprehensive logging throughout execution
* **`typing`**: Type hints for response types and return values
* **Internal modules**: `env_config`, `database_statement`, individual subagent modules

## Error Handling

Comprehensive error handling approach:

* **Database Validation**: Returns appropriate error responses based on scope type (empty list for metadata, error dict for research)
* **Module Loading**: Handles ImportError and AttributeError with detailed logging
* **Execution Errors**: Catches general exceptions during subagent execution
* **Process Monitor Integration**: Updates monitor with error details and maintains stage tracking
* **Backward Compatibility**: Handles both 2-element and 3-element result tuples from subagents

## Security Considerations

* **Token Management**: Secure handling of authentication tokens passed to subagents
* **Module Import Security**: Controlled dynamic import using package namespace restriction
* **Error Information**: Prevents sensitive information leakage in error messages
* **Access Control**: Database access controlled through available databases configuration

## Performance Notes

* **Concurrent Execution**: Designed for concurrent subagent execution (though current implementation is synchronous)
* **Module Caching**: Imported modules are cached by Python's import system
* **Process Monitoring**: Minimal overhead monitoring with optional parameter support
* **Error Response Caching**: Efficient error response generation for failed queries

---

[Related Documentation: Individual subagent documentation in respective subdirectories]
