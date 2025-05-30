# Initial Setup (`iris/src/initial_setup/`)

This directory contains modules responsible for the initial configuration and setup of the IRIS system environment. It includes database connection management, centralized logging configuration, process monitoring, conversation processing, and security-related setup such as OAuth and SSL.

## Overview

The initial setup system provides foundational configuration and environment management for the IRIS system. These modules handle essential setup tasks including database connectivity, logging configuration, process monitoring, conversation processing, and security components like OAuth authentication and SSL certificate management. The setup modules ensure consistent and reliable environment initialization across both local development and RBC production deployments.

## Key Components

* **`conversation_setup.py`**: Processes and filters conversation histories for use with language models
* **`db_config.py`**: Manages database connection parameters for local and RBC environments
* **`env_config.py`**: Centralized configuration management loading settings from environment variables
* **`logging_config.py`**: Provides centralized logging configuration for consistent log formatting
* **`oauth_setup.py`**: Handles OAuth authentication for RBC API access with retry logic
* **`process_monitor_setup.py`**: Implements structured process monitoring system for execution tracking
* **`ssl_setup.py`**: Handles SSL certificate setup for secure API communication
* **`__init__.py`**: Marks the directory as a Python package

## Core Functions/Classes

### Environment Configuration Module (`env_config.py`)

#### Purpose
Provides centralized configuration management that loads settings from environment variables and offers configuration access throughout the application.

#### Key Functions
* `config` object: Global configuration instance with environment-specific settings

### Database Configuration Module (`db_config.py`)

#### Purpose
Manages database connection parameters for local and RBC environments with connection establishment and table verification.

#### Key Functions
* Database connection parameter functions for environment-specific configuration
* Connection establishment functions for PostgreSQL database access
* Table verification functions for required database schema validation

### Conversation Setup Module (`conversation_setup.py`)

#### Purpose
Processes and filters conversation histories for use with language models, standardizing formats and managing history length.

#### Key Functions
* Conversation filtering and role-based message processing functions
* History length management based on configuration settings
* Format standardization for different conversation input types

### Logging Configuration Module (`logging_config.py`)

#### Purpose
Provides centralized logging configuration to ensure consistent log formatting and prevent duplicate messages across the application.

#### Key Functions
* Root logger setup with appropriate handlers and formatting
* Consistent logging behavior initialization functions

### OAuth Setup Module (`oauth_setup.py`)

#### Purpose
Handles OAuth authentication for RBC API access with robust error handling, retry logic, and detailed operational monitoring.

#### Key Functions
* OAuth token acquisition and validation functions
* Retry logic implementation for authentication failures
* Operational logging for authentication monitoring

### Process Monitor Setup Module (`process_monitor_setup.py`)

#### Purpose
Implements structured process monitoring system that tracks execution stages, timing, token usage, and stage-specific details.

#### Key Functions
* Process stage tracking and timing measurement functions
* Database logging functions for debugging and analysis
* Enable/disable monitoring control functions

### SSL Setup Module (`ssl_setup.py`)

#### Purpose
Handles SSL certificate setup required for secure API communication with certificate validation and expiration checking.

#### Key Functions
* SSL certificate configuration functions
* Certificate validation and expiration checking functions
* Environment variable configuration for secure communication

## Configuration

Environment-based configuration managed through `env_config.py`:

* **Environment Variables**: All configuration loaded from environment variables for deployment flexibility
* **Local vs RBC Settings**: Environment-specific configurations for database, OAuth, and SSL settings
* **Default Values**: Sensible defaults provided for optional configuration parameters
* **Centralized Access**: Single configuration object provides access to all settings across the application

## Usage Examples

### Basic Setup Initialization
```python
from iris.src.initial_setup import (
    env_config,
    logging_config,
    db_config
)

# Initialize logging
logging_config.setup_logging()

# Access configuration
config = env_config.config

# Get database connection
connection = db_config.get_connection()
```

### Process Monitoring Usage
```python
from iris.src.initial_setup.process_monitor_setup import ProcessMonitor

monitor = ProcessMonitor()
monitor.start_stage("agent_processing")
# ... perform work ...
monitor.end_stage("agent_processing", {"tokens_used": 150})
```

## Integration Points

This module is used throughout the IRIS system for foundational setup:

* **Application Startup**: Environment configuration and logging initialization
* **Database Access**: Connection management for all database operations
* **Security Setup**: OAuth and SSL configuration for secure API communication
* **Process Monitoring**: Execution tracking and performance monitoring across all agents
* **Conversation Processing**: Message history standardization for LLM interactions

## Dependencies

* **`psycopg2`**: PostgreSQL database connectivity
* **`requests`**: OAuth authentication API calls
* **`cryptography`**: SSL certificate validation (optional)
* **`logging`** and **`sys`**: Logging configuration
* **`uuid`**, **`datetime`**, and **`time`**: Process monitoring and timing
* **Standard Python modules**: Configuration and utility functions

## Error Handling

Comprehensive error handling approach across all setup modules:

* **Robust Connection Handling**: Database connection failures with retry logic and fallback options
* **OAuth Error Management**: Authentication failures with detailed error logging and retry mechanisms
* **SSL Certificate Validation**: Certificate validation with expiration checking and error reporting
* **Configuration Validation**: Environment variable validation with clear error messages for missing settings
* **Process Monitoring Resilience**: Monitoring failures do not impact application functionality

## Security Considerations

* **OAuth Token Management**: Secure handling of authentication tokens with proper masking in logs
* **SSL Certificate Validation**: Proper certificate validation and expiration checking for secure communication
* **Database Security**: Secure connection parameter handling and credential management
* **Environment Variable Protection**: Sensitive configuration data loaded from environment variables only
* **Logging Security**: Sensitive information filtered from log outputs

## Performance Notes

* **Configuration Caching**: Environment configuration loaded once and cached for application lifetime
* **Connection Pooling**: Database connections managed efficiently with proper connection lifecycle
* **Monitoring Overhead**: Process monitoring designed to have minimal impact on application performance
* **Lazy Loading**: Setup modules only initialize when explicitly called to reduce startup overhead
* **Efficient Logging**: Logging configuration optimized to prevent duplicate messages and excessive overhead

---

This initial setup system ensures consistent, secure, and reliable environment initialization for all IRIS system deployments across local development and RBC production environments.
