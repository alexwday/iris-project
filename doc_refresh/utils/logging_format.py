"""
Centralized Logging Configuration Module.

Provides consistent logging configuration for all modules in the application,
preventing duplicate log messages and ensuring uniform log formatting.
The logging level is configured via environment variables.

Functions:
    configure_logging: Set up the root logger with appropriate handlers
"""

import logging
import sys
from typing import Optional

from .env_config import Config


def configure_logging(level: Optional[int] = None) -> logging.Logger:
    """
    Configure root logger with handlers for consistent logging across modules.

    This function should be called once at application startup to establish
    a unified logging configuration. It clears any existing handlers to avoid
    duplicate log messages.

    Args:
        level: The logging level to set. If None, uses environment config.

    Returns:
        Configured root logger.
    """
    if level is None:
        level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()

    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    logging.info("Logging system initialized")

    return root_logger
