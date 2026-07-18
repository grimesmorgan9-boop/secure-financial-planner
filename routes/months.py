"""
routes/months.py
-----------------
Handles the core month lifecycle:
  - selecting/creating a month to plan
  - entering planned amounts per category ("Plan Month")
  - entering actual amounts per category ("Actual Month")
  - closing a month (locks further editing, ready for AI review)
  - history of all completed (locked) months

Authorization: every route that takes a month_id first loads the
Month and verifies `month.user_id == current_user.id`, returning 404
rather than 403 for months that belong to someone else, so we don't
leak which month IDs exist for other users.
"""

from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from database import db
from database.audit import log_event
from models import Month, Category, Plan, Actual
from forms.budget_forms import MonthSelectForm, CSRFOnlyForm, validate_amount
from services.finance import month_summary

months_bp = Blueprint("months", __name__, url_prefix="/months")


def _get_owned_month_or_404(month_id: int) -> Month:
    month = Month.query.get_or_404(month_id)
    if month.user_id != current_user.id:
        abort(404)
    return month


def _get_or_create_month(month_num: int, year: int) -> Month:
    month = Month.query.filter_by(
        user_id=current_user.id, month=month_num, year=year
    ).first()
    if month is None:
        month = Month(user_id=current_user.id, month=month_num, year=year)
        db.session.add(month)
        db.session.commit()
        log_event("month_created", user=current_user, extra=f"month={month.label}")
    return month


@months_bp.route("/select", methods=["GET", "POST"])
@login_required
def select_month():
    form = MonthSelectForm()
    if form.validate_on_submit():
        month = _get_or_create_month(form.month.data, form.year.data)
        return redirect(url_for("months.plan_month", month_id=month.id))
    return render_template("select_month.html", form=form)


@months_bp.route("/<int:month_id>/plan", methods=["GET", "POST"])
@login_required
def plan_month(month_id):
    month = _get_owned_month_or_404(month_id)
    categories = Category.query.order_by(Category.group, Category.id).all()
    csrf_form = CSRFOnlyForm()

    if request.method == "POST":
        if month.locked:
            flash("This month is closed and can no longer be edited.", "warning")
            return redirect(url_for("months.plan_month", month_id=month.id))

        if not csrf_form.validate_on_submit():
            flash("Your session expired or the form was invalid. Please try again.", "danger")
            return redirect(url_for("months.plan_month", month_id=month.id))

        existing = {p.category_id: p for p in month.plans}
        errors = []
        for cat in categories:
            field_name = f"amount_{cat.id}"
            raw = request.form.get(field_name, "0")
            try:
                amount = validate_amount(raw)
            except ValueError as exc:
                errors.append(f"{cat.name}: {exc}")
                continue

            if cat.id in existing:
                existing[cat.id].amount = amount
            else:
                db.session.add(Plan(month_id=month.id, category_id=cat.id, amount=amount))

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            db.session.commit()
            log_event("plan_updated", user=current_user, extra=f"month={month.label}")
            flash("Plan saved.", "success")
        return redirect(url_for("months.plan_month", month_id=month.id))

    summary = month_summary(month, categories)
    plan_map = {p.category_id: p.amount for p in month.plans}

    # "Copy Previous Month" support: find the previous calendar month for
    # this user, if one exists, so the template can offer a copy button.
    prev_month_num = 12 if month.month == 1 else month.month - 1
    prev_year = month.year - 1 if month.month == 1 else month.year
    previous_month = Month.query.filter_by(
        user_id=current_user.id, month=prev_month_num, year=prev_year
    ).first()

    return render_template(
        "month.html",
        mode="plan",
        month=month,
        categories=categories,
        planned=summary["planned"],
        plan_map=plan_map,
        previous_month=previous_month,
        csrf_form=csrf_form,
    )


@months_bp.route("/<int:month_id>/plan/copy-previous", methods=["POST"])
@login_required
def copy_previous_plan(month_id):
    month = _get_owned_month_or_404(month_id)
    if month.locked:
        flash("This month is closed and can no longer be edited.", "warning")
        return redirect(url_for("months.plan_month", month_id=month.id))

    prev_month_num = 12 if month.month == 1 else month.month - 1
    prev_year = month.year - 1 if month.month == 1 else month.year
    previous_month = Month.query.filter_by(
        user_id=current_user.id, month=prev_month_num, year=prev_year
    ).first()

    if previous_month is None:
        flash("No previous month found to copy from.", "warning")
        return redirect(url_for("months.plan_month", month_id=month.id))

    existing = {p.category_id: p for p in month.plans}
    for prev_plan in previous_month.plans:
        if prev_plan.category_id in existing:
            existing[prev_plan.category_id].amount = prev_plan.amount
        else:
            db.session.add(
                Plan(month_id=month.id, category_id=prev_plan.category_id, amount=prev_plan.amount)
            )
    db.session.commit()
    log_event("plan_copied", user=current_user, extra=f"from={previous_month.label} to={month.label}")
    flash(f"Copied plan from {previous_month.label}.", "success")
    return redirect(url_for("months.plan_month", month_id=month.id))


@months_bp.route("/<int:month_id>/actuals", methods=["GET", "POST"])
@login_required
def actual_month(month_id):
    month = _get_owned_month_or_404(month_id)
    categories = Category.query.order_by(Category.group, Category.id).all()
    csrf_form = CSRFOnlyForm()

    if request.method == "POST":
        if month.locked:
            flash("This month is closed and can no longer be edited.", "warning")
            return redirect(url_for("months.actual_month", month_id=month.id))

        if not csrf_form.validate_on_submit():
            flash("Your session expired or the form was invalid. Please try again.", "danger")
            return redirect(url_for("months.actual_month", month_id=month.id))

        existing = {a.category_id: a for a in month.actuals}
        errors = []
        for cat in categories:
            field_name = f"amount_{cat.id}"
            raw = request.form.get(field_name, "0")
            try:
                amount = validate_amount(raw)
            except ValueError as exc:
                errors.append(f"{cat.name}: {exc}")
                continue

            if cat.id in existing:
                existing[cat.id].amount = amount
            else:
                db.session.add(Actual(month_id=month.id, category_id=cat.id, amount=amount))

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            db.session.commit()
            log_event("actuals_updated", user=current_user, extra=f"month={month.label}")
            flash("Actuals saved.", "success")
        return redirect(url_for("months.actual_month", month_id=month.id))

    summary = month_summary(month, categories)
    actual_map = {a.category_id: a.amount for a in month.actuals}
    plan_map = {p.category_id: p.amount for p in month.plans}

    return render_template(
        "month.html",
        mode="actual",
        month=month,
        categories=categories,
        planned=summary["planned"],
        actual=summary["actual"],
        plan_map=plan_map,
        actual_map=actual_map,
        csrf_form=csrf_form,
    )


@months_bp.route("/<int:month_id>/close", methods=["POST"])
@login_required
def close_month(month_id):
    month = _get_owned_month_or_404(month_id)
    csrf_form = CSRFOnlyForm()

    if not csrf_form.validate_on_submit():
        flash("Your session expired. Please try again.", "danger")
        return redirect(url_for("months.actual_month", month_id=month.id))

    if month.locked:
        flash("This month is already closed.", "info")
    else:
        month.locked = True
        db.session.commit()
        log_event("month_closed", user=current_user, extra=f"month={month.label}")
        flash(f"{month.label} has been closed. You can now generate an AI review.", "success")

    return redirect(url_for("reviews.view_review", month_id=month.id))


@months_bp.route("/history")
@login_required
def history():
    completed = (
        Month.query.filter_by(user_id=current_user.id, locked=True)
        .order_by(Month.year.desc(), Month.month.desc())
        .all()
    )
    categories = Category.query.all()

    rows = []
    for month in completed:
        summary = month_summary(month, categories)
        overspend_count = sum(1 for line in summary["lines"] if line.variance < 0)
        rows.append(
            {
                "month": month,
                "net_after_savings": summary["actual"].net_after_savings,
                "overspend_count": overspend_count,
            }
        )

    return render_template("history.html", rows=rows)
