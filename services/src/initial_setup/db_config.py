# services/src/initial_setup/db_config.py
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


# def build_postgres_uri(app_config):
#     """
#     Build a PostgreSQL connection URI from config properties (no port/dbname).
#     """

#     user = app_config.get('user')
#     password = app_config.get('password')
#     host = app_config.get('host')

#     logger.info(f"Connecting to DB with user: {user}, host: {host}")

#     return f"postgresql://{user}:{password}@{host}"

def construct_dsn(params: dict, for_sqlalchemy=True):
    hosts = params.get('host')
    if not hosts:
        raise ValueError("Host is not set or is empty.")

    hosts = hosts.split(',')
    port = params.get('port')
    database = params.get('dbname')
    user = params.get('user')
    password = params.get('password')

    logger.info(f"Using database: {database}")
    #logger.info(f"Using user: {user}")
    logger.info(f"Using host(s): {hosts}")
    logger.info(f"Using port(s): {port}")

    if ',' in port:
        ports = port.split(',')
        if len(ports) != len(hosts):
            raise ValueError("The number of ports must match the number of hosts.")
    else:
        ports = [port] * len(hosts)

    host_port_pairs = [f"{host}:{port}" for host, port in zip(hosts, ports)]

    if for_sqlalchemy:
        primary_host_port = host_port_pairs[0]
        dsn = (
            f"postgresql+psycopg2://{user}:{password}@{primary_host_port}/{database}?"
            f"sslmode=require&target_session_attrs=read-write"
        )
    else:
        dsn = (
            f"dbname='{database}' user='{user}' password='{password}' "
            f"host='{','.join(hosts)}' port='{port}' sslmode='require' "
            f"target_session_attrs='read-write'"
        )

    #logger.info(f"Constructed DSN: {dsn}")
    return dsn


def connect_to_db(env: str = "rbc") -> Optional[psycopg2.extensions.connection]:
    """
    Connect to the PostgreSQL database using configuration parameters.

    Args:
        env (str): Environment identifier (default: "rbc")

    Returns:
        Optional[psycopg2.extensions.connection]: Database connection or None if failed

    Raises:
        Exception: If database connection fails
    """
    params = get_db_params()
    dsn = construct_dsn(params, for_sqlalchemy=False)
    hosts = params.get('host', '').split(',')
    port = params.get('port', '')
    logger.info(f"Attempting connection to hosts: {hosts} on port(s): {port}")
    #uri = build_postgres_uri(params)
    try:
        logger.debug("Attempting database connection")
        conn = psycopg2.connect(dsn)
        logger.info(f"Connected to DB host: {conn.info.host} on port: {conn.info.port} (selected for read-write)")
        conn.autocommit = False

        logger.debug("Database connection successful")
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
    # with conn.cursor() as cur:
    #     cur.execute(
    #         """
    #         SELECT table_name
    #         FROM information_schema.tables
    #         WHERE table_schema = 'public'
    #         AND table_name IN ('apg_catalog', 'apg_content')
    #     """
    #     )
    #     tables = [row[0] for row in cur.fetchall()]
    # return tables
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('apg_catalog', 'apg_content')
            """
        )
        tables = [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error checking tables: {e}", exc_info=True)
    finally:
        if cur is not None:
            cur.close()
    return tables

