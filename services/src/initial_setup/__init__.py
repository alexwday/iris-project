# services/src/initial_setup/__init__.py
"""
Initial setup module for IRIS project.
Contains configuration for database, logging, OAuth and SSL.
"""

from ..initial_setup.db_config import check_tables_exist, connect_to_db
from ..initial_setup.logging_config import configure_logging

__all__ = ["configure_logging", "connect_to_db", "check_tables_exist"]
