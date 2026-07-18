"""
config.py
---------
Central application configuration.

Configuration values that affect security (secret key, cookie flags,
session lifetime, etc.) are pulled from environment variables so that
no secrets are ever committed to source control. A `.env.example`
file is provided to document the expected variables; real values
belong in a local `.env` file (which is git-ignored) or in the
environment of whatever host/container runs the app.

The project ships with SQLite for local development, but the
SQLALCHEMY_DATABASE_URI is driven entirely by the DATABASE_URL
environment variable so that swapping in PostgreSQL later (e.g.
`postgresql://user:pass@host:5432/budget`) requires no code changes.
"""

import os
from datetime import timedelta

# Load a local .env file if python-dotenv is available and a .env exists.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is a dev convenience only
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    # --- Core Flask / secrets -------------------------------------------------
    # SECRET_KEY signs the session cookie and CSRF tokens. It MUST be set
    # via an environment variable in any real deployment. A fallback is
    # provided only so the app doesn't hard-crash on a first `flask run`
    # during local exploration; a warning is logged in app.py if it's used.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")

    # --- Database ---------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'database', 'budget.db')}"
    )
    # Some hosts (e.g. Heroku-style) emit postgres:// which SQLAlchemy 1.4+
    # no longer accepts; normalise it here so PostgreSQL "just works".
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Session / cookie security ----------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Secure cookies require HTTPS. Toggle via env so local HTTP dev still
    # works, while production (HTTPS) deployments can enforce it.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # --- CSRF (Flask-WTF) ---------------------------------------------------
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # tokens valid for the whole session

    # --- Rate limiting (Flask-Limiter) -------------------------------------
    # RATELIMIT_STORAGE_URI is the current config key (Flask-Limiter >= 3);
    # RATELIMIT_STORAGE_URL is kept as an alias for older versions.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_STORAGE_URL = RATELIMIT_STORAGE_URI
    RATELIMIT_DEFAULT = "200 per day;50 per hour"

    # --- AI monthly review ---------------------------------------------------
    # Optional: if set, real calls are made to the Anthropic API to generate
    # the monthly AI report. If absent, a deterministic local summariser is
    # used instead so the app is fully functional without any external key.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # --- Misc ---------------------------------------------------------------
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    # CSRF stays enabled in tests (rather than disabled) so the test suite
    # exercises the real protection path; tests fetch a token from a
    # rendered form before posting, the same way a browser would.
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(name, DevelopmentConfig)
