from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database
db = SQLAlchemy()

# Migrations
migrate = Migrate()

# Rate limiting (apply per-route with @limiter.limit(...))
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # keep global defaults off; set limits per endpoint
)
