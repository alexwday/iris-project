"""
OAuth Authentication Module for Document Refresh Pipeline.

Handles OAuth authentication for RBC API access with retry logic.
For local development, simply returns the OPENAI_API_KEY.

Functions:
    get_auth_token: Get authentication token (OAuth for RBC, API key for local)
    setup_oauth: Obtain OAuth authentication token for RBC API access
"""

import logging
import time

import requests

from ..utils.env_config import Config

logger = logging.getLogger(__name__)


def get_auth_token() -> str:
    """
    Get authentication token for LLM API calls.

    In local development mode (OPENAI_API_KEY set, no OAUTH_URL):
        Returns the OPENAI_API_KEY directly.

    In RBC environment (OAUTH_URL set):
        Performs OAuth client credentials flow to get a token.

    Returns:
        Authentication token string.

    Raises:
        ValueError: If no authentication method is configured.
    """
    # Check for local development with direct API key
    if Config.OPENAI_API_KEY and not Config.OAUTH_URL:
        logger.info("Using direct OpenAI API key for authentication")
        return Config.OPENAI_API_KEY

    # Check for RBC OAuth
    if Config.OAUTH_URL:
        logger.info("Using OAuth authentication for RBC environment")
        return setup_oauth()

    # No authentication configured
    raise ValueError(
        "No authentication configured. Set either OPENAI_API_KEY (local) "
        "or OAUTH_URL with CLIENT_ID and CLIENT_SECRET (RBC)."
    )


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
    logger.debug("OAuth setup starting")

    if not all([Config.OAUTH_URL, Config.OAUTH_CLIENT_ID, Config.OAUTH_CLIENT_SECRET]):
        error_msg = "Missing required OAuth settings: URL, client ID, or client secret"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.debug("OAuth URL endpoint: %s", Config.OAUTH_URL)
    logger.debug("Using client ID: %s****", Config.OAUTH_CLIENT_ID[:4])

    payload = {
        "grant_type": "client_credentials",
        "client_id": Config.OAUTH_CLIENT_ID,
        "client_secret": Config.OAUTH_CLIENT_SECRET,
    }

    start_time = time.time()
    last_exception = None

    logger.debug(
        "Beginning OAuth token request with max %d attempts", Config.MAX_RETRY_ATTEMPTS
    )

    for attempt_num in range(1, Config.MAX_RETRY_ATTEMPTS + 1):
        attempt_start = time.time()

        try:
            logger.debug(
                "Attempt %d/%d: Requesting OAuth token",
                attempt_num,
                Config.MAX_RETRY_ATTEMPTS,
            )

            response = requests.post(
                Config.OAUTH_URL, data=payload, timeout=Config.REQUEST_TIMEOUT
            )
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
                token_str[: Config.TOKEN_PREVIEW_LENGTH] + "..."
                if len(token_str) > Config.TOKEN_PREVIEW_LENGTH
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

            if attempt_num < Config.MAX_RETRY_ATTEMPTS:
                logger.debug("Retrying in %d seconds...", Config.RETRY_DELAY_SECONDS)
                time.sleep(Config.RETRY_DELAY_SECONDS)

    logger.error(
        "Failed to obtain OAuth token after %d attempts and %.2f seconds",
        Config.MAX_RETRY_ATTEMPTS,
        time.time() - start_time,
    )
    raise last_exception or requests.exceptions.RequestException(
        "Failed to obtain OAuth token"
    )
