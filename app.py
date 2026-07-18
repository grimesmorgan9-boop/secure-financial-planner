"""
app.py
------
Application factory for Secure Budget Planner.

Using a factory (`create_app`) rather than a bare module-level `app`
makes the app testable (tests can create fresh instances with
TestingConfig) and avoids import-time side effects.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
from flask_login import current_user

from config import get_config
from database import db, login_manager, csrf, limiter


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    _configure_logging(app)
    _warn_on_insecure_secret_key(app)

    # --- Extensions ---------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # --- Blueprints ------------------------------------------------------
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.months import months_bp
    from routes.reviews import reviews_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(months_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(api_bp)

    _register_user_loader()
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_template_globals(app)

    with app.app_context():
        os.makedirs(os.path.join(app.root_path, "database"), exist_ok=True)
        db.create_all()
        from models import seed_categories
        seed_categories()

    return app


def _configure_logging(app: Flask) -> None:
    log_dir = os.path.join(app.root_path, "logs")
    os.makedirs(log_dir, exist_ok=True)

    app_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1_000_000, backupCount=3
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    app.logger.addHandler(app_handler)
    app.logger.setLevel(logging.INFO)

    audit_handler = RotatingFileHandler(
        os.path.join(log_dir, "audit.log"), maxBytes=1_000_000, backupCount=5
    )
    audit_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    audit_logger = logging.getLogger("budget_planner.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False


def _warn_on_insecure_secret_key(app: Flask) -> None:
    if app.config.get("SECRET_KEY") == "dev-insecure-key-change-me":
        app.logger.warning(
            "SECRET_KEY is using the insecure development default. "
            "Set the SECRET_KEY environment variable before deploying."
        )


def _register_user_loader():
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(_e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(_e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error: %s", e)
        return render_template("errors/500.html"), 500


def _register_security_headers(app: Flask) -> None:
    """Attach a conservative set of security headers to every response.

    Content-Security-Policy is intentionally permissive enough to allow
    Bootstrap/Chart.js from a CDN while still blocking inline script
    injection vectors typical of XSS.
    """

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net;",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


def _register_template_globals(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}


# WSGI entry point (e.g. `gunicorn app:app`).
app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
