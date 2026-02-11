# app/__init__.py
from __future__ import annotations

import os
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from flask import Flask, current_app as flask_current_app

from .logging import setup_logging
from .scheduler import enforce_all_expiry  # ✅ PPPoE + Hotspot


def _load_env() -> None:
    """
    Load .env for LOCAL DEV only, without overriding real environment variables.

    Rule:
    - If DATABASE_URL is already set (e.g. Render, CI, migrations),
      do NOT override it from .env.
    """
    if os.getenv("DATABASE_URL"):
        return

    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


def _env_flag(name: str, default: bool = True) -> bool:
    """Parse env bools like true/false/1/0/yes/no/on/off."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_app() -> Flask:
    # ---------------------------------------------------------
    # 1) Load env BEFORE importing Config (local dev only)
    # ---------------------------------------------------------
    _load_env()

    # ---------------------------------------------------------
    # 2) Import config AFTER env is loaded
    # ---------------------------------------------------------
    from .config import Config

    # ---------------------------------------------------------
    # 3) Create app
    # ---------------------------------------------------------
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)

    # ---------------------------------------------------------
    # Scheduler settings (safe defaults)
    # ---------------------------------------------------------
    app.config["SCHEDULER_ENABLED"] = _env_flag("SCHEDULER_ENABLED", False)
    app.config["SCHEDULER_DRY_RUN"] = _env_flag("SCHEDULER_DRY_RUN", True)
    app.config["SCHEDULER_INTERVAL_MINUTES"] = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "2"))

    # ---------------------------------------------------------
    # 4) Logging
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
    from .routes import main as main_bp
    from .mpesa import mpesa_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(mpesa_bp)  # ✅ /api/mpesa/*

    # ---------------------------------------------------------
    # 6b) Optional: keep legacy callback URL working
    #     This ensures BOTH:
    #       POST /mpesa/callback
    #       POST /api/mpesa/callback
    #     hit the same handler, avoiding Daraja misconfig risk.
    # ---------------------------------------------------------
    #@main_bp.post("/mpesa/callback")
    #def mpesa_callback_legacy():
    #   from .mpesa import mpesa_callback_route  # local import avoids circulars
    #    return mpesa_callback_route()

    # ---------------------------------------------------------
    # 7) Context processor
    # ---------------------------------------------------------
    @app.context_processor
    def inject_current_app():
        return {"current_app": flask_current_app}

    # ---------------------------------------------------------
    # 8) Health check
    # ---------------------------------------------------------
    @app.get("/_ping")
    def ping():
        return {"service": "dmp-hotspot", "status": "running"}

    # =========================================================
    # 9) Expiry Scheduler (PPPoE + Hotspot) — safe gating
    # =========================================================
    scheduler = BackgroundScheduler(timezone="UTC")

    def _should_start_scheduler() -> bool:
        """
        Start scheduler only when:
        - Enabled (SCHEDULER_ENABLED=true)
        - NOT running via Flask CLI commands (db upgrade/migrate/shell/etc.)
        - NOT the debug reloader parent process
        """
        if not app.config.get("SCHEDULER_ENABLED", False):
            return False

        # Avoid starting scheduler during CLI commands
        if _env_flag("FLASK_RUN_FROM_CLI", False):
            return False

        # In debug mode, only start scheduler in the reloader child process
        if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return False

        return True

    def start_scheduler() -> None:
        if not _should_start_scheduler():
            app.logger.info(
                "Scheduler NOT started (SCHEDULER_ENABLED=%s, FLASK_RUN_FROM_CLI=%s, debug=%s, WERKZEUG_RUN_MAIN=%s).",
                app.config.get("SCHEDULER_ENABLED", False),
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
            enforce_all_expiry,
            trigger=IntervalTrigger(minutes=interval_minutes),
            kwargs={"app": app, "dry_run": dry_run},
            id="expiry_enforcer_all",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )

        app.logger.info("Scheduler job registered: expiry_enforcer_all -> enforce_all_expiry")
        scheduler.start()
        app.logger.info("Scheduler started (interval=%sm, dry_run=%s).", interval_minutes, dry_run)

    start_scheduler()

    @app.teardown_appcontext
    def _shutdown_scheduler(_exc):
        if scheduler.running:
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                pass

    # ---------------------------------------------------------
    # 10) CLI Commands (Flask 3.x reliable registration)
    # ---------------------------------------------------------
    from .cli import ping_cli, sub_disconnect_last, sub_reconnect_last

    app.cli.add_command(ping_cli)
    app.cli.add_command(sub_disconnect_last)
    app.cli.add_command(sub_reconnect_last)

    return app
