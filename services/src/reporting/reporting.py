"""
Reporting Module.

Provides functionality for storing conversation reports and user feedback
to the reporting database.

Classes:
    Reporting: Handles report and feedback storage
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from config.config import Config
from m9db import models
from m9db.database import SessionLocal

logger = logging.getLogger(__name__)


class Reporting:
    """Handles storing reports and feedback to the database."""

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize a Reporting instance.

        Args:
            **kwargs: Report/feedback fields including question, answer,
                ai_generated, time_taken, confidence, thumb, expectation,
                feedback, info.
        """
        self._data: Dict[str, Any] = kwargs

    def add_to_reporting_db(self) -> None:
        """
        Add conversation report to the reporting database.

        Stores question, answer, timing, and confidence information.
        """
        db = None
        try:
            db = SessionLocal()
            report = models.REPORTING_FEEDBACK(
                app=Config().app_id,
                timestamp=datetime.now(timezone.utc),
                question=self._data.get("question", ""),
                answer=self._data.get("answer", ""),
                aigenerated=self._data.get("ai_generated"),
                timetaken=self._data.get("time_taken"),
                confidence=self._data.get("confidence"),
                info=self._data.get("info"),
            )
            db.add(report)
            db.commit()
            db.refresh(report)
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
            logger.error("Failed to add report to database: %s", exc)
        finally:
            if db is not None:
                db.close()

    def add_user_feedback_to_reporting_db(self) -> None:
        """
        Add user feedback to the reporting database.

        Stores user's thumbs rating, expectation, and feedback text.
        """
        db = None
        try:
            db = SessionLocal()
            report = models.FEEDBACK(
                app=Config().app_id,
                timestamp=datetime.now(timezone.utc),
                question=self._data.get("question", ""),
                answer=self._data.get("answer", ""),
                expectation=self._data.get("expectation"),
                feedback=self._data.get("feedback"),
                thumb=self._data.get("thumb"),
            )
            db.add(report)
            db.commit()
            db.refresh(report)
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
            logger.error("Failed to add user feedback to database: %s", exc)
        finally:
            if db is not None:
                db.close()
