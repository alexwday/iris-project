"""
RBC Security - SSL certificate configuration for RBC infrastructure.

This module handles SSL certificate setup required for HTTPS connections within
RBC's network. It wraps the optional rbc_security package which is only available
in RBC's deployment environment. Called during application startup to enable
secure connections to Azure endpoints and internal services.

When running locally (outside RBC infrastructure), the rbc_security import fails
gracefully and the application continues without certificate configuration.
"""

import logging
from typing import Optional

try:
    import rbc_security

    _RBC_SECURITY_AVAILABLE = True
except ImportError:
    _RBC_SECURITY_AVAILABLE = False

logger = logging.getLogger(__name__)


def configure_rbc_security_certs() -> Optional[str]:
    """Enable RBC SSL certificates if the rbc_security package is available.

    Returns:
        "rbc_security" if certificates were enabled, None if unavailable.
    """
    if not _RBC_SECURITY_AVAILABLE:
        logger.info("rbc_security not available, continuing without SSL certificates")
        return None

    logger.info("Enabling RBC Security certificates...")
    rbc_security.enable_certs()
    logger.info("RBC Security certificates enabled")
    return "rbc_security"
