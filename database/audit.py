"""
database/audit.py
------------------
Minimal audit logging helper.

Security-relevant events (login success/failure, registration, month
close, AI report generation, etc.) are written to a dedicated logger
that is configured in app.py to write to logs/audit.log, separate
from ordinary application logs. This keeps a tamper-evident-ish trail
that is useful during incident review, without pulling in a heavier
dependency.
"""

import logging

audit_logger = logging.getLogger("budget_planner.audit")


def log_event(event: str, *, user=None, extra: str = "") -> None:
    """Record a structured audit event.

    Args:
        event: short machine-readable event name, e.g. "login_success".
        user: the current user (if any) - only id/username are logged,
              never passwords or password hashes.
        extra: optional human-readable context.
    """
    identity = "anonymous"
    if user is not None and getattr(user, "is_authenticated", False):
        identity = f"user_id={user.id} username={user.username}"
    audit_logger.info("event=%s %s extra=%s", event, identity, extra)
