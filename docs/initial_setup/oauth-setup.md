# OAuth Setup (`iris/src/initial_setup/oauth_setup.py`)

The OAuth setup module handles secure authentication for RBC API access using the OAuth 2.0 client credentials flow. It provides robust error handling, retry logic with timing metrics, and comprehensive security features for enterprise authentication requirements.

## Overview

This module serves as the authentication foundation for all RBC API interactions in the IRIS system. It implements the OAuth 2.0 client credentials grant flow with enterprise-grade reliability features including retry mechanisms, detailed logging, and security-conscious credential handling. The module is designed for server-to-server authentication scenarios typical in enterprise environments.

## Key Components

* **`oauth_setup.py`**: Contains OAuth authentication logic with retry mechanisms and comprehensive error handling

## Core Functions/Classes

### `setup_oauth()`

#### Purpose
Obtains OAuth authentication token for RBC API access using client credentials flow with comprehensive retry logic and operational monitoring.

#### Parameters
None

#### Returns
* **str**: OAuth authentication token for API access

#### Workflow
1. **Configuration Validation**: Validates presence of required OAuth settings (URL, client ID, client secret)
2. **Security Logging**: Logs configuration details with security-conscious masking of sensitive information
3. **Payload Preparation**: Constructs OAuth client credentials grant request with standard OAuth 2.0 format
4. **Retry Loop Execution**: Attempts up to `MAX_RETRY_ATTEMPTS` times with configurable delay between attempts
5. **HTTP Request Processing**: Makes POST request to OAuth endpoint with timeout handling and status validation
6. **Token Extraction**: Parses JSON response to extract and validate access_token presence
7. **Security Preview**: Creates truncated token preview for secure logging without exposure
8. **Timing Tracking**: Measures individual attempt time and total process duration for monitoring

#### Error Handling
* **ValueError**: Raised for missing required settings or invalid token response
* **requests.exceptions.RequestException**: Handles HTTP failures with comprehensive retry logic
* **Exception Preservation**: Maintains reference to last exception for proper error propagation

## Configuration

Settings used from `env_config`:

* **`OAUTH_URL`**: OAuth endpoint URL for token requests (required)
* **`OAUTH_CLIENT_ID`**: OAuth client identifier for authentication (required)
* **`OAUTH_CLIENT_SECRET`**: OAuth client secret for authentication (required)
* **`MAX_RETRY_ATTEMPTS`**: Maximum number of retry attempts for failed requests (default: 3)
* **`REQUEST_TIMEOUT`**: Timeout in seconds for HTTP requests (default: 180)
* **`RETRY_DELAY_SECONDS`**: Delay between retry attempts (default: 2)
* **`TOKEN_PREVIEW_LENGTH`**: Number of characters to show in token preview for logging (default: 7)

## Usage Examples

### Basic OAuth Authentication
```python
from iris.src.initial_setup.oauth_setup import setup_oauth

try:
    token = setup_oauth()
    print(f"Successfully obtained token: {token[:8]}...")
except ValueError as e:
    print(f"Configuration error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
```

### Integration with API Calls
```python
from iris.src.initial_setup.oauth_setup import setup_oauth

def make_authenticated_request():
    token = setup_oauth()
    headers = {"Authorization": f"Bearer {token}"}
    # Use token in subsequent API calls
    return headers
```

## Integration Points

How this module integrates with other IRIS components:

* **Model Initialization**: Called early in `model.py` startup to obtain authentication token
* **LLM Connectors**: Provides authentication tokens for all OpenAI API interactions
* **Agent Pipeline**: Token passed through entire agent workflow for secure API access
* **Process Monitor**: Authentication timing and success metrics tracked for monitoring
* **Error Handling**: Integration with centralized error handling and logging systems

## Dependencies

* **`requests`**: HTTP library for OAuth endpoint communication
* **`logging`**: Comprehensive logging of authentication process and errors
* **`time`**: Timing measurements and retry delay implementation
* **`typing`**: Type hints for function signatures and return values
* **Internal modules**: `env_config` for OAuth configuration settings

## Error Handling

Comprehensive error handling approach:

* **Configuration Validation**: Early validation of required OAuth settings with clear error messages
* **Network Resilience**: Retry logic with configurable attempts and delays for network failures
* **Response Validation**: JSON parsing and token presence validation with detailed error reporting
* **Exception Propagation**: Proper exception chaining and preservation for debugging
* **Graceful Degradation**: Detailed logging of failures without system crash

## Security Considerations

* **Credential Masking**: Client ID truncated to first 4 characters in logs to prevent exposure
* **Token Security**: Access tokens truncated in logs with configurable preview length
* **No Persistent Storage**: Tokens returned directly without local storage or caching
* **HTTPS Enforcement**: All OAuth requests use secure HTTPS transmission
* **Secret Protection**: Client secrets never logged or exposed in error messages

## Performance Notes

* **Retry Efficiency**: Configurable retry attempts and delays to balance reliability and speed
* **Timing Metrics**: Comprehensive timing tracking for performance monitoring and optimization
* **Request Timeout**: Configurable timeout prevents hanging requests in network issues
* **Memory Efficiency**: No token caching or storage reduces memory footprint
* **Connection Reuse**: Uses requests library connection pooling for efficiency

---

[Related Documentation: Environment Configuration (`env_config.py`), LLM Connectors (`rbc_openai.py`)]