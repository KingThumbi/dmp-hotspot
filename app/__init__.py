# app/__init__.py
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .scheduler import enforce_pppoe_expiry
from .logging import setup_logging


def _load_env() -> None:
    """
    Load .env reliably for:
    - flask run
    - python -c / scripts
    - gunicorn / Render
    """
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


def create_app() -> Flask:
    # 1) Load env FIRST
    _load_env()

    # 2) Import config AFTER env
    from .config import Config

    # 3) Create app
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    app.config.setdefault("SECRET_KEY", "dev-change-me")

    # 4) Logging (central)
    setup_logging(debug=bool(app.config.get("DEBUG", False)))

    # 5) Extensions
    from .extensions import db, migrate, limiter, login_manager

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)

    # 6) Blueprints
    from .routes import main
    from .admin import admin as admin_bp

    app.register_blueprint(main)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # 7) Health check
    @app.get("/_ping")
    def ping():
        return {"service": "dmp-hotspot", "status": "running"}

    # =========================================================
    # 8) PPPoE Expiry Scheduler (Phase C)
    # =========================================================
    scheduler = BackgroundScheduler(timezone="UTC")

    def start_scheduler() -> None:
        """
        Start scheduler safely.
        - Avoid double-starting under Flask reloader
        - Allow master switch via SCHEDULER_ENABLED
        """
        if not app.config.get("SCHEDULER_ENABLED", True):
            app.logger.info("Scheduler disabled (SCHEDULER_ENABLED=false).")
            return

        # Flask debug reloader runs two processes; only run in the main one.
        if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return

        if scheduler.running:
            return

        scheduler.add_job(
            enforce_pppoe_expiry,
            trigger=IntervalTrigger(minutes=2),
            kwargs={"app": app, "dry_run": True},  # 🔒 DRY-RUN DEFAULT
            id="pppoe_expiry_enforcer",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        scheduler.start()
        app.logger.info("Scheduler started (dry_run=True).")

    # Start immediately after app is created
    start_scheduler()

    return app
