# app/__init__.py
from __future__ import annotations

import os
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from flask import Flask

from .logging import setup_logging
from .scheduler import enforce_pppoe_expiry


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
        load_dotenv(dotenv_path=env_path, override=True)


def _env_flag(name: str, default: bool = True) -> bool:
    """Parse env bools like true/false/1/0/yes/no."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_app() -> Flask:
    # ---------------------------------------------------------
    # 1) Load .env BEFORE importing Config
    # ---------------------------------------------------------
    _load_env()

    # ---------------------------------------------------------
    # 2) Import config AFTER env
    # ---------------------------------------------------------
    from .config import Config

    # ---------------------------------------------------------
    # 3) Create app
    # ---------------------------------------------------------
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    app.config.setdefault("SECRET_KEY", "dev-change-me")

    # Optional: allow env override in addition to Config
    # (If you already set this inside Config, this won’t hurt.)
    app.config.setdefault("SCHEDULER_ENABLED", _env_flag("SCHEDULER_ENABLED", True))
    app.config.setdefault("SCHEDULER_DRY_RUN", _env_flag("SCHEDULER_DRY_RUN", True))
    app.config.setdefault("SCHEDULER_INTERVAL_MINUTES", int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "2")))

    # ---------------------------------------------------------
    # 4) Logging (central)
    # ---------------------------------------------------------
    setup_logging(debug=bool(app.config.get("DEBUG", False)))

    # ---------------------------------------------------------
    # 5) Extensions
    # ---------------------------------------------------------
    from .extensions import db, limiter, login_manager, migrate

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)

    # ---------------------------------------------------------
    # 6) Blueprints
    # ---------------------------------------------------------
    from .admin import admin as admin_bp
    from .routes import main

    app.register_blueprint(main)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ---------------------------------------------------------
    # 7) Health check
    # ---------------------------------------------------------
    @app.get("/_ping")
    def ping():
        return {"service": "dmp-hotspot", "status": "running"}

    # =========================================================
    # 8) PPPoE Expiry Scheduler (Phase C)
    # =========================================================
    scheduler = BackgroundScheduler(timezone="UTC")

    def _should_start_scheduler() -> bool:
        """
        Start scheduler only when:
        - Enabled (SCHEDULER_ENABLED=true)
        - NOT running via Flask CLI (db migrate/upgrade/shell/etc.)
        - NOT the reloader parent process (debug reloader)
        """
        if not app.config.get("SCHEDULER_ENABLED", True):
            return False

        # Flask CLI sets this when running commands like `flask db ...`
        if _env_flag("FLASK_RUN_FROM_CLI", False):
            return False

        # Flask debug reloader spawns two processes; only run in the child.
        if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return False

        return True

    def start_scheduler() -> None:
        if not _should_start_scheduler():
            app.logger.info(
                "Scheduler NOT started (SCHEDULER_ENABLED=%s, FLASK_RUN_FROM_CLI=%s, debug=%s, WERKZEUG_RUN_MAIN=%s).",
                app.config.get("SCHEDULER_ENABLED", True),
                os.getenv("FLASK_RUN_FROM_CLI", ""),
                app.debug,
                os.getenv("WERKZEUG_RUN_MAIN", ""),
            )
            return

        if scheduler.running:
            return

        interval_minutes = int(app.config.get("SCHEDULER_INTERVAL_MINUTES", 2))
        dry_run = bool(app.config.get("SCHEDULER_DRY_RUN", True))

        scheduler.add_job(
            enforce_pppoe_expiry,
            trigger=IntervalTrigger(minutes=interval_minutes),
            kwargs={"app": app, "dry_run": dry_run},
            id="pppoe_expiry_enforcer",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        scheduler.start()
        app.logger.info("Scheduler started (interval=%sm, dry_run=%s).", interval_minutes, dry_run)

    # Start immediately after app is created (but safely gated)
    start_scheduler()

    # Ensure clean shutdown (helps in dev reloads and tests)
    @app.teardown_appcontext
    def _shutdown_scheduler(_exc):
        if scheduler.running:
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                # Don’t break request teardown if scheduler shutdown fails
                pass

    return app
