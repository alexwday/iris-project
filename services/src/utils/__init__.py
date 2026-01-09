# services/src/utils/__init__.py
"""
Utilities module for IRIS project.
Contains configuration for logging, SSL, environment settings, and conversation processing.
Database and OAuth connections are in services.src.connections.
"""

from .logging_format import configure_logging

__all__ = ["configure_logging"]
