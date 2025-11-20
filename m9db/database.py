"""
m9db Database - Reporting Database Session Stubs

This module provides stub implementations of IT's reporting database session management.
For local development, SessionLocal returns a mock session that accepts all operations
but doesn't actually persist to a database.

All database operations are logged for debugging purposes.
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class MockSession:
    """
    Mock database session for local development.

    This session implements the same interface as IT's actual database session
    but logs operations instead of persisting to a database.
    """

    def __init__(self):
        """Initialize a mock database session."""
        self._objects: List[Any] = []
        self._committed = False
        self._closed = False
        logger.debug("MockSession created (local dev mode - no actual database)")

    def add(self, obj: Any) -> None:
        """
        Add an object to the session.

        In a real database session, this stages the object for insertion.
        In our stub, we just log it and keep a reference.

        Args:
            obj: Model instance to add
        """
        if self._closed:
            logger.warning("Attempted to add object to closed session")
            return

        self._objects.append(obj)
        obj_type = type(obj).__name__
        logger.info(f"Session.add(): Added {obj_type} to session (stub - not persisted)")

    def commit(self) -> None:
        """
        Commit the session.

        In a real database session, this persists all staged changes.
        In our stub, we just mark as committed and log.
        """
        if self._closed:
            logger.warning("Attempted to commit closed session")
            return

        self._committed = True
        logger.info(
            f"Session.commit(): Committed {len(self._objects)} objects "
            "(stub - not persisted to database)"
        )

    def refresh(self, obj: Any) -> None:
        """
        Refresh an object from the database.

        In a real database session, this reloads the object from the database.
        In our stub, this is a no-op.

        Args:
            obj: Model instance to refresh
        """
        if self._closed:
            logger.warning("Attempted to refresh object in closed session")
            return

        obj_type = type(obj).__name__
        logger.debug(f"Session.refresh(): Refreshed {obj_type} (stub - no-op)")

    def close(self) -> None:
        """
        Close the database session.

        In a real database session, this releases database connections.
        In our stub, we just mark as closed and log.
        """
        if self._closed:
            logger.debug("Session already closed")
            return

        self._closed = True
        logger.debug(
            f"Session.close(): Closed session with {len(self._objects)} objects "
            "(stub - no cleanup needed)"
        )

    def rollback(self) -> None:
        """
        Rollback the session.

        In a real database session, this reverts uncommitted changes.
        In our stub, we just log and clear objects.
        """
        if self._closed:
            logger.warning("Attempted to rollback closed session")
            return

        obj_count = len(self._objects)
        self._objects.clear()
        logger.info(f"Session.rollback(): Rolled back {obj_count} objects (stub)")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically close session."""
        if exc_type is not None:
            logger.error(f"Exception in session context: {exc_val}")
            self.rollback()
        self.close()
        return False  # Don't suppress exceptions


def SessionLocal() -> MockSession:
    """
    Create a new database session.

    For local development, this returns a mock session that implements
    the same interface as IT's actual database sessions but doesn't
    persist data.

    Returns:
        MockSession: A mock database session

    Example:
        >>> db = SessionLocal()
        >>> db.add(model_instance)
        >>> db.commit()
        >>> db.close()

        Or with context manager:
        >>> with SessionLocal() as db:
        ...     db.add(model_instance)
        ...     db.commit()
    """
    return MockSession()


__all__ = ["SessionLocal", "MockSession"]
