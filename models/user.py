"""
models/user.py
---------------
The User model backs authentication (Flask-Login). Passwords are
NEVER stored in plain text: only a salted Werkzeug hash is persisted,
and the hashing algorithm (scrypt by default in modern Werkzeug) is
delegated entirely to `werkzeug.security`, avoiding any hand-rolled
crypto.
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from database import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Placeholder fields for future features (password reset, email
    # verification) so those can be added without a breaking migration.
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    reset_token = db.Column(db.String(128), nullable=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    months = db.relationship(
        "Month", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        """Hash and store the given plaintext password."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<User {self.username}>"
