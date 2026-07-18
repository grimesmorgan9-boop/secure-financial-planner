"""
routes/dashboard.py
--------------------
Landing page after login. Shows the current calendar month's figures
(creating the Month record on first visit if it doesn't exist yet)
plus quick links into planning/actuals/history.
"""

from datetime import date

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from database import db
from models import Month, Category
from services.finance import month_summary

dashboard_bp = Blueprint("dashboard", __name__)


def get_or_create_current_month():
    today = date.today()
    month = Month.query.filter_by(
        user_id=current_user.id, month=today.month, year=today.year
    ).first()
    if month is None:
        month = Month(user_id=current_user.id, month=today.month, year=today.year)
        db.session.add(month)
        db.session.commit()
    return month


@dashboard_bp.route("/")
@login_required
def index():
    month = get_or_create_current_month()
    categories = Category.query.all()
    summary = month_summary(month, categories)

    return render_template(
        "dashboard.html",
        month=month,
        categories=categories,
        planned=summary["planned"],
        actual=summary["actual"],
        lines=summary["lines"],
    )


@dashboard_bp.route("/months/current")
@login_required
def current_month_redirect():
    month = get_or_create_current_month()
    return redirect(url_for("months.plan_month", month_id=month.id))
