# services/src/initial_setup/ssl_setup.py
"""
SSL Certificate Setup Module

This module handles the SSL certificate setup required for secure API communication
by configuring environment variables to use an existing certificate. It includes
functionality to validate the certificate's existence and optionally check its
expiration date.

Functions:
    check_certificate_expiry: Validates certificate expiration date
    setup_ssl: Configures SSL environment with existing CA bundle certificate

Dependencies:
    - os
    - logging
    - datetime
    - cryptography (for certificate parsing)
"""

import logging
import os
from datetime import datetime, timedelta, timezone

# Try to import certificate checking libraries
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Import configuration
from .env_config import config

# Get SSL settings from config
CHECK_CERT_EXPIRY = config.SSL_CHECK_CERT_EXPIRY
EXPIRY_WARNING_DAYS = config.SSL_EXPIRY_WARNING_DAYS
SSL_CERT_FILENAME = config.SSL_CERT_FILENAME

# Calculate SSL certificate directory and path based on this module's location
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CERT_DIR = _MODULE_DIR
SSL_CERT_PATH = os.path.join(SSL_CERT_DIR, SSL_CERT_FILENAME)

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)


def check_certificate_expiry(cert_path: str) -> bool:
    """
    Check if the certificate is valid and not expired or expiring soon.

    Args:
        cert_path (str): Path to the certificate file

    Returns:
        bool: True if valid and not expiring soon, False otherwise

    Raises:
        Exception: If there's an error reading or parsing the certificate
    """
    if not CRYPTO_AVAILABLE:
        logger.warning(
            "Cryptography library not available, skipping certificate expiry check"
        )
        return True

    try:
        logger.debug(f"Checking certificate expiry for: {cert_path}")

        # Read certificate data
        with open(cert_path, "rb") as cert_file:
            cert_data = cert_file.read()

        # Parse the certificate
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

        # Get expiration date using the UTC method to avoid deprecation warning
        expiry_date = cert.not_valid_after_utc

        # Use timezone-aware current date to match expiry_date's timezone awareness
        current_date = datetime.now(timezone.utc)

        # Check if expired
        if current_date > expiry_date:
            logger.error(f"Certificate expired on {expiry_date.strftime('%Y-%m-%d')}")
            return False

        # Check if expiring soon
        days_until_expiry = (expiry_date - current_date).days
        if days_until_expiry <= EXPIRY_WARNING_DAYS:
            logger.warning(
                f"Certificate will expire in {days_until_expiry} days "
                f"(on {expiry_date.strftime('%Y-%m-%d')})"
            )
            return True

        logger.debug(f"Certificate valid until {expiry_date.strftime('%Y-%m-%d')}")
        return True

    except Exception as e:
        logger.error(f"Error checking certificate expiry: {str(e)}")
        raise


def setup_ssl() -> str:
    """
    Configure SSL environment with existing CA bundle certificate.

    This function performs the following steps:
    1. Verifies the certificate file exists
    2. Optionally checks certificate expiration (if enabled in settings)
    3. Sets appropriate environment variables to use the certificate

    Returns:
        str: Path to the configured SSL certificate

    Raises:
        FileNotFoundError: If certificate file does not exist
        Exception: If certificate validation fails
    """
    # Proceed with SSL certificate setup
    # Log settings being used
    logger.debug(f"SSL setup starting with settings from: {__file__}")
    logger.debug(f"Using certificate directory: {SSL_CERT_DIR}")
    logger.debug(f"Using certificate filename: {SSL_CERT_FILENAME}")
    logger.debug(f"Full certificate path: {SSL_CERT_PATH}")

    # Verify the certificate exists
    if not os.path.exists(SSL_CERT_PATH):
        error_msg = f"Certificate not found at {SSL_CERT_PATH}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    logger.debug(f"Certificate file exists at {SSL_CERT_PATH}")

    # Check certificate expiry if enabled
    if CHECK_CERT_EXPIRY:
        try:
            check_certificate_expiry(SSL_CERT_PATH)
        except Exception as e:
            logger.warning(f"Certificate expiry check failed: {str(e)}")
    else:
        logger.debug("Certificate expiry check disabled")

    # Configure SSL environment variables
    os.environ["SSL_CERT_FILE"] = SSL_CERT_PATH
    os.environ["REQUESTS_CA_BUNDLE"] = SSL_CERT_PATH

    logger.debug(
        f"SSL environment configured successfully. Certificate path: {SSL_CERT_PATH}"
    )
    return SSL_CERT_PATH
