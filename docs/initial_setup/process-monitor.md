# Process Monitor (`iris/src/initial_setup/process_monitor_setup.py`)

The process monitor module provides comprehensive execution tracking and performance monitoring for the IRIS application. It captures timing metrics, LLM call details, token usage, and stage-specific information with robust database logging capabilities for operational analysis and debugging.

## Overview

This module serves as the operational monitoring foundation for the IRIS system, providing detailed tracking of execution stages, performance metrics, and LLM usage across the entire application workflow. It includes comprehensive database logging capabilities for audit trails, performance analysis, and debugging support with timezone-aware timestamps and structured data collection.

## Key Components

* **`ProcessStage`**: Individual stage tracking with timing, LLM calls, and metadata
* **`ProcessMonitor`**: Main monitoring coordinator with database integration
* **Global functions**: Singleton management and monitoring control

## Core Functions/Classes

### `ProcessStage` Class

#### Purpose
Represents a single execution stage with comprehensive timing, LLM usage tracking, and metadata collection capabilities.

#### Key Attributes
* **`name`**: Stage identifier string
* **`start_time`**: Timezone-aware UTC datetime for stage start
* **`end_time`**: Timezone-aware UTC datetime for stage completion
* **`duration`**: Calculated duration in seconds
* **`status`**: Stage status ("not_started", "in_progress", "completed", "error")
* **`llm_calls_data`**: List of detailed LLM call information
* **`details`**: Dictionary for stage-specific metadata

#### Core Methods

**`start()`**: Initiates stage timing with UTC timestamp and status update
**`end(status)`**: Finalizes stage with end timestamp, duration calculation, and status
**`add_llm_call_details(call_details)`**: Records individual LLM call metrics
**`add_details(**kwargs)`**: Updates stage-specific metadata dictionary
**`to_dict()`**: Serializes stage data for database storage or reporting

### `ProcessMonitor` Class

#### Purpose
Manages overall process monitoring with stage coordination, database logging, and comprehensive reporting capabilities.

#### Key Attributes
* **`enabled`**: Monitoring activation state
* **`stages`**: Dictionary of ProcessStage objects indexed by name
* **`run_uuid`**: Unique identifier for process run correlation
* **`start_time`** / **`end_time`**: Overall monitoring time boundaries

#### Core Methods

**`set_run_uuid(run_uuid)`**: Sets unique identifier for database correlation
**`start_monitoring()`** / **`end_monitoring()`**: Controls overall monitoring lifecycle
**`start_stage(stage_name)`** / **`end_stage(stage_name, status)`**: Stage lifecycle management
**`add_llm_call_details_to_stage(stage_name, call_details)`**: LLM usage tracking per stage
**`add_stage_details(stage_name, **kwargs)`**: Stage metadata management

### `log_to_database(cursor)`

#### Purpose
Comprehensive database logging of all collected monitoring data with structured schema and error handling.

#### Parameters
* **`cursor`**: psycopg2 database cursor within active transaction

#### Returns
None (logs data to database)

#### Workflow
1. **Validation**: Checks monitoring enabled, run_uuid set, stages exist
2. **Data Preparation**: Converts durations to milliseconds, serializes LLM data as JSON
3. **Totals Calculation**: Aggregates token usage and costs from LLM call details
4. **Decision Extraction**: Uses helper function to extract key decision information
5. **Database Insertion**: Structured insertion with comprehensive error handling
6. **Transaction Management**: Proper error propagation for transaction control

#### Error Handling
* **Individual Record Errors**: Logged but don't stop processing
* **Database Errors**: Logged and re-raised for transaction management
* **Detailed Debugging**: Comprehensive logging for failed insertions

### `_extract_decision_details(stage_name, details)`

#### Purpose
Extracts key decision information from stage details based on stage type for concise database logging.

#### Parameters
* **`stage_name`** (str): Stage identifier for extraction logic selection
* **`details`** (Dict[str, Any]): Stage details dictionary

#### Returns
* **Optional[str]**: Extracted decision summary or None

#### Stage-Specific Extraction
* **Router**: Function name from routing decisions
* **Planner**: Selected databases list
* **Clarifier**: Action and truncated output
* **Summary**: Scope, result count, source count
* **Database Queries**: Document IDs with format handling
* **SSL/OAuth Setup**: Configuration details without sensitive data

## Configuration

Settings used from `env_config`:

* **`PROCESS_MONITOR_MODEL_NAME`**: Model name for database logging (default: "iris")

## Usage Examples

### Basic Process Monitoring
```python
from iris.src.initial_setup.process_monitor_setup import enable_monitoring, get_process_monitor
import uuid

enable_monitoring(True)
process_monitor = get_process_monitor()

run_uuid = uuid.uuid4()
process_monitor.set_run_uuid(run_uuid)
process_monitor.start_monitoring()
```

### Stage Tracking with LLM Details
```python
process_monitor.start_stage("router")
process_monitor.add_stage_details("router", function_name="research_from_database")

llm_details = {
    "model": "gpt-4o-mini",
    "prompt_tokens": 150,
    "completion_tokens": 50,
    "cost": 0.001234
}
process_monitor.add_llm_call_details_to_stage("router", llm_details)
process_monitor.end_stage("router")
```

### Database Logging
```python
from iris.src.initial_setup.db_config import connect_to_db

conn = connect_to_db()
if conn:
    try:
        with conn.cursor() as cursor:
            process_monitor.log_to_database(cursor)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

## Integration Points

How this module integrates with other IRIS components:

* **Model Orchestration**: Main workflow monitoring and performance tracking
* **Agent Pipeline**: Stage timing and LLM usage collection across all agents
* **Database Operations**: Individual query monitoring with worker thread tracking
* **Error Handling**: Comprehensive error status and detail capture
* **Performance Analysis**: Cost tracking, timing analysis, and optimization insights

## Dependencies

* **`uuid`**: Unique run identification and correlation
* **`datetime`**: Timezone-aware timestamp handling and duration calculations
* **`psycopg2`**: PostgreSQL database logging with JSON support
* **`logging`**: Detailed operational logging and debugging
* **`json`**: LLM call data serialization for database storage
* **Internal modules**: `env_config` for configuration settings

## Error Handling

Comprehensive error handling approach:

* **Stage Validation**: Ensures stages exist before operations
* **Data Preparation**: Safe handling of missing or invalid data
* **Database Resilience**: Individual record error isolation with continued processing
* **Transaction Safety**: Proper exception propagation for transaction management
* **Debugging Support**: Detailed logging for troubleshooting failed operations

## Security Considerations

* **Sensitive Data Protection**: Decision details extraction avoids logging actual tokens or credentials
* **UUID Correlation**: Secure unique identifiers for process correlation
* **Database Security**: Uses parameterized queries to prevent injection attacks
* **Error Information**: Careful error logging to avoid sensitive data exposure

## Performance Notes

* **Minimal Overhead**: Monitoring designed for minimal impact on application performance
* **Efficient Storage**: JSON serialization for complex data with database optimization
* **Memory Management**: Stage data cleanup and proper resource management
* **Database Efficiency**: Batch operations and transaction management for optimal performance

---

[Related Documentation: Database Configuration (`db_config.py`), Environment Configuration (`env_config.py`)]