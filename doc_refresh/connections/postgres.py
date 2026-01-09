"""
PostgreSQL Database Connection Module for Document Refresh Pipeline.

Provides database access using psycopg2 with connection pooling.
Simplified version without SQLAlchemy dependency for standalone operation.

Functions:
    get_connection: Get a raw psycopg2 connection
    execute_query: Execute a query and return results
    execute_batch: Execute a batch of statements
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from ..utils.env_config import Config

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages database connection pooling."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    def _get_pool(self) -> pool.ThreadedConnectionPool:
        """Get or create the connection pool."""
        if self._pool is None:
            params = Config.get_db_params()
            logger.info(
                "Creating connection pool for database: %s on %s:%s",
                params["dbname"],
                params["host"],
                params["port"],
            )
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=params["host"],
                port=params["port"],
                dbname=params["dbname"],
                user=params["user"],
                password=params["password"],
            )
        return self._pool

    def get_connection(self) -> psycopg2.extensions.connection:
        """Get a connection from the pool."""
        return self._get_pool().getconn()

    def return_connection(self, conn: psycopg2.extensions.connection) -> None:
        """Return a connection to the pool."""
        if self._pool:
            self._pool.putconn(conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None


_connection_manager = ConnectionManager()


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for database connections.

    Provides automatic return to pool on completion.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                rows = cursor.fetchall()

    Yields:
        psycopg2 connection object.
    """
    conn = _connection_manager.get_connection()
    try:
        yield conn
    finally:
        _connection_manager.return_connection(conn)


@contextmanager
def get_cursor(
    dict_cursor: bool = False,
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """
    Context manager for database cursors with automatic commit/rollback.

    Args:
        dict_cursor: If True, use RealDictCursor for dict-like row access.

    Usage:
        with get_cursor(dict_cursor=True) as cursor:
            cursor.execute("SELECT * FROM table")
            rows = cursor.fetchall()  # Returns list of dicts

    Yields:
        psycopg2 cursor object.
    """
    conn = _connection_manager.get_connection()
    try:
        cursor_factory = RealDictCursor if dict_cursor else None
        with conn.cursor(cursor_factory=cursor_factory) as cursor:
            yield cursor
            conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        _connection_manager.return_connection(conn)


def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    dict_cursor: bool = False,
) -> List[Any]:
    """
    Execute a query and return all results.

    Args:
        query: SQL query string.
        params: Query parameters (tuple).
        dict_cursor: If True, return results as list of dicts.

    Returns:
        List of rows (tuples or dicts depending on dict_cursor).
    """
    with get_cursor(dict_cursor=dict_cursor) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def execute_one(
    query: str,
    params: Optional[Tuple] = None,
    dict_cursor: bool = False,
) -> Optional[Any]:
    """
    Execute a query and return the first result.

    Args:
        query: SQL query string.
        params: Query parameters (tuple).
        dict_cursor: If True, return result as dict.

    Returns:
        First row or None if no results.
    """
    with get_cursor(dict_cursor=dict_cursor) as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def execute_many(query: str, params_list: List[Tuple]) -> int:
    """
    Execute a query with multiple parameter sets.

    Args:
        query: SQL query string with placeholders.
        params_list: List of parameter tuples.

    Returns:
        Number of rows affected.
    """
    with get_cursor() as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount


def execute_batch_insert(
    table: str,
    columns: List[str],
    rows: List[Tuple],
    page_size: int = 1000,
) -> int:
    """
    Efficiently insert multiple rows using execute_values.

    Args:
        table: Target table name.
        columns: List of column names.
        rows: List of row tuples.
        page_size: Number of rows per batch.

    Returns:
        Number of rows inserted.
    """
    from psycopg2.extras import execute_values

    if not rows:
        return 0

    columns_str = ", ".join(columns)
    query = f"INSERT INTO {table} ({columns_str}) VALUES %s"

    total_inserted = 0
    with get_cursor() as cursor:
        for i in range(0, len(rows), page_size):
            batch = rows[i : i + page_size]
            execute_values(cursor, query, batch)
            total_inserted += len(batch)
            logger.debug("Inserted batch of %d rows into %s", len(batch), table)

    logger.info("Total rows inserted into %s: %d", table, total_inserted)
    return total_inserted


def close_connections() -> None:
    """Close all database connections."""
    _connection_manager.close_all()
    logger.info("All database connections closed")
