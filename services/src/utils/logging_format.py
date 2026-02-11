"""
Logging Format - Application-wide logging configuration.

This module configures Python's root logger for consistent log output across
all IRIS components. It sets up a stderr stream handler with colored output
for easy visual scanning during debugging. Called once during application
startup before any agents or database connections are initialized.

Log level defaults to the IRIS_LOG_LEVEL environment variable but can be
overridden programmatically.
"""

import logging
import sys

from .env_config import config


LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[1;31m",
}
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """Log formatter that adds ANSI colors keyed by log level."""

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = LEVEL_COLORS.get(level, "")

        timestamp = self.formatTime(record, "%H:%M:%S")

        name = record.name
        if name.startswith("services.src."):
            name = name[len("services.src."):]

        msg = record.getMessage()

        if level in ("WARNING", "ERROR", "CRITICAL"):
            return (
                f"{DIM}{timestamp}{RESET} "
                f"{color}{BOLD}{level:8s}{RESET} "
                f"{DIM}{name}{RESET} "
                f"{color}{msg}{RESET}"
            )

        return (
            f"{DIM}{timestamp}{RESET} "
            f"{color}{level:8s}{RESET} "
            f"{DIM}{name}{RESET} "
            f"{msg}"
        )


def configure_root_logger(level: int | None = None) -> logging.Logger:
    """Initialize the root logger with colored stderr output.

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
    handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    root_logger.info("Logging system initialized")
    return root_logger
