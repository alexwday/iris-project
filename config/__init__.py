"""
Compatibility layer for IT's config expectations.

This module provides a wrapper around the existing env_config to match
IT's expected config.config.Config interface without modifying the src code.
"""

from .config import Config

__all__ = ["Config"]
