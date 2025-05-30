"""
Database configuration for RBC environment.
All database parameters are loaded from environment variables.
"""

from typing import Any, Dict, Optional
import logging
import psycopg2
import psycopg2.extras
import uuid
from iris.src.initial_setup.env_config import config

# Register UUID adapter
psycopg2.extras.register_uuid()

# Get logger
logger = logging.getLogger(__name__)


def get_db_params() -> Dict[str, Any]:
    """
    Get database connection parameters from environment configuration.

    Returns:
        Dictionary with database connection parameters
    """
    logger.debug("Getting database parameters from environment configuration")
    return config.get_db_params()


def connect_to_db() -> Optional[psycopg2.extensions.connection]:
    """
    Connect to the PostgreSQL database.

    Returns:
        Database connection object or None if connection fails
    """
    db_params = get_db_params()
    try:
        logger.info(f"Connecting to database with parameters: host={db_params['host']}, " +
                   f"port={db_params['port']}, dbname={db_params['dbname']}, user={db_params['user']}")
        conn = psycopg2.connect(**db_params)
        conn.autocommit = False
        logger.info("Database connection successful")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}", exc_info=True)
        return None


def check_tables_exist(conn: psycopg2.extensions.connection) -> list:
    """
    Check if the required tables exist in the database.

    Args:
        conn: Database connection object

    Returns:
        List of existing table names
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('apg_catalog', 'apg_content')
        """
        )
        tables = [row[0] for row in cur.fetchall()]
    return tables
