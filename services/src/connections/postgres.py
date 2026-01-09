"""
PostgreSQL Database Connection Module.

Provides SQLAlchemy-based database access with connection pooling.
All database parameters are loaded from environment variables.

Functions:
    get_session: Context manager for database sessions (main interface)
    get_engine: Direct engine access for advanced use cases
    construct_dsn: Build database connection string from parameters
"""

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from ..utils.env_config import config

logger = logging.getLogger(__name__)


class _ConnectionManager:
    """Manages singleton database connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self._engine: Optional[Engine] = None
        self._factory: Optional[Callable[[], Session]] = None

    def get_engine(self) -> Engine:
        """Get or create the SQLAlchemy engine."""
        if self._engine is None:
            params = _get_db_params()
            dsn = construct_dsn(params)
            logger.info("Creating SQLAlchemy engine with connection pooling")
            self._engine = create_engine(
                dsn,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )
        return self._engine

    def get_session_factory(self) -> Callable[[], Session]:
        """Get or create the session factory."""
        if self._factory is None:
            engine = self.get_engine()
            self._factory = sessionmaker(bind=engine, expire_on_commit=False)
        return self._factory


_connection_manager = _ConnectionManager()


def _get_db_params() -> Dict[str, Any]:
    """
    Get database connection parameters from environment configuration.

    Returns:
        Dictionary with database connection parameters.
    """
    logger.debug("Getting database parameters from environment configuration")
    return config.get_db_params()


def construct_dsn(params: Dict[str, Any]) -> str:
    """
    Construct SQLAlchemy DSN from database parameters.

    This function can be patched for local development to disable SSL.

    Args:
        params: Database connection parameters.

    Returns:
        SQLAlchemy connection string.

    Raises:
        ValueError: If host is not set or port/host count mismatch.
    """
    hosts = params.get("host")
    if not hosts:
        raise ValueError("Host is not set or is empty.")

    hosts = hosts.split(",")
    port = params.get("port")
    database = params.get("dbname")
    user = params.get("user")
    password = params.get("password")

    logger.info("Using database: %s", database)
    logger.info("Using host(s): %s", hosts)
    logger.info("Using port(s): %s", port)

    if "," in str(port):
        ports = port.split(",")
        if len(ports) != len(hosts):
            raise ValueError("The number of ports must match the number of hosts.")
    else:
        ports = [port] * len(hosts)

    primary_host_port = f"{hosts[0]}:{ports[0]}"
    dsn = (
        f"postgresql+psycopg2://{user}:{password}@{primary_host_port}/{database}?"
        f"sslmode=require&target_session_attrs=read-write"
    )

    return dsn


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for SQLAlchemy database sessions.

    Provides automatic commit on success and rollback on error.

    Usage:
        with get_session() as session:
            result = session.execute(text("SELECT * FROM table"))
            rows = result.mappings().all()

    Yields:
        SQLAlchemy session object.
    """
    factory = _connection_manager.get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except (ValueError, TypeError, KeyError, RuntimeError) as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine for direct access.

    Use this only when you need direct engine access (e.g., for pd.read_sql).
    For most operations, use get_session() context manager instead.

    Returns:
        SQLAlchemy engine object.
    """
    return _connection_manager.get_engine()
