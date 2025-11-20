"""
PII Exception Module

This module provides a custom exception for PII (Personally Identifiable Information)
detection failures. It extends FastAPI's HTTPException to work seamlessly with
FastAPI's exception handling.

Usage:
    from classes.exceptions.pii_exception import PIIException

    raise PIIException(
        status_code=403,
        detail="PII detected in user input"
    )
"""

from fastapi import HTTPException
from typing import Any, Optional


class PIIException(HTTPException):
    """
    Exception raised when Personally Identifiable Information (PII) is detected.

    This exception is raised by IT's PII detection service when sensitive data
    is found in user input. It extends FastAPI's HTTPException to provide
    proper HTTP error responses.

    Attributes:
        status_code (int): HTTP status code (typically 403 Forbidden)
        detail (Any): Error message or detail object
        headers (Optional[dict]): Optional HTTP headers
    """

    def __init__(
        self,
        status_code: int = 403,
        detail: Any = "Personally Identifiable Information detected in request",
        headers: Optional[dict] = None,
    ):
        """
        Initialize the PIIException.

        Args:
            status_code: HTTP status code (default: 403 Forbidden)
            detail: Error message or detail object
            headers: Optional HTTP response headers
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)

    def __str__(self) -> str:
        """
        String representation of the exception.

        Returns:
            str: Formatted error message
        """
        return f"PIIException(status_code={self.status_code}, detail={self.detail})"

    def __repr__(self) -> str:
        """
        Developer-friendly representation of the exception.

        Returns:
            str: Detailed representation
        """
        return (
            f"PIIException(status_code={self.status_code}, "
            f"detail={self.detail!r}, headers={self.headers!r})"
        )
