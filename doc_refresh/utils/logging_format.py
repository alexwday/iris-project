"""Centralized logging configuration for the application."""

import logging
import sys

from .env_config import config


def configure_root_logger(level: int | None = None) -> logging.Logger:
    """Configure the root logger with a stderr stream handler."""
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


# Backward compatibility alias
def configure_logging(level: int | None = None) -> logging.Logger:
    """Alias for configure_root_logger."""
    return configure_root_logger(level)
