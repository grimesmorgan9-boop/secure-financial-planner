"""
database package
-----------------
Holds the shared extension instances (SQLAlchemy, Flask-Login,
Flask-WTF's CSRFProtect, and Flask-Limiter). Keeping them here, rather
than instantiating them inside app.py, avoids circular imports: models
and routes can `from database import db` without needing to import the
application factory itself.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Login manager configuration shared across the app.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"
