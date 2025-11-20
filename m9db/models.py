"""
m9db Models - Reporting Database Model Stubs

This module provides stub implementations of IT's reporting database models.
For local development, these models accept all the same parameters as the
real models but don't persist to a database.

All operations are logged for debugging purposes.
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class REPORTING_FEEDBACK:
    """
    Stub model for IT's REPORTING_FEEDBACK table.

    This model captures query/answer interactions for analytics and compliance.

    Fields:
        app (str): Application identifier
        timestamp (datetime): When the interaction occurred
        question (str): User's question
        answer (str): AI-generated answer
        aigenerated (bool): Whether answer was AI-generated
        timetaken (float): Time taken to generate response
        confidence (float): Confidence score of the answer
        info (dict): Additional metadata
    """

    def __init__(
        self,
        app: str,
        timestamp: datetime,
        question: str,
        answer: str,
        aigenerated: bool,
        timetaken: float,
        confidence: float,
        info: Optional[dict] = None,
        **kwargs
    ):
        """
        Initialize a REPORTING_FEEDBACK record.

        Args:
            app: Application identifier
            timestamp: Timestamp of the interaction
            question: User's question
            answer: AI-generated answer
            aigenerated: Whether answer was AI-generated
            timetaken: Time taken to generate response (seconds)
            confidence: Confidence score (0-1)
            info: Additional metadata dictionary
            **kwargs: Additional fields for forward compatibility
        """
        self.app = app
        self.timestamp = timestamp
        self.question = question
        self.answer = answer
        self.aigenerated = aigenerated
        self.timetaken = timetaken
        self.confidence = confidence
        self.info = info or {}

        # Store any additional fields
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Log for local development debugging
        logger.debug(
            f"Created REPORTING_FEEDBACK: app={app}, "
            f"question_preview={question[:50]}..., "
            f"timetaken={timetaken:.2f}s"
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"REPORTING_FEEDBACK(app={self.app!r}, "
            f"timestamp={self.timestamp}, "
            f"question={self.question[:50]!r}...)"
        )


class FEEDBACK:
    """
    Stub model for IT's FEEDBACK table.

    This model captures user feedback (thumbs up/down, comments) for quality monitoring.

    Fields:
        app (str): Application identifier
        timestamp (datetime): When feedback was provided
        question (str): Original question
        answer (str): Answer that was provided
        expectation (str): What user expected
        feedback (str): User's detailed feedback
        thumb (str): Thumbs up/down indicator
    """

    def __init__(
        self,
        app: str,
        timestamp: datetime,
        question: str,
        answer: str,
        expectation: str,
        feedback: str,
        thumb: str,
        **kwargs
    ):
        """
        Initialize a FEEDBACK record.

        Args:
            app: Application identifier
            timestamp: Timestamp of the feedback
            question: Original question
            answer: Answer that was provided
            expectation: What the user expected
            feedback: User's detailed feedback text
            thumb: Thumbs indicator ("up" or "down")
            **kwargs: Additional fields for forward compatibility
        """
        self.app = app
        self.timestamp = timestamp
        self.question = question
        self.answer = answer
        self.expectation = expectation
        self.feedback = feedback
        self.thumb = thumb

        # Store any additional fields
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Log for local development debugging
        logger.debug(
            f"Created FEEDBACK: app={app}, "
            f"thumb={thumb}, "
            f"question_preview={question[:50]}..."
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"FEEDBACK(app={self.app!r}, "
            f"thumb={self.thumb!r}, "
            f"timestamp={self.timestamp})"
        )


# Additional models can be added here as needed
__all__ = ["REPORTING_FEEDBACK", "FEEDBACK"]
