# python/iris/src/initial_setup/oauth/oauth.py
"""
Authentication Module for API Integration

This module handles authentication for API access, with support for both
RBC OAuth and local API key methods. It includes robust error handling,
retry logic, and detailed logging for operational monitoring.

Functions:
    setup_oauth: Obtains authentication token for API access

Dependencies:
    - requests
    - logging
    - time
    - typing
"""

import logging
import time
from typing import Dict, Tuple

import requests

from ...chat_model.model_settings import IS_RBC_ENV, USE_OAUTH

# Import appropriate settings based on environment
if IS_RBC_ENV and USE_OAUTH:
    from .oauth_settings import (
        CLIENT_ID,
        CLIENT_SECRET,
        MAX_RETRY_ATTEMPTS,
        OAUTH_URL,
        REQUEST_TIMEOUT,
        RETRY_DELAY_SECONDS,
        TOKEN_PREVIEW_LENGTH,
    )
else:
    # Import local authentication settings
    from .local_auth_settings import OPENAI_API_KEY, TOKEN_PREVIEW_LENGTH

    # Default values for local environment
    REQUEST_TIMEOUT = 30
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 2

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)


def setup_oauth() -> str:
    """
    Obtain authentication token for API access.

    In RBC environment:
    - Uses OAuth client credentials flow to obtain a token
    - Includes retry logic and detailed logging

    In local environment:
    - Uses API key from local_auth_settings.py

    Returns:
        str: Authentication token for API access

    Raises:
        requests.exceptions.RequestException: If API request fails after retries
        ValueError: If token is not found or settings are invalid
    """
    # Local environment: Use API key authentication
    if not IS_RBC_ENV or not USE_OAUTH:
        logger.info("Using API key authentication from local settings")

        # Verify API key is set
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
            error_msg = "API key not properly configured in local_auth_settings.py"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Create a preview of the API key for logging
        key_preview = (
            OPENAI_API_KEY[:TOKEN_PREVIEW_LENGTH] + "..."
            if len(OPENAI_API_KEY) > TOKEN_PREVIEW_LENGTH
            else OPENAI_API_KEY
        )
        logger.info(f"Using OpenAI API key from settings: {key_preview}")

        return OPENAI_API_KEY

    # RBC Environment: Proceed with OAuth token acquisition
    logger.info(f"OAuth setup starting with settings from: {__file__}")

    # Validate settings
    if not all([OAUTH_URL, CLIENT_ID, CLIENT_SECRET]):
        error_msg = "Missing required OAuth settings: URL, client ID, or client secret"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"OAuth URL endpoint: {OAUTH_URL}")
    logger.info(
        f"Using client ID: {CLIENT_ID[:4]}****"
    )  # Show only first 4 chars for security

    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    attempts = 0
    last_exception = None
    total_time = 0
    start_time = time.time()

    logger.info(f"Beginning OAuth token request with max {MAX_RETRY_ATTEMPTS} attempts")

    while attempts < MAX_RETRY_ATTEMPTS:
        attempt_start = time.time()
        attempts += 1

        try:
            logger.info(
                f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Requesting OAuth token"
            )

            response = requests.post(OAUTH_URL, data=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            attempt_time = time.time() - attempt_start
            logger.info(f"Received response in {attempt_time:.2f} seconds")

            token_data = response.json()
            token = token_data.get("access_token")

            if not token:
                raise ValueError("OAuth token not found in response")

            # Ensure token is a string
            token_str: str = str(token)

            # Create a preview of the token for logging
            token_preview = (
                token_str[:TOKEN_PREVIEW_LENGTH] + "..."
                if len(token_str) > TOKEN_PREVIEW_LENGTH
                else token_str
            )
            logger.info(f"Successfully obtained OAuth token: {token_preview}")

            total_time_seconds = time.time() - start_time
            logger.info(
                f"Total OAuth process completed in {total_time_seconds:.2f} seconds after {attempts} attempt(s)"
            )

            return token_str

        except (requests.exceptions.RequestException, ValueError) as e:
            last_exception = e
            attempt_time = time.time() - attempt_start
            logger.warning(
                f"OAuth token request attempt {attempts} failed after {attempt_time:.2f} seconds: {str(e)}"
            )

            if attempts < MAX_RETRY_ATTEMPTS:
                logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)

    # If we've exhausted all retries, raise the last exception
    total_time_seconds = time.time() - start_time
    logger.error(
        f"Failed to obtain OAuth token after {attempts} attempts and {total_time_seconds:.2f} seconds"
    )
    raise last_exception or requests.exceptions.RequestException(
        "Failed to obtain OAuth token"
    )
