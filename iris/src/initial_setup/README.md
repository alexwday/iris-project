# Initial Setup (`iris/src/initial_setup/`)

This directory contains modules responsible for the initial configuration and setup of the IRIS system environment. It includes database connection management, centralized logging configuration, process monitoring, and security-related setup such as OAuth and SSL.

## Key Components

* **`db_config.py`**: Manages database connection parameters for local and RBC environments. Provides functions to obtain connection parameters, establish connections to the PostgreSQL database, and check for required tables.
* **`logging_config.py`**: Provides centralized logging configuration to ensure consistent log formatting and prevent duplicate log messages across the application. It sets up the root logger with appropriate handlers and formatting.
* **`process_monitor.py`**: Implements a structured process monitoring system that tracks execution stages, timing, token usage, and stage-specific details. It supports logging to a database for debugging and analysis.
* **`oauth/`**: Contains modules related to OAuth authentication setup and management.
* **`ssl/`**: Contains modules for SSL certificate setup and configuration.
* **`__init__.py`**: Marks the directory as a Python package.

## Workflow

1. **Database Configuration and Connection**:
   * `db_config.py` provides environment-specific database parameters and connection functions used throughout the system.

2. **Logging Setup**:
   * `logging_config.py` is used to initialize and configure logging at application startup for consistent and centralized logging behavior.

3. **Process Monitoring**:
   * `process_monitor.py` tracks the lifecycle of application stages, recording timing, token usage, and other details. It supports enabling/disabling monitoring and logging collected data to the database.

4. **Security Setup**:
   * OAuth and SSL submodules handle authentication and secure communication setup.

## Initial Setup Role and Design

The initial setup modules are designed to:

* Provide foundational configuration for database access and logging.
* Enable detailed monitoring of application execution for performance and debugging.
* Manage security aspects such as OAuth tokens and SSL certificates.
* Ensure consistent and reliable environment setup across local and RBC deployments.

## Dependencies

* `psycopg2` for PostgreSQL database connectivity.
* `logging` and `sys` for logging configuration.
* `uuid`, `datetime`, and `time` for process monitoring and timing.
* Standard Python modules for configuration and utility functions.

## Error Handling

* Modules include error handling and logging to capture and report issues during setup, connection, and monitoring processes.

---

Refer to the main project README and other module READMEs for details on how initial setup integrates with the IRIS system.
