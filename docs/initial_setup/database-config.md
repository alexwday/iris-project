# Database Configuration (`iris/src/initial_setup/db_config.py`)

The database configuration module manages PostgreSQL database connectivity for the IRIS system. It handles connection parameters from environment variables, establishes secure database connections, and validates required database schema components.

## Overview

This module provides the foundational database connectivity layer for all IRIS data operations. It abstracts database connection management, handles environment-based configuration, and includes validation functions to ensure the required database schema is in place. All database parameters are securely loaded from environment variables through the configuration system.

## Key Components

* **`db_config.py`**: Contains database connection management, parameter handling, and schema validation functions

## Core Functions/Classes

### `get_db_params()`

#### Purpose
Retrieves database connection parameters from the environment configuration system with proper logging and validation.

#### Parameters
None

#### Returns
* **Dict[str, Any]**: Dictionary containing all required database connection parameters (host, port, dbname, user, password)

#### Workflow
1. **Configuration Access**: Delegates to `config.get_db_params()` from environment configuration
2. **Debug Logging**: Logs parameter retrieval for troubleshooting
3. **Parameter Return**: Returns complete parameter dictionary for connection use

#### Error Handling
* Inherits error handling from underlying environment configuration system

### `connect_to_db()`

#### Purpose
Establishes a secure connection to PostgreSQL database with proper configuration and error handling.

#### Parameters
None

#### Returns
* **Optional[psycopg2.extensions.connection]**: Database connection object or None if connection fails

#### Workflow
1. **Parameter Retrieval**: Gets database parameters using `get_db_params()`
2. **Connection Logging**: Logs connection attempt with non-sensitive parameters (host, port, database, user)
3. **Connection Establishment**: Uses `psycopg2.connect()` with unpacked parameters
4. **Configuration**: Sets `autocommit = False` for explicit transaction control
5. **Success Validation**: Logs successful connection and returns connection object

#### Error Handling
* **Exception**: Catches all connection exceptions, logs with stack trace, returns None for graceful degradation

### `check_tables_exist(conn)`

#### Purpose
Validates that required database tables exist in the public schema for proper system operation.

#### Parameters
* **`conn`** (psycopg2.extensions.connection): Active database connection object

#### Returns
* **List[str]**: List of existing table names from the required tables set

#### Workflow
1. **Schema Query**: Queries `information_schema.tables` for table existence
2. **Schema Filtering**: Checks specifically for tables in 'public' schema
3. **Table Validation**: Validates presence of required tables: 'apg_catalog', 'apg_content'
4. **Result Processing**: Extracts and returns table names using context manager for proper cursor handling

#### Error Handling
* **Database Errors**: Inherits exception handling from connection object
* **Cursor Management**: Uses context manager for automatic cursor cleanup

## Configuration

Settings used from `env_config`:

* **`DB_HOST`**: PostgreSQL server hostname for connection
* **`DB_PORT`**: PostgreSQL server port (typically 5432)
* **`DB_NAME`**: Target database name (default: "maven-finance")
* **`DB_USER`**: Database username for authentication
* **`DB_PASSWORD`**: Database password for secure authentication

## Usage Examples

### Basic Database Connection
```python
from iris.src.initial_setup.db_config import connect_to_db, check_tables_exist

conn = connect_to_db()
if conn:
    try:
        existing_tables = check_tables_exist(conn)
        print(f"Found tables: {existing_tables}")
    finally:
        conn.close()
```

### Connection with Operations
```python
conn = connect_to_db()
if conn:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM apg_catalog")
            count = cur.fetchone()[0]
            print(f"Catalog entries: {count}")
    finally:
        conn.close()
```

## Integration Points

How this module integrates with other IRIS components:

* **Process Monitor**: Uses database connection for logging execution data and performance metrics
* **Database Subagents**: Utilizes connections for querying document catalogs and content
* **Model Orchestration**: Employs database logging for final process tracking
* **Monitoring Systems**: Provides connectivity for operational data storage and retrieval

## Dependencies

* **`psycopg2`**: PostgreSQL adapter for Python with UUID support extensions
* **`psycopg2.extras`**: Extended functionality including UUID type registration
* **`logging`**: Connection status reporting and error logging
* **`typing`**: Type hints for function signatures and return values
* **Internal modules**: `env_config` for environment-based configuration management

## Error Handling

Comprehensive error handling approach:

* **Connection Failures**: Logs detailed error information with stack traces, returns None for graceful degradation
* **Parameter Validation**: Relies on environment configuration validation for parameter correctness
* **Exception Propagation**: Database operation exceptions propagated to calling code for appropriate handling
* **Graceful Degradation**: Connection failures don't crash the system, allowing fallback operations

## Security Considerations

* **Credential Protection**: Database passwords never logged, only non-sensitive parameters shown in logs
* **Connection Security**: Uses PostgreSQL's built-in security features and authentication
* **Parameter Isolation**: Database parameters isolated through environment variable system
* **Transaction Control**: Explicit transaction management prevents unintended commits

## Performance Notes

* **Connection Pooling**: Each call creates new connection - consider connection pooling for high-frequency operations
* **UUID Optimization**: Automatic UUID type registration for efficient UUID handling
* **Transaction Management**: Autocommit disabled for explicit control and better performance
* **Resource Management**: Connections should be properly closed by calling code to prevent resource leaks

---

[Related Documentation: Environment Configuration (`env_config.py`), Process Monitor Setup (`process_monitor_setup.py`)]