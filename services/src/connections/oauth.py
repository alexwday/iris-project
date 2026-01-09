"""
OAuth Authentication Module.

Handles OAuth authentication for RBC API access with retry logic and logging.

Functions:
    setup_oauth: Obtain OAuth authentication token for API access
"""

import logging
import time

import requests

from ..utils.env_config import config

logger = logging.getLogger(__name__)

CLIENT_ID = config.OAUTH_CLIENT_ID
CLIENT_SECRET = config.OAUTH_CLIENT_SECRET
MAX_RETRY_ATTEMPTS = config.MAX_RETRY_ATTEMPTS
OAUTH_URL = config.OAUTH_URL
REQUEST_TIMEOUT = config.REQUEST_TIMEOUT
RETRY_DELAY_SECONDS = config.RETRY_DELAY_SECONDS
TOKEN_PREVIEW_LENGTH = config.TOKEN_PREVIEW_LENGTH


def setup_oauth() -> str:
    """
    Obtain OAuth authentication token for RBC API access.

    Uses OAuth client credentials flow to obtain a token with retry logic
    and detailed logging for operational monitoring.

    Returns:
        OAuth authentication token for API access.

    Raises:
        requests.exceptions.RequestException: If API request fails after retries.
        ValueError: If token is not found or settings are invalid.
    """
    logger.debug("OAuth setup starting with settings from: %s", __file__)

    if not all([OAUTH_URL, CLIENT_ID, CLIENT_SECRET]):
        error_msg = "Missing required OAuth settings: URL, client ID, or client secret"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.debug("OAuth URL endpoint: %s", OAUTH_URL)
    logger.debug("Using client ID: %s****", CLIENT_ID[:4])

    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    start_time = time.time()
    last_exception = None

    logger.debug(
        "Beginning OAuth token request with max %d attempts", MAX_RETRY_ATTEMPTS
    )

    for attempt_num in range(1, MAX_RETRY_ATTEMPTS + 1):
        attempt_start = time.time()

        try:
            logger.debug(
                "Attempt %d/%d: Requesting OAuth token",
                attempt_num,
                MAX_RETRY_ATTEMPTS,
            )

            response = requests.post(OAUTH_URL, data=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            logger.debug(
                "Received response in %.2f seconds", time.time() - attempt_start
            )

            token_data = response.json()
            token = token_data.get("access_token")

            if not token:
                raise ValueError("OAuth token not found in response")

            token_str: str = str(token)

            token_preview = (
                token_str[:TOKEN_PREVIEW_LENGTH] + "..."
                if len(token_str) > TOKEN_PREVIEW_LENGTH
                else token_str
            )
            logger.debug("Successfully obtained OAuth token: %s", token_preview)

            logger.debug(
                "Total OAuth process completed in %.2f seconds after %d attempt(s)",
                time.time() - start_time,
                attempt_num,
            )

            return token_str

        except (requests.exceptions.RequestException, ValueError) as exc:
            last_exception = exc
            logger.warning(
                "OAuth token request attempt %d failed after %.2f seconds: %s",
                attempt_num,
                time.time() - attempt_start,
                exc,
            )

            if attempt_num < MAX_RETRY_ATTEMPTS:
                logger.debug("Retrying in %d seconds...", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)

    logger.error(
        "Failed to obtain OAuth token after %d attempts and %.2f seconds",
        MAX_RETRY_ATTEMPTS,
        time.time() - start_time,
    )
    raise last_exception or requests.exceptions.RequestException(
        "Failed to obtain OAuth token"
    )
