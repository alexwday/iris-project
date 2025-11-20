"""
m9db - Reporting Database Compatibility Layer

This package provides stub implementations of IT's m9db ORM package.
For local development, these stubs allow the code to run without requiring
IT's reporting database infrastructure.

The stubs log all operations but don't actually persist data to a database.
This is sufficient for local development and testing.

Usage:
    from m9db import models
    from m9db.database import SessionLocal

    # Create a session
    db = SessionLocal()

    # Use models
    report = models.REPORTING_FEEDBACK(...)
    db.add(report)
    db.commit()
    db.close()
"""

from . import models
from . import database

__all__ = ["models", "database"]
