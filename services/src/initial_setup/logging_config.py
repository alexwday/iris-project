# python/iris/src/initial_setup/logging_config.py
"""
Centralized Logging Configuration Module

This module provides a consistent logging configuration for all modules
in the application, preventing duplicate log messages and ensuring uniform
log formatting across the application. The logging level is configured
via environment variables.

Functions:
    configure_logging: Sets up the root logger with appropriate handlers

Dependencies:
    - logging
    - sys
    - services.src.initial_setup.env_config
"""

import logging
import sys
from ..initial_setup.env_config import config


def configure_logging(level=None):
    """
    Configure root logger with handlers for consistent logging across modules.

    This function should be called once at application startup to establish
    a unified logging configuration. It clears any existing handlers to avoid
    duplicate log messages.

    Args:
        level (int): The logging level to set. If None, uses environment config.

    Returns:
        logging.Logger: Configured root logger
    """
    # Use environment config if level not provided
    if level is None:
        level = getattr(logging, config.LOG_LEVEL.upper(), logging.DEBUG)
    # Configure root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers to avoid duplicates
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Add a new handler
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    logging.info("Logging system initialized")

    return root_logger
