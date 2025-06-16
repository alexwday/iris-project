"""
Database configuration for RBC environment.
All database parameters are loaded from environment variables.
"""

from typing import Any, Dict, Optional
import logging
import psycopg2
import psycopg2.extras
from ..initial_setup.env_config import config

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


def build_postgres_uri(app_config):
    """
    Build a PostgreSQL connection URI from config properties (no port/dbname).
    """
    user = app_config.get('user')
    password = app_config.get('password')
    host = app_config.get('host')
    return f"postgresql://{user}:{password}@{host}"


def connect_to_db(env: str = "rbc") -> Optional[psycopg2.extensions.connection]:
    """
    Connect to the PostgreSQL database using a URI without port/dbname.
    """
    params = get_db_params()
    uri = build_postgres_uri(params)
    try:
        logger.info(f"Connecting to database with URI:")
        conn = psycopg2.connect(dsn=uri)
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
