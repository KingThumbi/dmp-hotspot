from __future__ import annotations

from flask import Flask

from .config import Config
from .extensions import db, migrate, limiter


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Register blueprints
    from .routes import api
    app.register_blueprint(api)

    # Simple root sanity check (optional)
    @app.get("/")
    def index():
        return {"service": "dmp-hotspot", "status": "running"}

    return app
