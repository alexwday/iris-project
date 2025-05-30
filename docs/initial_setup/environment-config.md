# Environment Configuration (`iris/src/initial_setup/env_config.py`)

The environment configuration module provides centralized management of environment variables for the IRIS project. It handles configuration loading, type conversions, validation, and provides a singleton configuration object with all RBC-specific settings.

## Overview

This module serves as the central configuration hub for the entire IRIS application. It loads all settings from environment variables with the `IRIS_` prefix, applies appropriate type conversions, and provides validation methods to ensure required configuration is present. The module is specifically designed for RBC deployment environments with secure SSL and OAuth authentication requirements.

## Key Components

* **`Config`**: Centralized configuration class that loads all settings from environment variables as class attributes
* **`config`**: Singleton instance providing application-wide access to configuration values

## Core Functions/Classes

### `Config` Class

#### Purpose
Centralized configuration class that loads all environment-based settings and provides validation and utility methods for configuration management.

#### Key Attributes
* All configuration values loaded as class attributes from environment variables
* RBC-specific constants (USE_SSL=True, USE_OAUTH=True, IS_RBC_ENV=True)
* Organized by functional categories: database, OAuth, SSL, models, logging, etc.

### `validate()`

#### Purpose
Validates that all required configuration values are set and provides detailed error reporting for missing variables.

#### Parameters
None (class method)

#### Returns
* **bool**: True if all required values are set, False otherwise

#### Workflow
1. **Required Field Check**: Validates presence of DB_HOST, DB_USER, DB_PASSWORD, OAUTH_URL, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
2. **Missing Field Detection**: Identifies and collects missing environment variables
3. **Error Reporting**: Logs missing variables with proper IRIS_ prefix format
4. **Validation Result**: Returns boolean result with appropriate logging

#### Error Handling
* **Missing Variables**: Logs detailed error messages for missing required environment variables

### `get_db_params()`

#### Purpose
Returns database connection parameters formatted as a dictionary for use with database connectors.

#### Parameters
None (class method)

#### Returns
* **dict**: Database connection parameters with keys: host, port, dbname, user, password

#### Workflow
1. **Parameter Collection**: Gathers all database-related configuration values
2. **Dictionary Formation**: Formats parameters in psycopg2-compatible structure
3. **Parameter Return**: Returns complete connection parameter dictionary

### `get_ssl_cert_path(settings_dir)`

#### Purpose
Constructs the full path to SSL certificate file by combining settings directory with certificate filename.

#### Parameters
* **`settings_dir`** (str): Directory where SSL certificate is located

#### Returns
* **str**: Full absolute path to SSL certificate file

#### Workflow
1. **Path Construction**: Combines settings directory with SSL_CERT_FILENAME
2. **Path Resolution**: Returns absolute path for certificate location

### `get_model_config(capability)`

#### Purpose
Returns model configuration including name and pricing for specified capability level.

#### Parameters
* **`capability`** (str): Model capability level ('small', 'large', or 'embedding')

#### Returns
* **dict**: Model configuration with name, prompt_token_cost, and completion_token_cost

#### Workflow
1. **Capability Validation**: Checks if requested capability is supported
2. **Configuration Selection**: Selects appropriate model configuration based on capability
3. **Cost Integration**: Includes pricing information for token usage calculations
4. **Configuration Return**: Returns complete model configuration dictionary

#### Error Handling
* **ValueError**: Raised for unknown model capabilities with helpful error message

## Configuration

Environment variables with `IRIS_` prefix organized by category:

### Core Environment Settings
* **`IRIS_RBC_BASE_URL`**: RBC API base URL (default: RBC performance gateway)
* **`IRIS_LOG_LEVEL`**: Application logging level (default: "DEBUG")

### Database Configuration
* **`IRIS_DB_HOST`**: PostgreSQL server hostname (required)
* **`IRIS_DB_PORT`**: PostgreSQL server port (default: "5432")
* **`IRIS_DB_NAME`**: Database name (default: "maven-finance")
* **`IRIS_DB_USER`**: Database username (required)
* **`IRIS_DB_PASSWORD`**: Database password (required)

### OAuth Configuration
* **`IRIS_OAUTH_URL`**: OAuth token endpoint (required)
* **`IRIS_OAUTH_CLIENT_ID`**: OAuth client identifier (required)
* **`IRIS_OAUTH_CLIENT_SECRET`**: OAuth client secret (required)

### Model Configuration
* **`IRIS_MODEL_SMALL`**: Small model name (default: "gpt-4o-mini-2024-07-18")
* **`IRIS_MODEL_LARGE`**: Large model name (default: "gpt-4o-2024-05-13")
* **`IRIS_MODEL_EMBEDDING`**: Embedding model name (default: "text-embedding-3-large")

## Usage Examples

### Basic Configuration Access
```python
from iris.src.initial_setup.env_config import config

# Access configuration values
api_url = config.RBC_BASE_URL
db_host = config.DB_HOST
log_level = config.LOG_LEVEL
```

### Configuration Validation
```python
if config.validate():
    print("Configuration is valid")
    db_params = config.get_db_params()
else:
    print("Missing required configuration")
```

### Model Configuration
```python
small_model = config.get_model_config("small")
print(f"Using model: {small_model['name']}")
print(f"Prompt cost: ${small_model['prompt_token_cost']}")
```

## Integration Points

How this module integrates with other IRIS components:

* **Database Configuration**: Provides connection parameters for all database operations
* **OAuth Setup**: Supplies authentication credentials for RBC API access
* **Model Orchestration**: Provides model names and pricing for LLM operations
* **Logging Configuration**: Sets log levels and formatting preferences
* **SSL Setup**: Provides certificate paths and expiration settings

## Dependencies

* **`os`**: Environment variable access and path operations
* **`logging`**: Configuration status logging and error reporting
* **`typing`**: Type hints for method signatures and return values
* **`python-dotenv`**: Optional .env file support for development environments

## Error Handling

Comprehensive error handling approach:

* **Missing Variables**: Detailed logging of missing required environment variables with IRIS_ prefix
* **Type Conversion**: Automatic handling of string-to-boolean, string-to-int, and string-to-float conversions
* **Graceful Degradation**: Optional dotenv support that doesn't fail if package unavailable
* **Validation Feedback**: Clear success/failure messaging for configuration validation

## Security Considerations

* **Credential Protection**: Sensitive values like passwords and secrets not logged in debug output
* **Environment Isolation**: All configuration through environment variables prevents hardcoded secrets
* **RBC Security Standards**: Enforced SSL usage and OAuth authentication for enterprise security
* **Certificate Management**: Configurable SSL certificate validation and expiration monitoring

## Performance Notes

* **Singleton Pattern**: Single configuration instance prevents repeated environment variable loading
* **Class Attributes**: Fast attribute access using class-level storage
* **Type Caching**: Type conversions performed once at startup
* **Lazy Loading**: Configuration values loaded only when class is instantiated

---

[Related Documentation: Database Configuration (`db_config.py`), OAuth Setup (`oauth_setup.py`), SSL Setup (`ssl_setup.py`)]