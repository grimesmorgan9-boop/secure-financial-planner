"""
models/plan.py
---------------
A Plan row stores the *planned* amount for one category within one
month. Amounts are stored as non-negative decimals (application-level
validation enforces this in the WTForms layer / API).
"""

from database import db


class Plan(db.Model):
    __tablename__ = "plans"
    __table_args__ = (
        db.UniqueConstraint("month_id", "category_id", name="uq_plan_month_category"),
    )

    id = db.Column(db.Integer, primary_key=True)
    month_id = db.Column(db.Integer, db.ForeignKey("months.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Plan month={self.month_id} category={self.category_id} amount={self.amount}>"
