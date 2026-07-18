"""
tests/test_models.py
---------------------
Covers model relationships, category seeding, and the finance
calculation service (totals/variance).
"""

from decimal import Decimal

from models import User, Month, Category, Plan, Actual, seed_categories
from models.category import CATEGORY_SEED
from services.finance import month_summary, biggest_variances


def test_seed_categories_creates_expected_count(app, db):
    seed_categories()
    total_expected = sum(len(v) for v in CATEGORY_SEED.values())
    assert Category.query.count() == total_expected


def test_seed_categories_is_idempotent(app, db):
    seed_categories()
    seed_categories()
    total_expected = sum(len(v) for v in CATEGORY_SEED.values())
    assert Category.query.count() == total_expected


def test_month_unique_constraint_per_user(app, db):
    user = User(username="bob", email="bob@example.com")
    user.set_password("Sup3rSecret!")
    db.session.add(user)
    db.session.commit()

    db.session.add(Month(user_id=user.id, month=1, year=2026))
    db.session.commit()

    db.session.add(Month(user_id=user.id, month=1, year=2026))
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_month_summary_computes_totals(app, db):
    seed_categories()
    user = User(username="carol", email="carol@example.com")
    user.set_password("Sup3rSecret!")
    db.session.add(user)
    db.session.commit()

    month = Month(user_id=user.id, month=3, year=2026)
    db.session.add(month)
    db.session.commit()

    salary = Category.query.filter_by(name="Salary").first()
    groceries = Category.query.filter_by(name="Groceries").first()
    emergency = Category.query.filter_by(name="Emergency Fund").first()

    db.session.add_all([
        Plan(month_id=month.id, category_id=salary.id, amount=Decimal("3000.00")),
        Plan(month_id=month.id, category_id=groceries.id, amount=Decimal("400.00")),
        Plan(month_id=month.id, category_id=emergency.id, amount=Decimal("200.00")),
        Actual(month_id=month.id, category_id=salary.id, amount=Decimal("3000.00")),
        Actual(month_id=month.id, category_id=groceries.id, amount=Decimal("450.00")),
        Actual(month_id=month.id, category_id=emergency.id, amount=Decimal("150.00")),
    ])
    db.session.commit()

    categories = Category.query.all()
    summary = month_summary(month, categories)

    assert summary["planned"].income == Decimal("3000.00")
    assert summary["planned"].expenses == Decimal("400.00")
    assert summary["planned"].savings == Decimal("200.00")
    assert summary["actual"].expenses == Decimal("450.00")
    assert summary["actual"].savings == Decimal("150.00")

    overspend, underspend = biggest_variances(summary["lines"])
    assert overspend.name == "Groceries"
