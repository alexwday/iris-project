# Initial Setup (`iris/src/initial_setup/`)

This directory contains modules responsible for configuring and initializing various aspects of the IRIS application environment when it starts up.

## Purpose

The modules here ensure that necessary configurations are loaded, connections are established, and services like logging are ready before the main application logic begins processing queries.

## Key Components

*   **`db_config.py`**: Handles the configuration and potentially the establishment of the connection to the primary PostgreSQL database (`maven-finance`). It likely reads connection details (host, port, user, password, database name) from environment variables or a configuration file.
*   **`logging_config.py`**: Configures the application's logging framework (e.g., Python's built-in `logging`). This includes setting log levels, defining log formats, and specifying output handlers (e.g., console, file).
*   **`process_monitor.py`**: Appears to be related to monitoring application processes or perhaps specific long-running tasks within IRIS. It might involve logging process status, performance metrics, or handling process lifecycle events.
*   **`oauth/`**: Contains modules (`oauth.py`, `oauth_settings.py`) for handling OAuth authentication, likely used for securing connections to certain APIs or internal services that require OAuth tokens.
*   **`ssl/`**: Contains modules (`ssl.py`, `ssl_settings.py`) for managing SSL/TLS configurations, potentially used for securing database connections or external API calls.
*   **`__init__.py`**: Marks the directory as a Python package.

## Initialization Flow

Scripts or modules within this directory are typically executed early in the application's startup sequence to ensure the environment is properly configured before any agent or core logic is invoked.
