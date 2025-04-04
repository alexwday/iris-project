"""
Initial setup module for IRIS project.
Contains configuration for database, logging, OAuth and SSL.
"""

from iris.src.initial_setup.db_config import check_tables_exist, connect_to_db
from iris.src.initial_setup.logging_config import configure_logging

__all__ = ["configure_logging", "connect_to_db", "check_tables_exist"]
