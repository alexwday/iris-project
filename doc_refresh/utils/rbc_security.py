"""RBC Security certificate setup.

Uses optional ``rbc_security`` support for SSL; disabled when IRIS_DEV_MODE=true.
"""

import logging
from typing import Optional

from .env_config import config

try:
    import rbc_security

    _RBC_SECURITY_AVAILABLE = True
except ImportError:
    _RBC_SECURITY_AVAILABLE = False

logger = logging.getLogger(__name__)


def configure_rbc_security_certs() -> Optional[str]:
    """Configure SSL certificates for the RBC environment.

    Skips configuration when ``config.DEV_MODE`` is true. Logs a warning and
    returns None if the optional ``rbc_security`` dependency is missing.

    Returns:
        Optional[str]: ``"rbc_security"`` when certificates are enabled; otherwise
        None.
    """
    if config.DEV_MODE:
        logger.info("DEV_MODE: Skipping SSL setup")
        return None

    if not _RBC_SECURITY_AVAILABLE:
        logger.warning(
            "rbc_security not available; install with `pip install rbc_security`. "
            "Continuing without SSL certificates (may fail in RBC environment)."
        )
        return None

    logger.info("Enabling RBC Security certificates...")
    rbc_security.enable_certs()
    logger.info("RBC Security certificates enabled")
    return "rbc_security"


# Backwards compatibility
def setup_ssl() -> Optional[str]:
    """Alias for legacy doc_refresh callers."""
    return configure_rbc_security_certs()
