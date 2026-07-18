"""
models package
---------------
Aggregates all SQLAlchemy models so the rest of the app can simply do
`from models import User, Month, Category, Plan, Actual, Review`.
Also exposes `seed_categories()` used at startup / in tests to ensure
the fixed category list from the spec always exists.
"""

from models.user import User
from models.month import Month
from models.category import Category, CATEGORY_SEED
from models.plan import Plan
from models.actual import Actual
from models.review import Review
from database import db

__all__ = [
    "User",
    "Month",
    "Category",
    "Plan",
    "Actual",
    "Review",
    "seed_categories",
]


def seed_categories() -> None:
    """Idempotently ensure every category in CATEGORY_SEED exists.

    Safe to call on every app startup: existing categories (matched by
    name + group) are left untouched, missing ones are inserted.
    """
    existing = {(c.name, c.group) for c in Category.query.all()}
    changed = False
    for group, names in CATEGORY_SEED.items():
        for name in names:
            if (name, group) not in existing:
                db.session.add(Category(name=name, group=group))
                changed = True
    if changed:
        db.session.commit()
