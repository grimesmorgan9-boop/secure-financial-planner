"""
tests/test_auth.py
-------------------
Covers registration, login, logout, duplicate-account rejection, and
password hashing (never storing plaintext).
"""

from tests.conftest import register, login
from models.user import User


def test_register_creates_user_with_hashed_password(client, db):
    response = register(client)
    assert response.status_code == 200

    user = User.query.filter_by(username="alice").first()
    assert user is not None
    assert user.password_hash != "Sup3rSecret!"
    assert user.check_password("Sup3rSecret!")
    assert not user.check_password("wrong-password")


def test_duplicate_username_rejected(client, db):
    register(client)
    response = register(client, email="different@example.com")
    assert b"already taken" in response.data


def test_duplicate_email_rejected(client, db):
    register(client)
    response = register(client, username="alice2")
    assert b"already exists" in response.data


def test_login_success_redirects_to_dashboard(client, db):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_wrong_password_shows_error(client, db):
    register(client)
    response = login(client, password="wrong-password")
    assert b"Invalid username" in response.data


def test_logout_requires_login_redirect(client, db):
    response = client.get("/logout", follow_redirects=True)
    # Should be redirected to the login page rather than logging out anonymously.
    assert b"Log In" in response.data or b"Please log in" in response.data


def test_dashboard_requires_login(client, db):
    response = client.get("/", follow_redirects=True)
    assert b"Log In" in response.data or b"Please log in" in response.data
