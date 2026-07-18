"""
tests/conftest.py
------------------
Shared pytest fixtures: a fresh in-memory-SQLite app per test
(TestingConfig), plus a Flask test client and a helper to register
and log in a user quickly.
"""

import re

import pytest

from app import create_app
from database import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


def _csrf_token_from(response):
    match = re.search(rb'name="csrf_token" type="hidden" value="([^"]+)"', response.data)
    assert match, "Could not find CSRF token in rendered form"
    return match.group(1).decode()


def register(client, username="alice", email="alice@example.com", password="Sup3rSecret!"):
    get_resp = client.get("/register")
    token = _csrf_token_from(get_resp)
    return client.post(
        "/register",
        data={
            "csrf_token": token,
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, username="alice", password="Sup3rSecret!"):
    get_resp = client.get("/login")
    token = _csrf_token_from(get_resp)
    return client.post(
        "/login",
        data={"csrf_token": token, "username": username, "password": password},
        follow_redirects=True,
    )
