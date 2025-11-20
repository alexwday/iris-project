from datetime import datetime, timezone
from m9db import models
from m9db.database import SessionLocal
from config.config import Config

class Reporting:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key == 'question':
                self.question = value
            if key == 'answer':
                self.answer = value
            if key == 'ai_generated':
                self.ai_generated = value
            if key == 'time_taken':
                self.time_taken = value
            if key == 'confidence':
                self.confidence = value
            if key == 'thumb':
                self.thumb = value
            if key == 'expectation':
                self.expectation = value
            if key == 'feedback':
                self.feedback = value
            if key == 'info':
                self.info = value

    def add_to_reporting_db(self):
        try:
            db = SessionLocal()
            report = models.REPORTING_FEEDBACK(
                app=Config().app_id,
                timestamp=datetime.now(timezone.utc),
                question=self.question,
                answer=self.answer,
                aigenerated=self.ai_generated,
                timetaken=self.time_taken,
                confidence=self.confidence,
                info=self.info
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            db.close()
        except Exception as e:
            print(e)

    def add_user_feedback_to_reporting_db(self):
        try:
            db = SessionLocal()
            report = models.FEEDBACK(
                app=APP_ID,
                timestamp=datetime.now(timezone.utc),
                question=self.question,
                answer=self.answer,
                expectation=self.expectation,
                feedback=self.feedback,
                thumb=self.thumb
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            db.close()
        except Exception as e:
            print(e)
