"""
forms/auth_forms.py
--------------------
Registration and login forms. Validation here is defence-in-depth:
even though the database also enforces unique username/email at the
schema level, validating early gives better error messages and stops
malformed input before it reaches the ORM layer.
"""

import re

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

from models.user import User

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def username_format(_form, field):
    if not USERNAME_RE.match(field.data or ""):
        raise ValidationError(
            "Username must be 3-32 characters and contain only letters, "
            "numbers, dots, hyphens, or underscores."
        )


class RegisterForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=32), username_format]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=10, max=128)]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("An account with that email already exists.")

    def validate_password(self, field):
        # Basic complexity check beyond simple length, without being so
        # strict that it becomes user-hostile.
        pwd = field.data or ""
        if not (re.search(r"[A-Za-z]", pwd) and re.search(r"[0-9]", pwd)):
            raise ValidationError("Password must include at least one letter and one number.")


class LoginForm(FlaskForm):
    username = StringField("Username or Email", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class PasswordResetRequestForm(FlaskForm):
    """Placeholder form for the future password-reset feature."""

    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    submit = SubmitField("Send Reset Link")
