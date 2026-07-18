"""
models/actual.py
-----------------
An Actual row stores the *actual* amount spent/received for one
category within one month, mirroring Plan.
"""

from database import db


class Actual(db.Model):
    __tablename__ = "actuals"
    __table_args__ = (
        db.UniqueConstraint("month_id", "category_id", name="uq_actual_month_category"),
    )

    id = db.Column(db.Integer, primary_key=True)
    month_id = db.Column(db.Integer, db.ForeignKey("months.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Actual month={self.month_id} category={self.category_id} amount={self.amount}>"
