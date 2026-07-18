"""
services/finance.py
--------------------
Pure(ish) calculation helpers that turn a Month's Plan/Actual rows
into the aggregate figures the UI needs: planned/actual income,
expenses, savings, net, and per-category variance. Kept free of Flask
imports so it can be unit tested in isolation.
"""

from decimal import Decimal
from dataclasses import dataclass, field

from models.category import GROUP_INCOME, GROUP_SAVINGS, GROUP_FIXED, GROUP_VARIABLE


def _to_map(rows):
    """category_id -> Decimal amount, for a list of Plan or Actual rows."""
    return {row.category_id: Decimal(row.amount) for row in rows}


@dataclass
class Totals:
    income: Decimal = Decimal("0")
    expenses: Decimal = Decimal("0")
    savings: Decimal = Decimal("0")

    @property
    def net(self) -> Decimal:
        """Net balance before savings are set aside."""
        return self.income - self.expenses

    @property
    def net_after_savings(self) -> Decimal:
        """What's left once planned/actual savings contributions are removed."""
        return self.income - self.expenses - self.savings


@dataclass
class CategoryLine:
    category_id: int
    name: str
    group: str
    planned: Decimal
    actual: Decimal

    @property
    def variance(self) -> Decimal:
        """Positive = under planned amount (good) for expenses/savings;
        for income, positive variance means you earned more than planned."""
        return self.planned - self.actual


def compute_totals(categories, amount_map) -> Totals:
    """Sum amounts (either plan or actual) into income/expenses/savings buckets."""
    t = Totals()
    for cat in categories:
        amount = amount_map.get(cat.id, Decimal("0"))
        if cat.group == GROUP_INCOME:
            t.income += amount
        elif cat.group == GROUP_SAVINGS:
            t.savings += amount
        elif cat.group in (GROUP_FIXED, GROUP_VARIABLE):
            t.expenses += amount
    return t


def build_category_lines(categories, plan_map, actual_map):
    """One CategoryLine per category, for the plan-vs-actual comparison table."""
    lines = []
    for cat in categories:
        lines.append(
            CategoryLine(
                category_id=cat.id,
                name=cat.name,
                group=cat.group,
                planned=plan_map.get(cat.id, Decimal("0")),
                actual=actual_map.get(cat.id, Decimal("0")),
            )
        )
    return lines


def month_summary(month, categories):
    """Build the full set of figures used by the dashboard/plan/actual/review pages.

    Returns a dict with: planned Totals, actual Totals, and the list of
    per-category comparison lines.
    """
    plan_map = _to_map(month.plans)
    actual_map = _to_map(month.actuals)

    planned = compute_totals(categories, plan_map)
    actual = compute_totals(categories, actual_map)
    lines = build_category_lines(categories, plan_map, actual_map)

    return {
        "planned": planned,
        "actual": actual,
        "lines": lines,
    }


def biggest_variances(lines, expense_only=True):
    """Return (biggest_overspend, biggest_underspend) CategoryLine objects.

    Overspend = actual exceeded planned (variance is negative).
    Underspend = actual came in under planned (variance is positive).
    Only considers expense categories (fixed + variable) by default,
    since "overspend" isn't a meaningful concept for income.
    """
    candidates = [
        line for line in lines
        if (not expense_only or line.group in (GROUP_FIXED, GROUP_VARIABLE))
    ]
    if not candidates:
        return None, None

    overspend = min(candidates, key=lambda l: l.variance, default=None)
    underspend = max(candidates, key=lambda l: l.variance, default=None)

    # Only report genuine over/under spends (non-zero variance).
    if overspend and overspend.variance >= 0:
        overspend = None
    if underspend and underspend.variance <= 0:
        underspend = None

    return overspend, underspend
