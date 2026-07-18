"""
models/category.py
-------------------
Categories are global (not per-user) and grouped into four types:
income, fixed, variable, and savings. Savings categories are stored
internally exactly like expenses (a Plan/Actual amount against a
Category) but the `group == "savings"` flag lets templates and
calculations display and total them separately, per the spec.
"""

from database import db

GROUP_INCOME = "income"
GROUP_FIXED = "fixed"
GROUP_VARIABLE = "variable"
GROUP_SAVINGS = "savings"

GROUP_LABELS = {
    GROUP_INCOME: "Income",
    GROUP_FIXED: "Fixed Expenses",
    GROUP_VARIABLE: "Variable Expenses",
    GROUP_SAVINGS: "Savings",
}

# The fixed seed list from the project specification. Order within each
# group is preserved so the UI lists categories in a sensible, stable order.
CATEGORY_SEED = {
    GROUP_INCOME: [
        "Salary", "Freelance", "Benefits", "Interest", "Other",
    ],
    GROUP_FIXED: [
        "Rent/Mortgage", "Council Tax", "Electricity", "Gas", "Water",
        "Internet", "Mobile", "Home Insurance", "Car Insurance",
        "Debt Payments", "Childcare", "TV Licence",
    ],
    GROUP_VARIABLE: [
        "Groceries", "Eating Out", "Fuel", "Public Transport",
        "Car Maintenance", "Health", "Personal Care", "Clothing",
        "Household", "Entertainment", "Hobbies", "Gifts",
        "Subscriptions", "Travel", "Miscellaneous",
    ],
    GROUP_SAVINGS: [
        "Emergency Fund", "Holiday Fund", "Home Maintenance",
        "Car Fund", "Big Purchases Fund",
    ],
}


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("name", "group", name="uq_category_name_group"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    group = db.Column(db.String(16), nullable=False)  # income/fixed/variable/savings

    plans = db.relationship("Plan", backref="category", lazy=True)
    actuals = db.relationship("Actual", backref="category", lazy=True)

    @property
    def is_income(self) -> bool:
        return self.group == GROUP_INCOME

    @property
    def is_savings(self) -> bool:
        return self.group == GROUP_SAVINGS

    @property
    def is_expense(self) -> bool:
        # Fixed and variable expenses count toward "expenses"; savings are
        # tracked separately even though stored the same way.
        return self.group in (GROUP_FIXED, GROUP_VARIABLE)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category {self.name} ({self.group})>"
