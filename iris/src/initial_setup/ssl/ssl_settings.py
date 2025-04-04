# python/iris/src/initial_setup/ssl/ssl_settings.py
"""
SSL Certificate Settings Configuration

This module defines the configuration settings for SSL certificate handling,
including certificate path, filename, and validation options for secure API
communication.

Attributes:
    SSL_CERT_DIR (str): Directory containing the SSL certificate
    SSL_CERT_FILENAME (str): Name of the SSL certificate file
    SSL_CERT_PATH (str): Full path to the SSL certificate
    CHECK_CERT_EXPIRY (bool): Whether to check certificate expiration
    EXPIRY_WARNING_DAYS (int): Number of days before expiry to trigger warnings

Dependencies:
    - os
    - logging
    - datetime
"""

import logging
import os
from datetime import datetime, timedelta

# Get module logger (no configuration here - using centralized config)
logger = logging.getLogger(__name__)

# Get the absolute path to the directory containing this settings file
_SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

# Certificate settings
SSL_CERT_FILENAME = "rbc-ca-bundle.cer"
SSL_CERT_DIR = _SETTINGS_DIR  # Default to the same directory as settings file
SSL_CERT_PATH = os.path.join(SSL_CERT_DIR, SSL_CERT_FILENAME)

# Expiry check settings
CHECK_CERT_EXPIRY = True  # Whether to check certificate expiry
EXPIRY_WARNING_DAYS = 30  # Warn if certificate expires within this many days

logger.debug(f"SSL settings initialized")
logger.debug(f"Calculated SSL_CERT_PATH: {SSL_CERT_PATH}")
logger.debug(
    f"Certificate expiry checking: {'Enabled' if CHECK_CERT_EXPIRY else 'Disabled'}"
)
