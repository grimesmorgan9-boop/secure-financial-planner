"""
models/review.py
-----------------
Stores the generated AI Monthly Review (Markdown text) for a closed
Month. One-to-one with Month.
"""

from datetime import datetime, timezone

from database import db


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    month_id = db.Column(db.Integer, db.ForeignKey("months.id"), nullable=False, unique=True)
    ai_report = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Review month={self.month_id}>"
