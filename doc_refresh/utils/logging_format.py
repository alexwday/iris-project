"""
Logging Format - Application-wide logging configuration.

This module configures Python's root logger for consistent log output across
all IRIS components. It sets up a stderr stream handler with timestamp, logger
name, and level formatting. Called once during application startup before any
agents or database connections are initialized.

Log level defaults to the IRIS_LOG_LEVEL environment variable but can be
overridden programmatically.
"""

import logging
import sys

from .env_config import config


def configure_root_logger(level: int | None = None) -> logging.Logger:
    """Initialize the root logger with stderr output and standard formatting.

    Args:
        level: Logging level constant (e.g., logging.INFO). Defaults to config.

    Returns:
        The configured root logger instance.
    """
    if level is None:
        level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()

    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    root_logger.info("Logging system initialized")
    return root_logger
