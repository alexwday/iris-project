"""
SSL Certificate Setup Module

This module handles the SSL certificate setup required for secure API communication
by configuring environment variables to use an existing certificate. It includes
functionality to validate the certificate's existence and optionally check its
expiration date.

Functions:
    check_certificate_expiry: Validates certificate expiration date
    setup_ssl: Configures SSL environment with existing CA bundle certificate
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from ..config import IS_RBC_ENV, USE_SSL

# Try to import certificate checking libraries, but don't fail if not available in local env
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Only import SSL settings if we're in RBC environment
if IS_RBC_ENV and USE_SSL:
    from .ssl_settings import (
        CHECK_CERT_EXPIRY,
        EXPIRY_WARNING_DAYS,
        SSL_CERT_DIR,
        SSL_CERT_FILENAME,
        SSL_CERT_PATH,
    )

# Get module logger
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
        logger.info(f"Checking certificate expiry for: {cert_path}")

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

        logger.info(f"Certificate valid until {expiry_date.strftime('%Y-%m-%d')}")
        return True

    except Exception as e:
        logger.error(f"Error checking certificate expiry: {str(e)}")
        raise


def setup_ssl(custom_cert_path=None) -> str:
    """
    Configure SSL environment with existing CA bundle certificate.

    This function performs the following steps:
    1. Checks if SSL is required for the current environment
    2. If in local environment, returns a placeholder message
    3. In RBC environment:
       a. Attempts to find a valid certificate in multiple locations
       b. Optionally checks certificate expiration (if enabled in settings)
       c. Sets appropriate environment variables to use the certificate

    Args:
        custom_cert_path (str, optional): Custom path to a certificate file

    Returns:
        str: Path to the configured SSL certificate or placeholder message

    Raises:
        FileNotFoundError: If certificate file cannot be found
        Exception: If certificate validation fails
    """
    # Skip SSL setup in local environment
    if not IS_RBC_ENV or not USE_SSL:
        logger.info("SSL certificate setup skipped in local environment")
        return "SSL certificate not required in local environment"

    # RBC Environment: Proceed with SSL certificate setup
    # Log settings being used
    logger.info(f"SSL setup starting with settings from: {__file__}")
    
    # Try to find a valid certificate
    cert_paths_to_try = []
    
    # Add custom path if provided
    if custom_cert_path and os.path.exists(custom_cert_path):
        cert_paths_to_try.append(custom_cert_path)
        logger.info(f"Using custom certificate path: {custom_cert_path}")
    
    # Add default path from settings
    cert_paths_to_try.append(SSL_CERT_PATH)
    logger.info(f"Using default certificate path: {SSL_CERT_PATH}")
    
    # Add common system locations for certificates
    system_cert_paths = [
        # Common RBC environment locations
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "ssl", SSL_CERT_FILENAME),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "certs", SSL_CERT_FILENAME),
        # Mac OS default locations
        "/etc/ssl/cert.pem",
        "/usr/local/etc/openssl/cert.pem",
        # Linux default locations
        "/etc/ssl/certs/ca-certificates.crt",
        # Windows (may not exist on other platforms)
        os.path.expandvars("%APPDATA%\\ssl\\cert.pem")
    ]
    
    # Add system paths if they exist
    for path in system_cert_paths:
        if os.path.exists(path):
            cert_paths_to_try.append(path)
            logger.info(f"Found system certificate at: {path}")
    
    # Try each path until we find a working certificate
    cert_path = None
    for path in cert_paths_to_try:
        if os.path.exists(path):
            logger.info(f"Found certificate at {path}")
            cert_path = path
            break
    
    # If no certificate was found, handle the error
    if not cert_path:
        paths_tried = "\n - ".join(cert_paths_to_try)
        error_msg = f"No valid SSL certificate found. Tried the following paths:\n - {paths_tried}"
        logger.error(error_msg)
        
        # Fallback behavior - on Mac/Linux try to use the system default
        if os.name != 'nt':  # Not Windows
            logger.info("Attempting to use system SSL certificates...")
            # Don't set environment variables, let the system find certificates
            logger.info("Using system default SSL certificates")
            return "Using system default SSL certificates"
        else:
            raise FileNotFoundError(error_msg)

    logger.info(f"Using certificate file: {cert_path}")

    # Check certificate expiry if enabled
    if CHECK_CERT_EXPIRY:
        try:
            check_certificate_expiry(cert_path)
        except Exception as e:
            logger.warning(f"Certificate expiry check failed: {str(e)}")
    else:
        logger.info("Certificate expiry check disabled")

    # Configure SSL environment variables
    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path
    
    # For Python requests and urllib3
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path
    os.environ["CURL_CA_BUNDLE"] = cert_path

    logger.info(f"SSL environment configured successfully. Certificate path: {cert_path}")
    return cert_path