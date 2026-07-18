"""
routes/auth.py
---------------
Registration, login, logout, and a placeholder password-reset request
flow. Login attempts are rate-limited to slow down credential
stuffing / brute force attempts, and every significant auth event is
written to the audit log (without ever logging passwords).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from database import db, limiter
from database.audit import log_event
from forms.auth_forms import RegisterForm, LoginForm, PasswordResetRequestForm
from models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        log_event("registration_success", user=user)
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            log_event("login_success", user=user)
            next_page = request.args.get("next")
            # Only allow relative redirect targets to prevent open-redirect attacks.
            if not next_page or not next_page.startswith("/"):
                next_page = url_for("dashboard.index")
            return redirect(next_page)

        log_event("login_failure", extra=f"identifier={identifier}")
        flash("Invalid username/email or password.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_event("logout", user=current_user)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def reset_password_request():
    """Placeholder for the future password-reset feature (spec: 'Password
    reset structure (placeholder)'). Does not yet send email; it simply
    acknowledges the request without revealing whether the address exists,
    to avoid leaking account existence."""
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        log_event("password_reset_requested", extra=f"email={form.email.data}")
        flash(
            "If an account with that email exists, password reset instructions "
            "will be sent. (Email delivery is not yet implemented in this build.)",
            "info",
        )
        return redirect(url_for("auth.login"))
    return render_template("reset_password.html", form=form)
