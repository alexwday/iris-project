"""Centralized logging configuration for the application."""

import logging
import sys
from typing import Optional

from .env_config import config


def configure_root_logger(level: Optional[int] = None) -> logging.Logger:
    """Configure the root logger with a stderr stream handler.

    Args:
        level (int | None): Log level to apply. When omitted, uses
            `config.LOG_LEVEL` or INFO as fallback.

    Returns:
        logging.Logger: Root logger after configuration.
    """
    level = (
        getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        if level is None
        else level
    )

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


# Backwards compatibility
def configure_logging(level: Optional[int] = None) -> logging.Logger:
    """Alias maintained for doc_refresh entrypoints."""
    return configure_root_logger(level)
