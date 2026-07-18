"""
services/ai_review.py
----------------------
Generates the AI Monthly Review shown after a month is closed.

Design/security notes:
- Only AGGREGATED monthly totals and per-category variances are ever
  sent to the AI provider - never raw line-item descriptions, dates,
  or anything that could resemble a full transaction history. This
  keeps the payload small and avoids exposing more personal spending
  detail than necessary for a summary.
- If ANTHROPIC_API_KEY is not configured (the default for local /
  portfolio use), a deterministic, rule-based Markdown summary is
  generated locally instead. This means the app is fully functional
  and demoable with zero external dependencies or API keys, while
  still being architected to call a real model when a key is present.
"""

from decimal import Decimal
import json
import logging

import requests

from services.finance import biggest_variances

logger = logging.getLogger("budget_planner.ai_review")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


def _fmt(amount: Decimal) -> str:
    return f"£{amount:,.2f}"


def _build_aggregate_payload(month, summary):
    """Build the small, aggregated-only JSON payload sent to the AI."""
    planned = summary["planned"]
    actual = summary["actual"]
    lines = summary["lines"]

    return {
        "month": month.label,
        "planned": {
            "income": float(planned.income),
            "expenses": float(planned.expenses),
            "savings": float(planned.savings),
            "net": float(planned.net),
            "net_after_savings": float(planned.net_after_savings),
        },
        "actual": {
            "income": float(actual.income),
            "expenses": float(actual.expenses),
            "savings": float(actual.savings),
            "net": float(actual.net),
            "net_after_savings": float(actual.net_after_savings),
        },
        "categories": [
            {
                "name": line.name,
                "group": line.group,
                "planned": float(line.planned),
                "actual": float(line.actual),
                "variance": float(line.variance),
            }
            for line in lines
            if line.planned != 0 or line.actual != 0
        ],
    }


SYSTEM_PROMPT = (
    "You are a careful, encouraging personal finance assistant. You will "
    "receive ONLY aggregated monthly budget totals and per-category "
    "variances for a single household - never raw transactions. Write a "
    "concise Markdown monthly review covering: Overall performance, "
    "Largest overspends, Largest underspends, Savings performance, Risks, "
    "Recommendations, and Questions for the user. Use short sections with "
    "Markdown headings. Be specific but do not invent numbers that were not "
    "provided."
)


def _call_anthropic(api_key: str, model: str, payload: dict) -> str | None:
    """Call the Anthropic Messages API. Returns Markdown text, or None on failure."""
    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1200,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Here are this month's aggregated budget figures "
                            "as JSON:\n\n" + json.dumps(payload, indent=2)
                        ),
                    }
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(text_blocks).strip() or None
    except requests.RequestException as exc:
        logger.warning("Anthropic API call failed, falling back to local summary: %s", exc)
        return None


def _local_summary(month, summary) -> str:
    """Deterministic rule-based Markdown summary used when no API key is configured."""
    planned = summary["planned"]
    actual = summary["actual"]
    lines = summary["lines"]
    overspend, underspend = biggest_variances(lines)

    performance = (
        "came in ahead of plan" if actual.net_after_savings >= planned.net_after_savings
        else "fell short of plan"
    )

    md = [f"# Monthly Review — {month.label}", ""]

    md.append("## Overall Performance")
    md.append(
        f"Your household {performance} this month. Planned net after savings was "
        f"{_fmt(planned.net_after_savings)}; actual net after savings was "
        f"{_fmt(actual.net_after_savings)}."
    )
    md.append("")

    md.append("## Largest Overspend")
    if overspend:
        md.append(
            f"**{overspend.name}** was over budget by {_fmt(-overspend.variance)} "
            f"(planned {_fmt(overspend.planned)}, actual {_fmt(overspend.actual)})."
        )
    else:
        md.append("No categories exceeded their planned amount this month. Well done.")
    md.append("")

    md.append("## Largest Underspend")
    if underspend:
        md.append(
            f"**{underspend.name}** came in under budget by {_fmt(underspend.variance)} "
            f"(planned {_fmt(underspend.planned)}, actual {_fmt(underspend.actual)})."
        )
    else:
        md.append("No categories came in significantly under budget this month.")
    md.append("")

    md.append("## Savings Performance")
    savings_diff = actual.savings - planned.savings
    if savings_diff >= 0:
        md.append(
            f"You saved {_fmt(actual.savings)}, which meets or exceeds your "
            f"{_fmt(planned.savings)} savings plan."
        )
    else:
        md.append(
            f"You saved {_fmt(actual.savings)} against a plan of {_fmt(planned.savings)}, "
            f"a shortfall of {_fmt(-savings_diff)}."
        )
    md.append("")

    md.append("## Risks")
    if actual.net_after_savings < 0:
        md.append("Actual spending exceeded income after savings this month, which is not sustainable if repeated.")
    elif overspend and overspend.variance < -100:
        md.append(f"The overspend in **{overspend.name}** is large enough to watch closely next month.")
    else:
        md.append("No significant risks stand out from this month's figures.")
    md.append("")

    md.append("## Recommendations")
    if overspend:
        md.append(f"- Review spending in **{overspend.name}** and consider adjusting next month's plan.")
    if savings_diff < 0:
        md.append("- Consider automating savings transfers early in the month so they happen before discretionary spending.")
    if not overspend and savings_diff >= 0:
        md.append("- Keep doing what you're doing — consider increasing your savings targets slightly next month.")
    md.append("")

    md.append("## Questions for You")
    md.append("- Was the overspend (if any) a one-off, or is it likely to recur next month?")
    md.append("- Are your current category plans still realistic, or do any need adjusting?")

    return "\n".join(md)


def generate_review(month, summary, api_key: str | None, model: str) -> str:
    """Generate the AI Monthly Review Markdown for a closed month.

    Tries the Anthropic API first if `api_key` is provided; falls back
    to a local deterministic summariser otherwise (or on API failure).
    """
    if api_key:
        payload = _build_aggregate_payload(month, summary)
        result = _call_anthropic(api_key, model, payload)
        if result:
            return result
    return _local_summary(month, summary)
