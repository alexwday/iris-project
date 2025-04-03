"""
Database configuration for local development and production environments.
"""
import psycopg2
from typing import Dict, Any, Optional


# Local development database parameters
LOCAL_DB_PARAMS = {
    'host': "localhost",
    'port': "5432",
    'dbname': "maven-finance",
    'user': "iris_dev",
    'password': ""  # No password needed for local development
}

# Production database parameters will be set in the RBC environment
# This is just a placeholder - these values will be replaced in production
PROD_DB_PARAMS = {
    'host': "x",
    'port': "x",
    'dbname': "maven-finance",
    'user': "x",
    'password': "x"
}


def get_db_params(env: str = "local") -> Dict[str, Any]:
    """
    Get database connection parameters based on environment.
    
    Args:
        env: Environment type ("local" or "prod")
        
    Returns:
        Dictionary with database connection parameters
    """
    if env.lower() == "prod":
        return PROD_DB_PARAMS
    return LOCAL_DB_PARAMS


def connect_to_db(env: str = "local") -> Optional[psycopg2.extensions.connection]:
    """
    Connect to the PostgreSQL database.
    
    Args:
        env: Environment type ("local" or "prod")
        
    Returns:
        Database connection object or None if connection fails
    """
    db_params = get_db_params(env)
    try:
        # Connect silently without printing messages
        conn = psycopg2.connect(**db_params)
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
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
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('apg_catalog', 'apg_content')
        """)
        tables = [row[0] for row in cur.fetchall()]
    return tables