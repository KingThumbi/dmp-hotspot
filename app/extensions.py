from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager


# =========================================================
# Database + Migrations
# =========================================================
db = SQLAlchemy()
migrate = Migrate()


# =========================================================
# Rate limiting
# (no global limits; apply per-route with @limiter.limit)
# =========================================================
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)


# =========================================================
# Admin authentication (Flask-Login)
# =========================================================
login_manager = LoginManager()
login_manager.login_view = "admin.login_get"
login_manager.login_message = "Please log in to access the admin dashboard."
login_manager.login_message_category = "error"
