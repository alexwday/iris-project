# services/src/initial_setup/oauth_setup.py
"""
Authentication Module for API Integration

This module handles OAuth authentication for RBC API access. It includes
robust error handling, retry logic, and detailed logging for operational monitoring.

Functions:
    setup_oauth: Obtains OAuth authentication token for API access

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

from .env_config import config

# Get OAuth settings from config
CLIENT_ID = config.OAUTH_CLIENT_ID
CLIENT_SECRET = config.OAUTH_CLIENT_SECRET
MAX_RETRY_ATTEMPTS = config.MAX_RETRY_ATTEMPTS
OAUTH_URL = config.OAUTH_URL
REQUEST_TIMEOUT = config.REQUEST_TIMEOUT
RETRY_DELAY_SECONDS = config.RETRY_DELAY_SECONDS
TOKEN_PREVIEW_LENGTH = config.TOKEN_PREVIEW_LENGTH

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)


def setup_oauth() -> str:
    """
    Obtain OAuth authentication token for RBC API access.

    Uses OAuth client credentials flow to obtain a token with retry logic
    and detailed logging for operational monitoring.

    Returns:
        str: OAuth authentication token for API access

    Raises:
        requests.exceptions.RequestException: If API request fails after retries
        ValueError: If token is not found or settings are invalid
    """
    logger.debug(f"OAuth setup starting with settings from: {__file__}")

    # Validate settings
    if not all([OAUTH_URL, CLIENT_ID, CLIENT_SECRET]):
        error_msg = "Missing required OAuth settings: URL, client ID, or client secret"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.debug(f"OAuth URL endpoint: {OAUTH_URL}")
    logger.debug(
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

    logger.debug(
        f"Beginning OAuth token request with max {MAX_RETRY_ATTEMPTS} attempts"
    )

    while attempts < MAX_RETRY_ATTEMPTS:
        attempt_start = time.time()
        attempts += 1

        try:
            logger.debug(
                f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Requesting OAuth token"
            )

            response = requests.post(OAUTH_URL, data=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            attempt_time = time.time() - attempt_start
            logger.debug(f"Received response in {attempt_time:.2f} seconds")

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
            logger.debug(f"Successfully obtained OAuth token: {token_preview}")

            total_time_seconds = time.time() - start_time
            logger.debug(
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
                logger.debug(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)

    # If we've exhausted all retries, raise the last exception
    total_time_seconds = time.time() - start_time
    logger.error(
        f"Failed to obtain OAuth token after {attempts} attempts and {total_time_seconds:.2f} seconds"
    )
    raise last_exception or requests.exceptions.RequestException(
        "Failed to obtain OAuth token"
    )
