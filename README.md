# Secure Budget Planner

A production-style personal budgeting web application built with **Flask**,
designed as a portfolio project demonstrating secure software development
practices for a career in **Cybersecurity and Network Infrastructure**.

Users can plan a monthly budget across income, fixed expenses, variable
expenses, and savings categories; log actual spending; compare plan vs
actual with variance reporting; close out a month; and generate an
AI-written Monthly Review from the aggregated totals.

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Folder Structure](#folder-structure)
- [Database Overview](#database-overview)
- [API Documentation](#api-documentation)
- [Security Features](#security-features)
- [AI Monthly Review](#ai-monthly-review)
- [Testing](#testing)
- [Future Improvements](#future-improvements)

---

## Features

- User registration & login with hashed passwords (Flask-Login + Werkzeug)
- Monthly budget planning across seeded income / fixed / variable / savings categories
- Actual spending entry with live plan-vs-actual variance
- "Copy Previous Month" and "Hide Unused Categories" on the plan page
- Month closing (locks further edits)
- Monthly Review page: planned vs actual net, net after savings, biggest over/underspend, full variance table
- AI-generated Monthly Review (Markdown) from aggregated totals only
- History page listing every closed month
- Dashboard with Chart.js visualisations (spending by category, income vs expenses, savings progress, monthly trend)
- JSON REST API mirroring the core workflow
- Dark-mode-ready, responsive Bootstrap 5 UI

## Technology Stack

**Backend:** Python 3, Flask, SQLAlchemy (Flask-SQLAlchemy), Flask-Login,
Flask-WTF, Flask-Limiter, Werkzeug password hashing.

**Frontend:** HTML5, CSS3, Bootstrap 5, vanilla JavaScript, Chart.js.

**Database:** SQLite for local development. The connection string is
entirely driven by the `DATABASE_URL` environment variable, so switching
to PostgreSQL later requires no code changes — only a different URL and
`psycopg2-binary` in `requirements.txt`.

---

## Installation

### Prerequisites

- Python 3.10+
- pip

### Steps

```bash
# 1. Clone / unzip the project, then enter it
cd budget-planner

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
# (for running the test suite too)
pip install -r requirements-dev.txt

# 4. Configure environment variables
cp .env.example .env
# then edit .env and set a real SECRET_KEY, e.g.:
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Run the app (creates database/budget.db and seeds categories automatically)
python app.py
```

The app will be available at `http://127.0.0.1:5000`. Register an account,
log in, and you're ready to plan your first month.

### Running with Gunicorn (production-style)

```bash
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export SESSION_COOKIE_SECURE=true   # only if served over HTTPS
gunicorn app:app
```

---

## Configuration

All configuration lives in `config.py` and is driven by environment
variables (see `.env.example`). Key variables:

| Variable | Purpose | Default |
|---|---|---|
| `FLASK_ENV` | `development` / `testing` / `production` | `development` |
| `SECRET_KEY` | Signs session cookies & CSRF tokens — **must** be set in production | insecure dev fallback (a warning is logged) |
| `DATABASE_URL` | SQLAlchemy connection string | local SQLite file |
| `SESSION_COOKIE_SECURE` | Require HTTPS for cookies | `false` |
| `ANTHROPIC_API_KEY` | Enables real AI-generated reviews | unset (uses local summariser) |
| `RATELIMIT_STORAGE_URI` | Backend for Flask-Limiter | `memory://` |

---

## Folder Structure

```
budget-planner/
├── app.py                  # Application factory + WSGI entry point
├── config.py                # Environment-driven configuration
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── README.md
├── database/
│   ├── __init__.py          # db / login_manager / csrf / limiter singletons
│   └── audit.py             # Security audit-log helper
├── models/
│   ├── __init__.py          # aggregates models + seed_categories()
│   ├── user.py
│   ├── month.py
│   ├── category.py
│   ├── plan.py
│   ├── actual.py
│   └── review.py
├── forms/
│   ├── auth_forms.py        # Register / Login / Reset forms
│   └── budget_forms.py       # Month select, CSRF-only form, amount validation
├── services/
│   ├── finance.py           # Totals / variance calculations
│   └── ai_review.py          # AI Monthly Review generation
├── routes/
│   ├── auth.py
│   ├── dashboard.py
│   ├── months.py
│   ├── reviews.py
│   └── api.py
├── templates/                # Jinja2 templates (Bootstrap 5)
├── static/
│   ├── css/style.css
│   └── js/theme.js
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_models.py
│   └── test_api.py
└── logs/                     # app.log / audit.log (created at runtime)
```

---

## Database Overview

| Model | Purpose |
|---|---|
| `User` | Account credentials (hashed password only) |
| `Month` | One calendar month for one user; `locked` freezes editing |
| `Category` | Global, seeded list grouped as `income` / `fixed` / `variable` / `savings` |
| `Plan` | Planned amount for one category in one month |
| `Actual` | Actual amount for one category in one month |
| `Review` | The generated AI Monthly Review (Markdown) for a closed month |

Categories are seeded automatically on first run (`seed_categories()` in
`models/__init__.py`, called from the application factory) and match the
exact list specified for the project: 5 income categories, 12 fixed
expenses, 15 variable expenses, and 5 savings categories. **Savings
categories are stored identically to expenses** (a `Plan`/`Actual` row
against a `Category`) but are grouped separately (`group == "savings"`) so
totals and the UI can display them apart from ordinary spending.

---

## API Documentation

All endpoints require an authenticated session (Flask-Login cookie).
State-changing endpoints (`PUT`/`POST`) additionally require a valid CSRF
token in the `X-CSRFToken` header — fetch one from any rendered page's
`csrf_token` hidden input, or from `/months/select`.

| Method | Endpoint | Description |
|---|---|---|
| `PUT` | `/api/months/<id>/plan` | Bulk-update planned amounts. Body: `{"entries": [{"category_id": 1, "amount": "500.00"}, ...]}` |
| `PUT` | `/api/months/<id>/actuals` | Bulk-update actual amounts. Same body shape. |
| `POST` | `/api/months/<id>/close` | Lock the month against further edits. |
| `GET` | `/api/months/<id>/review` | Get planned/actual totals, biggest over/underspend, and the AI report (if generated). |
| `POST` | `/api/months/<id>/ai-report/generate` | Generate (or regenerate) the AI Monthly Review. Requires the month to be closed. |

All responses are JSON. A month that doesn't belong to the requesting
user returns `404` (not `403`), to avoid confirming that a given month ID
exists for someone else.

---

## Security Features

- **Password hashing** — Werkzeug's `generate_password_hash` / `check_password_hash` (scrypt); plaintext passwords are never stored or logged.
- **SQL injection prevention** — all queries go through the SQLAlchemy ORM; no raw string-built SQL.
- **CSRF protection** — Flask-WTF on every HTML form; the JSON API validates a per-session CSRF token from the `X-CSRFToken` header.
- **Secure sessions & cookies** — `HttpOnly`, `SameSite=Lax` on session/remember-me cookies, with `Secure` enforced automatically in production config (HTTPS only).
- **Input validation** — WTForms validators (username format, email format, password complexity/length) plus server-side amount validation (`forms/budget_forms.validate_amount`) shared between HTML routes and the API.
- **Output escaping** — Jinja2 autoescaping is on by default and untouched (no `|safe` on user input anywhere).
- **Rate limiting** — Flask-Limiter on `/register`, `/login`, and `/reset-password` to slow brute-force/credential-stuffing attempts.
- **Audit logging** — every security-relevant event (registration, login success/failure, logout, month close, AI report generation, etc.) is written to `logs/audit.log` via `database/audit.py`, without ever logging credentials.
- **Environment variables for secrets** — `SECRET_KEY`, `DATABASE_URL`, and `ANTHROPIC_API_KEY` are read from the environment (`.env`, git-ignored); a warning is logged if the insecure default `SECRET_KEY` is still in use.
- **Security response headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, a `Content-Security-Policy`, and `Strict-Transport-Security` (when serving over HTTPS) are set on every response.
- **Proper error handling** — custom 400/403/404/429/500 pages; unhandled exceptions are logged server-side rather than leaking stack traces to the client.
- **Ownership checks** — every month/plan/actual/review lookup verifies `month.user_id == current_user.id` before returning data, both in the HTML routes and the API.
- **AI review data minimisation** — only aggregated monthly totals and category variances are ever sent to an AI provider; raw transaction-level detail is never transmitted.

---

## AI Monthly Review

After a month is closed, `services/ai_review.generate_review()` builds a
small JSON payload of **aggregated totals only** (planned/actual income,
expenses, savings, net, and non-zero category variances — never raw
line items) and:

- If `ANTHROPIC_API_KEY` is configured, calls the Anthropic Messages API
  with that payload and a system prompt asking for a structured Markdown
  review (overall performance, largest overspends/underspends, savings
  performance, risks, recommendations, and questions for the user).
- Otherwise (or if the API call fails), falls back to a deterministic,
  rule-based Markdown summariser (`_local_summary`) covering the same
  sections — so the app is fully functional and demoable with **zero**
  external API keys.

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover:

- **Authentication** — registration (including duplicate username/email
  rejection and password hashing), login success/failure, logout,
  and login-required redirects.
- **Database models** — category seeding (and idempotency), the unique
  `(user, month, year)` constraint, and the finance calculation service
  (planned/actual totals, biggest overspend detection).
- **API endpoints** — plan/actual updates, month close, AI report
  generation, missing/invalid CSRF rejection, and cross-user access
  denial (a user cannot read another user's month via the API).

> **Note on this build environment:** this project was generated in a
> sandboxed environment without outbound network access, so the Flask
> extensions in `requirements.txt` could not be `pip install`-ed to run
> the suite live here. Every file was syntax-checked with
> `python -m py_compile`, and the code was carefully reviewed by hand for
> import/logic correctness, but you should run `pytest` yourself after
> installing dependencies to confirm everything passes in your
> environment before relying on this as a finished, verified deliverable.

---

## Future Improvements

The codebase is deliberately structured so these can be added without a
rewrite:

- Two-Factor Authentication (TOTP)
- Docker support (Dockerfile / docker-compose)
- PostgreSQL in production (`DATABASE_URL` already supports it)
- CSV import/export of plans and actuals
- PDF export of the Monthly Review
- Email notifications
- Email verification (the `User.email_verified` field already exists)
- Full password-reset flow (the `User.reset_token` fields and the
  `/reset-password` placeholder route already exist)
- Multi-user / household support with role-based permissions
- GitHub Actions CI/CD (lint + `pytest` on every push)

---

## License

This is a personal portfolio project. Feel free to fork and adapt it for
your own learning.
