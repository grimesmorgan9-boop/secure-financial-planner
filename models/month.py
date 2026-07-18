"""
models/month.py
----------------
A Month represents one calendar month's financial plan for a given
user. Locking (`locked=True`) happens when the user closes the month
after entering actuals, which freezes Plan/Actual editing and allows
an AI review to be generated against a stable snapshot.
"""

from datetime import datetime, timezone

from database import db


class Month(db.Model):
    __tablename__ = "months"
    __table_args__ = (
        db.UniqueConstraint("user_id", "month", "year", name="uq_user_month_year"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    plans = db.relationship("Plan", backref="month", lazy=True, cascade="all, delete-orphan")
    actuals = db.relationship("Actual", backref="month", lazy=True, cascade="all, delete-orphan")
    review = db.relationship(
        "Review", backref="month", uselist=False, cascade="all, delete-orphan"
    )

    MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    @property
    def label(self) -> str:
        return f"{self.MONTH_NAMES[self.month - 1]} {self.year}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Month {self.label} user={self.user_id}>"
