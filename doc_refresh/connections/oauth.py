"""OAuth helpers for retrieving RBC API tokens with retries."""

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


def fetch_oauth_token() -> str:
    """Get an OAuth token using the client credentials flow with retries.

    Returns:
        str: OAuth access token for RBC API access.

    Raises:
        ValueError: If OAuth settings are missing or invalid, or no token is returned.
        requests.exceptions.RequestException: If the request fails after all retries.
    """
    if not all([OAUTH_URL, CLIENT_ID, CLIENT_SECRET]):
        error_msg = "Missing required OAuth settings: URL, client ID, or client secret"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if MAX_RETRY_ATTEMPTS < 1:
        raise ValueError("MAX_RETRY_ATTEMPTS must be at least 1")
    if REQUEST_TIMEOUT <= 0:
        raise ValueError("REQUEST_TIMEOUT must be greater than 0")
    if RETRY_DELAY_SECONDS < 0:
        raise ValueError("RETRY_DELAY_SECONDS cannot be negative")

    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    start_time = time.time()
    logger.debug(
        "Starting OAuth flow endpoint=%s client=%s**** attempts=%d timeout=%ss",
        OAUTH_URL,
        CLIENT_ID[:4],
        MAX_RETRY_ATTEMPTS,
        REQUEST_TIMEOUT,
    )

    with requests.Session() as session:
        for attempt_num in range(1, MAX_RETRY_ATTEMPTS + 1):
            attempt_start = time.time()

            try:
                response = session.post(
                    OAUTH_URL, data=payload, timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()

                token_data = response.json()
                if not isinstance(token_data, dict):
                    raise ValueError("OAuth response is not a JSON object")

                token = token_data.get("access_token")
                if not token:
                    raise ValueError("OAuth token not found in response")

                token_str = str(token)
                token_preview = (
                    f"{token_str[:TOKEN_PREVIEW_LENGTH]}..."
                    if len(token_str) > TOKEN_PREVIEW_LENGTH
                    else token_str
                )
                logger.debug(
                    "Received OAuth token in %.2fs (total %.2fs) attempt %d/%d: %s",
                    time.time() - attempt_start,
                    time.time() - start_time,
                    attempt_num,
                    MAX_RETRY_ATTEMPTS,
                    token_preview,
                )

                return token_str

            except (requests.exceptions.RequestException, ValueError) as exc:
                attempt_elapsed = time.time() - attempt_start
                logger.warning(
                    "OAuth attempt %d/%d failed after %.2f seconds: %s",
                    attempt_num,
                    MAX_RETRY_ATTEMPTS,
                    attempt_elapsed,
                    exc,
                )

                if attempt_num == MAX_RETRY_ATTEMPTS:
                    logger.error(
                        "OAuth token acquisition failed after %d attempts (%.2fs)",
                        MAX_RETRY_ATTEMPTS,
                        time.time() - start_time,
                    )
                    raise

                if RETRY_DELAY_SECONDS:
                    logger.debug("Retrying in %d seconds...", RETRY_DELAY_SECONDS)
                    time.sleep(RETRY_DELAY_SECONDS)

    # Should never reach here due to raise in final attempt, but for clarity:
    raise ValueError("OAuth token acquisition failed")
