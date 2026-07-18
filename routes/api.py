"""
routes/api.py
--------------
JSON REST API mirroring the core month workflow, for programmatic /
JavaScript (Chart.js dashboard, future SPA/mobile client) access.

  PUT  /api/months/<id>/plan
  PUT  /api/months/<id>/actuals
  POST /api/months/<id>/close
  GET  /api/months/<id>/review
  POST /api/months/<id>/ai-report/generate

Auth: these endpoints rely on the existing Flask-Login session cookie
(login_required), the same as the HTML routes - there is no separate
token scheme in this build. Because state-changing requests here are
JSON (not a plain HTML form), Flask-WTF's per-form CSRF token doesn't
apply automatically; instead callers must send the current session's
CSRF token in the `X-CSRFToken` header, which is validated manually
below via `validate_csrf`. This keeps the same-origin protection CSRF
tokens provide without needing a template form per API call.
"""

from flask import Blueprint, jsonify, request, current_app, abort
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf
from wtforms import ValidationError

from database import db
from database.audit import log_event
from models import Month, Category, Plan, Actual, Review
from forms.budget_forms import validate_amount
from services.finance import month_summary, biggest_variances
from services.ai_review import generate_review

api_bp = Blueprint("api", __name__, url_prefix="/api/months")


def _get_owned_month_or_404(month_id: int) -> Month:
    month = Month.query.get_or_404(month_id)
    if month.user_id != current_user.id:
        abort(404)
    return month


def _check_csrf():
    token = request.headers.get("X-CSRFToken")
    try:
        validate_csrf(token)
    except ValidationError:
        abort(400, description="Missing or invalid CSRF token (X-CSRFToken header).")


def _totals_json(totals):
    return {
        "income": float(totals.income),
        "expenses": float(totals.expenses),
        "savings": float(totals.savings),
        "net": float(totals.net),
        "net_after_savings": float(totals.net_after_savings),
    }


@api_bp.route("/<int:month_id>/plan", methods=["PUT"])
@login_required
def put_plan(month_id):
    _check_csrf()
    month = _get_owned_month_or_404(month_id)
    if month.locked:
        return jsonify({"error": "Month is closed and cannot be edited."}), 409

    payload = request.get_json(silent=True) or {}
    entries = payload.get("entries", [])  # [{category_id, amount}, ...]
    if not isinstance(entries, list):
        return jsonify({"error": "entries must be a list."}), 400

    existing = {p.category_id: p for p in month.plans}
    valid_category_ids = {c.id for c in Category.query.all()}

    for entry in entries:
        category_id = entry.get("category_id")
        if category_id not in valid_category_ids:
            return jsonify({"error": f"Unknown category_id {category_id}."}), 400
        try:
            amount = validate_amount(entry.get("amount"))
        except ValueError as exc:
            return jsonify({"error": f"category_id {category_id}: {exc}"}), 400

        if category_id in existing:
            existing[category_id].amount = amount
        else:
            db.session.add(Plan(month_id=month.id, category_id=category_id, amount=amount))

    db.session.commit()
    log_event("api_plan_updated", user=current_user, extra=f"month={month.label}")

    categories = Category.query.all()
    summary = month_summary(month, categories)
    return jsonify({"month_id": month.id, "planned": _totals_json(summary["planned"])})


@api_bp.route("/<int:month_id>/actuals", methods=["PUT"])
@login_required
def put_actuals(month_id):
    _check_csrf()
    month = _get_owned_month_or_404(month_id)
    if month.locked:
        return jsonify({"error": "Month is closed and cannot be edited."}), 409

    payload = request.get_json(silent=True) or {}
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return jsonify({"error": "entries must be a list."}), 400

    existing = {a.category_id: a for a in month.actuals}
    valid_category_ids = {c.id for c in Category.query.all()}

    for entry in entries:
        category_id = entry.get("category_id")
        if category_id not in valid_category_ids:
            return jsonify({"error": f"Unknown category_id {category_id}."}), 400
        try:
            amount = validate_amount(entry.get("amount"))
        except ValueError as exc:
            return jsonify({"error": f"category_id {category_id}: {exc}"}), 400

        if category_id in existing:
            existing[category_id].amount = amount
        else:
            db.session.add(Actual(month_id=month.id, category_id=category_id, amount=amount))

    db.session.commit()
    log_event("api_actuals_updated", user=current_user, extra=f"month={month.label}")

    categories = Category.query.all()
    summary = month_summary(month, categories)
    return jsonify({"month_id": month.id, "actual": _totals_json(summary["actual"])})


@api_bp.route("/<int:month_id>/close", methods=["POST"])
@login_required
def close_month(month_id):
    _check_csrf()
    month = _get_owned_month_or_404(month_id)
    if not month.locked:
        month.locked = True
        db.session.commit()
        log_event("api_month_closed", user=current_user, extra=f"month={month.label}")

    return jsonify({"month_id": month.id, "locked": month.locked})


@api_bp.route("/<int:month_id>/review", methods=["GET"])
@login_required
def get_review(month_id):
    month = _get_owned_month_or_404(month_id)
    categories = Category.query.all()
    summary = month_summary(month, categories)
    overspend, underspend = biggest_variances(summary["lines"])

    return jsonify(
        {
            "month_id": month.id,
            "label": month.label,
            "locked": month.locked,
            "planned": _totals_json(summary["planned"]),
            "actual": _totals_json(summary["actual"]),
            "biggest_overspend": overspend.name if overspend else None,
            "biggest_underspend": underspend.name if underspend else None,
            "ai_report": month.review.ai_report if month.review else None,
        }
    )


@api_bp.route("/<int:month_id>/ai-report/generate", methods=["POST"])
@login_required
def generate_ai_report(month_id):
    _check_csrf()
    month = _get_owned_month_or_404(month_id)
    if not month.locked:
        return jsonify({"error": "Close the month before generating an AI review."}), 409

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
    log_event("api_ai_review_generated", user=current_user, extra=f"month={month.label}")

    return jsonify({"month_id": month.id, "ai_report": report_text})
