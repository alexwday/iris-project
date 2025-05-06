# OAuth Authentication (`iris/src/initial_setup/oauth/`)

This directory contains modules responsible for handling authentication within the IRIS system. It provides a robust authentication layer supporting both RBC's enterprise OAuth flow and local API key authentication, ensuring secure API communication across different deployment environments.

## Architecture Overview

The OAuth module implements a flexible, environment-aware approach to authentication that transparently adapts to different deployment contexts. It abstracts authentication complexity from the rest of the system while providing consistent token management and error handling.

### Key Components

* **`oauth.py`**: Core authentication module that:
  * Provides a unified `setup_oauth()` function for token acquisition
  * Implements conditional authentication for different environments
  * Supports RBC enterprise OAuth flow with automatic token refresh
  * Handles local development with API key authentication
  * Manages token caching to minimize authentication requests
  * Implements retry logic for transient authentication failures
  * Logs authentication activities for monitoring and debugging
  * Provides comprehensive error handling with typed exceptions
  * Returns standardized token formats for downstream consumers

* **`oauth_settings.py`**: Configuration module that defines:
  * OAuth endpoints and authentication parameters
  * Client credentials for token requests
  * Timeout and retry settings
  * Token expiration buffer periods
  * Environment indicators and flags
  * Type definitions for function parameters

* **`local_auth_settings.py`**: Local development module that:
  * Provides a simplified authentication interface for development
  * Stores local API keys securely
  * Mimics OAuth response format for consistent integration
  * Enables testing without enterprise OAuth infrastructure

## Authentication Flow

The OAuth module follows a systematic authentication approach:

### 1. Environment Detection
* Determines whether running in RBC enterprise or local environment
* Sets appropriate authentication strategy based on environment
* Configures paths, endpoints, and credentials accordingly

### 2. Authentication Methods
* **Enterprise OAuth Flow**: 
  * Uses client credentials grant type
  * Retrieves and caches access tokens
  * Handles token expiration and refresh
  * Manages secure token storage
* **Local API Key Method**: 
  * Uses API keys directly stored in local settings
  * Formats API keys in OAuth-compatible format
  * Simplifies development and testing workflow

### 3. Error Management
* Implements automatic retries for network-related failures
* Provides detailed logging for troubleshooting
* Raises appropriate exceptions with context
* Gracefully handles timeout and connection issues

### 4. Token Delivery
* Returns tokens in consistent format regardless of source
* Ensures all downstream components receive properly formatted credentials
* Manages authentication headers for API requests

## Common Authentication Workflow

The typical workflow follows this pattern:

1. **Authentication Request**: System component calls `setup_oauth()` for a token
2. **Environment Check**: Module determines appropriate authentication method
3. **Token Acquisition**: Module retrieves token through OAuth flow or local settings
4. **Validation**: Authentication response is validated for correctness
5. **Token Return**: Properly formatted token is returned to calling component
6. **Usage**: Token is used for authenticating API requests

## Integration with the Wider System

The OAuth module is a foundational security component that:

* Provides authentication tokens for LLM API requests
* Supports both enterprise and development environments
* Abstracts authentication complexity from other components
* Ensures secure and authorized API access
* Integrates with the SSL module for secure communication

## Error Handling and Monitoring

The authentication system implements:

* Detailed logging with authentication steps and results
* Automatic retries with configurable parameters
* Typed exceptions for different error scenarios
* Token validation to prevent unauthorized access
* Comprehensive error context for troubleshooting

---

Refer to the main project README and the initial_setup README for details on how the OAuth module integrates with the overall IRIS system infrastructure.