# SSL Setup (`iris/src/initial_setup/ssl_setup.py`)

The SSL setup module handles SSL certificate configuration for secure API communication in enterprise environments. It configures environment variables to use existing CA bundle certificates, validates certificate existence and expiration, and ensures proper HTTPS connectivity for all external API interactions.

## Overview

This module provides the SSL foundation for secure communication in the IRIS system, particularly important for RBC's enterprise security requirements. It manages CA bundle certificates, performs optional expiration validation, and configures the Python environment to use specified certificates for all HTTPS connections. The module includes graceful degradation for optional dependencies and comprehensive error handling.

## Key Components

* **`ssl_setup.py`**: Contains SSL configuration logic with certificate validation and environment setup

## Core Functions/Classes

### `setup_ssl()`

#### Purpose
Configures the SSL environment with existing CA bundle certificate, ensuring secure HTTPS communication for all API interactions.

#### Parameters
None

#### Returns
* **str**: Path to the configured SSL certificate for verification and monitoring

#### Workflow
1. **Configuration Loading**: Loads SSL settings from `env_config` including certificate filename and validation preferences
2. **Path Resolution**: Calculates certificate path based on module directory location using `__file__`
3. **Certificate Validation**: Verifies certificate file exists at expected path with detailed logging
4. **Expiration Checking**: Optionally validates certificate expiration if `CHECK_CERT_EXPIRY` enabled
5. **Environment Configuration**: Sets `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` environment variables
6. **Verification Logging**: Comprehensive logging of setup steps and certificate details

#### Error Handling
* **FileNotFoundError**: Raised when certificate file doesn't exist at expected path
* **Exception**: Certificate validation failures logged with detailed error messages

### `check_certificate_expiry(cert_path)`

#### Purpose
Validates certificate expiration date and provides early warning of upcoming expiration to prevent service disruptions.

#### Parameters
* **`cert_path`** (str): Path to certificate file for expiration validation

#### Returns
* **bool**: True if certificate is valid and not expiring soon, False if expired

#### Workflow
1. **Library Availability**: Checks if cryptography library is available for certificate parsing
2. **Certificate Loading**: Reads certificate file in binary mode for X.509 parsing
3. **Date Parsing**: Extracts expiration date using timezone-aware datetime handling
4. **Expiration Validation**: Compares current date with certificate expiration using UTC
5. **Warning Calculation**: Calculates days until expiration and warns if within threshold
6. **Status Reporting**: Logs certificate validity status with detailed date information

#### Error Handling
* **ImportError**: Graceful degradation if cryptography library unavailable
* **FileError**: Comprehensive error handling for file reading failures
* **ParseError**: Detailed logging of certificate parsing errors

## Configuration

Settings used from `env_config`:

* **`SSL_CERT_FILENAME`**: Certificate filename (default: "rbc-ca-bundle.cer")
* **`SSL_CHECK_CERT_EXPIRY`**: Enable expiration checking (default: true)
* **`SSL_EXPIRY_WARNING_DAYS`**: Warning threshold in days (default: 30)

## Usage Examples

### Basic SSL Setup
```python
from iris.src.initial_setup.ssl_setup import setup_ssl

# Configure SSL environment
cert_path = setup_ssl()
print(f"SSL configured with certificate: {cert_path}")
```

### Manual Certificate Validation
```python
from iris.src.initial_setup.ssl_setup import check_certificate_expiry

cert_path = "/path/to/certificate.pem"
is_valid = check_certificate_expiry(cert_path)
if not is_valid:
    print("Certificate validation failed")
```

### Environment Integration
```python
# After setup_ssl(), environment variables are configured
import os
print(f"SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE')}")
print(f"REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE')}")
```

## Integration Points

How this module integrates with other IRIS components:

* **Model Initialization**: Called early in startup to establish secure communication foundation
* **LLM Connectors**: Provides SSL configuration for all OpenAI API interactions
* **OAuth Setup**: Ensures secure authentication requests with proper certificate validation
* **Database Connections**: Enables secure database connections when SSL required
* **External APIs**: Configures environment for all HTTPS-based external service calls

## Dependencies

* **`os`**: Environment variable configuration and file path operations
* **`logging`**: Comprehensive logging of SSL setup and validation operations
* **`datetime`**: Timezone-aware timestamp handling for expiration calculations
* **`cryptography`** (optional): X.509 certificate parsing and validation
* **Internal modules**: `env_config` for SSL configuration settings

## Error Handling

Comprehensive error handling approach:

* **Certificate Existence**: File existence validation with clear error messages
* **Library Dependencies**: Graceful degradation when optional cryptography library unavailable
* **Certificate Parsing**: Detailed error logging for certificate format or corruption issues
* **Expiration Validation**: Timezone-aware date handling to prevent validation errors
* **Environment Setup**: Validation that environment variables are properly set

## Security Considerations

* **Certificate Validation**: Optional but recommended expiration checking to prevent outages
* **Path Security**: Certificate path resolution using secure module directory location
* **Environment Isolation**: SSL configuration through environment variables prevents hardcoding
* **Error Information**: Careful error logging to avoid exposing sensitive certificate details
* **Graceful Degradation**: System remains functional even if optional validation fails

## Performance Notes

* **Startup Overhead**: SSL setup performed once during application initialization
* **Certificate Caching**: Environment variables cached by system for subsequent use
* **Optional Validation**: Expiration checking can be disabled for performance-critical scenarios
* **File I/O Efficiency**: Certificate file read once during setup process
* **Memory Efficiency**: No certificate data retained in memory after validation

---

[Related Documentation: Environment Configuration (`env_config.py`), OAuth Setup (`oauth_setup.py`)]