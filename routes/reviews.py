"""
routes/reviews.py
------------------
Displays the Monthly Review page (planned vs actual cards, variance
table, biggest over/underspend) and lets the user trigger AI Monthly
Review generation once a month is closed.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user

from database import db
from database.audit import log_event
from models import Month, Category, Review
from forms.budget_forms import CSRFOnlyForm
from services.finance import month_summary, biggest_variances
from services.ai_review import generate_review

reviews_bp = Blueprint("reviews", __name__, url_prefix="/months")


def _get_owned_month_or_404(month_id: int) -> Month:
    month = Month.query.get_or_404(month_id)
    if month.user_id != current_user.id:
        abort(404)
    return month


@reviews_bp.route("/<int:month_id>/review")
@login_required
def view_review(month_id):
    month = _get_owned_month_or_404(month_id)
    categories = Category.query.order_by(Category.group, Category.id).all()
    summary = month_summary(month, categories)
    overspend, underspend = biggest_variances(summary["lines"])
    csrf_form = CSRFOnlyForm()

    return render_template(
        "review.html",
        month=month,
        planned=summary["planned"],
        actual=summary["actual"],
        lines=summary["lines"],
        overspend=overspend,
        underspend=underspend,
        review=month.review,
        csrf_form=csrf_form,
    )


@reviews_bp.route("/<int:month_id>/review/generate", methods=["POST"])
@login_required
def generate_review_route(month_id):
    month = _get_owned_month_or_404(month_id)
    csrf_form = CSRFOnlyForm()

    if not csrf_form.validate_on_submit():
        flash("Your session expired. Please try again.", "danger")
        return redirect(url_for("reviews.view_review", month_id=month.id))

    if not month.locked:
        flash("Close the month before generating an AI review.", "warning")
        return redirect(url_for("months.actual_month", month_id=month.id))

    categories = Category.query.all()
    summary = month_summary(month, categories)
    report_text = generate_review(
        month,
        summary,
        api_key=current_app.config.get("ANTHROPIC_API_KEY"),
        model=current_app.config.get("ANTHROPIC_MODEL"),
    )

    if month.review:
        month.review.ai_report = report_text
    else:
        db.session.add(Review(month_id=month.id, ai_report=report_text))
    db.session.commit()
    log_event("ai_review_generated", user=current_user, extra=f"month={month.label}")
    flash("AI Monthly Review generated.", "success")
    return redirect(url_for("reviews.view_review", month_id=month.id))
