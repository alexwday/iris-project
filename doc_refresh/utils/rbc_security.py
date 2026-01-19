"""RBC Security certificate setup.

Uses optional ``rbc_security`` support for SSL when available.
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
    """Configure SSL certificates for the RBC environment.

    Enables certificates if ``rbc_security`` is available; logs and continues
    otherwise.

    Returns:
        Optional[str]: ``"rbc_security"`` when certificates are enabled; otherwise
        None.
    """
    if not _RBC_SECURITY_AVAILABLE:
        logger.info("rbc_security not available, continuing without SSL certificates")
        return None

    logger.info("Enabling RBC Security certificates...")
    rbc_security.enable_certs()
    logger.info("RBC Security certificates enabled")
    return "rbc_security"


# Backwards compatibility
def setup_ssl() -> Optional[str]:
    """Alias for legacy doc_refresh callers."""
    return configure_rbc_security_certs()
