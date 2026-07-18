"""
tests/test_api.py
------------------
Covers the JSON REST API: plan/actual updates, close, review
retrieval, AI report generation, and ownership enforcement (a user
cannot access another user's month via the API).
"""

from tests.conftest import register, login, _csrf_token_from


def _get_csrf_token(client):
    """Fetch a CSRF token by loading a page that renders a form."""
    resp = client.get("/months/select")
    return _csrf_token_from(resp)


def _create_month(client, db):
    login_resp = client.get("/")  # ensures current-month Month row exists
    month = Month.query.first()
    assert month is not None
    return month


def test_api_requires_login(client, db):
    response = client.put("/api/months/1/plan", json={"entries": []})
    assert response.status_code in (302, 401)


def test_api_plan_update_and_get_review(app, client, db):
    register(client)
    login(client)
    month = _create_month(client, db)
    token = _get_csrf_token(client)

    salary = Category.query.filter_by(name="Salary").first()
    response = client.put(
        f"/api/months/{month.id}/plan",
        json={"entries": [{"category_id": salary.id, "amount": "2500.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    assert response.get_json()["planned"]["income"] == 2500.0

    review_resp = client.get(f"/api/months/{month.id}/review")
    assert review_resp.status_code == 200
    body = review_resp.get_json()
    assert body["planned"]["income"] == 2500.0
    assert body["locked"] is False


def test_api_close_and_generate_ai_report(app, client, db):
    register(client)
    login(client)
    month = _create_month(client, db)
    token = _get_csrf_token(client)

    close_resp = client.post(f"/api/months/{month.id}/close", headers={"X-CSRFToken": token})
    assert close_resp.status_code == 200
    assert close_resp.get_json()["locked"] is True

    report_resp = client.post(
        f"/api/months/{month.id}/ai-report/generate", headers={"X-CSRFToken": token}
    )
    assert report_resp.status_code == 200
    assert "ai_report" in report_resp.get_json()
    assert len(report_resp.get_json()["ai_report"]) > 0


def test_api_rejects_missing_csrf_token(app, client, db):
    register(client)
    login(client)
    month = _create_month(client, db)

    response = client.post(f"/api/months/{month.id}/close")
    assert response.status_code == 400


def test_api_cannot_access_other_users_month(app, client, db):
    register(client, username="alice", email="alice@example.com")
    login(client, username="alice")
    month = _create_month(client, db)
    client.get("/logout")

    register(client, username="mallory", email="mallory@example.com")
    login(client, username="mallory")

    response = client.get(f"/api/months/{month.id}/review")
    assert response.status_code == 404
