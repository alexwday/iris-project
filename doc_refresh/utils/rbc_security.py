"""
RBC Security Certificate Setup Module.

Simplified SSL setup using rbc_security library when available.
Can be disabled with IRIS_DEV_MODE=true environment variable for local development.

Functions:
    setup_ssl: Configure SSL certificates for RBC environment
"""

import logging
from typing import Optional

from .env_config import Config

try:
    import rbc_security

    _RBC_SECURITY_AVAILABLE = True
except ImportError:
    _RBC_SECURITY_AVAILABLE = False

logger = logging.getLogger(__name__)


def setup_ssl() -> Optional[str]:
    """
    Set up SSL certificates for RBC environment.

    Uses rbc_security library if available.
    Can be disabled with IRIS_DEV_MODE=true environment variable.

    Returns:
        "rbc_security" if certificates were enabled, None otherwise.
    """
    if Config.DEV_MODE:
        logger.info("DEV_MODE: Skipping SSL setup")
        return None

    if not _RBC_SECURITY_AVAILABLE:
        logger.warning(
            "rbc_security not available - install with: pip install rbc_security"
        )
        logger.warning(
            "Continuing without SSL certificates (may fail in RBC environment)"
        )
        return None

    logger.info("Enabling RBC Security certificates...")
    rbc_security.enable_certs()
    logger.info("RBC Security certificates enabled")
    return "rbc_security"
