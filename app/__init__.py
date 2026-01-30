from __future__ import annotations

from flask import Flask, send_from_directory

from .config import Config
from .extensions import db, migrate, limiter, login_manager


def create_app() -> Flask:
    app = Flask(__name__)

    # Load config
    app.config.from_object(Config)

    # Ensure sessions work (needed for Flask-Login + flashing)
    app.config.setdefault("SECRET_KEY", "dev-change-me")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from .routes import main
    from .admin import admin as admin_bp

    app.register_blueprint(main)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Simple sanity check endpoint (avoid clashing with main "/")
    @app.get("/_ping")
    def ping():
        return {"service": "dmp-hotspot", "status": "running"}

    # Favicon handler
    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory("static", "favicon.ico")

    return app
