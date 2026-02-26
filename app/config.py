# app/config.py
from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    # =========================================================
    # Core Flask
    # =========================================================
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL is not set")

    # =========================================================
    # Rate limiting storage (Flask-Limiter)
    # =========================================================
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")

    # =========================================================
    # Router Automation Master Switch (CANONICAL)
    # =========================================================
    # Single source of truth switch for ANY router-touching code.
    ROUTER_AGENT_ENABLED = _env_bool("ROUTER_AGENT_ENABLED", False)

    # Compatibility aliases (used elsewhere)
    # If you set ROUTER_AUTOMATION_ENABLED=true, we treat that as enabling router agent too.
    ROUTER_AUTOMATION_ENABLED = _env_bool("ROUTER_AUTOMATION_ENABLED", ROUTER_AGENT_ENABLED) or ROUTER_AGENT_ENABLED
    ROUTER_AUTOMATION_DRY_RUN = _env_bool("ROUTER_AUTOMATION_DRY_RUN", True)

    # =========================================================
    # MikroTik PPPoE Router (Core)
    # =========================================================
    MIKROTIK_PPPOE_HOST = os.getenv("MIKROTIK_PPPOE_HOST", "192.168.230.1").strip()
    MIKROTIK_PPPOE_PORT = int(os.getenv("MIKROTIK_PPPOE_PORT", "8728"))
    MIKROTIK_PPPOE_USER = os.getenv("MIKROTIK_PPPOE_USER", "admin").strip()
    MIKROTIK_PPPOE_PASS = os.getenv("MIKROTIK_PPPOE_PASS", "").strip()
    MIKROTIK_PPPOE_TLS = _env_bool("MIKROTIK_PPPOE_TLS", False)

    # =========================================================
    # MikroTik Hotspot Router (separate)
    # =========================================================
    MIKROTIK_HOTSPOT_HOST = os.getenv("MIKROTIK_HOTSPOT_HOST", "192.168.240.1").strip()
    MIKROTIK_HOTSPOT_PORT = int(os.getenv("MIKROTIK_HOTSPOT_PORT", "8728"))
    MIKROTIK_HOTSPOT_USER = os.getenv("MIKROTIK_HOTSPOT_USER", "admin").strip()
    MIKROTIK_HOTSPOT_PASS = os.getenv("MIKROTIK_HOTSPOT_PASS", "").strip()
    MIKROTIK_HOTSPOT_TLS = _env_bool("MIKROTIK_HOTSPOT_TLS", False)

    # =========================================================
    # Compatibility aliases (used by mikrotik_hotspot.py today)
    # Prefer HOTSPOT_* vars; fall back to generic vars if provided.
    # =========================================================
    MIKROTIK_HOST = os.getenv("MIKROTIK_HOTSPOT_HOST", os.getenv("MIKROTIK_HOST", "192.168.240.1")).strip()
    MIKROTIK_PORT = int(os.getenv("MIKROTIK_HOTSPOT_PORT", os.getenv("MIKROTIK_PORT", "8728")))
    MIKROTIK_USER = os.getenv("MIKROTIK_HOTSPOT_USER", os.getenv("MIKROTIK_USER", "admin")).strip()
    MIKROTIK_PASSWORD = os.getenv("MIKROTIK_HOTSPOT_PASS", os.getenv("MIKROTIK_PASSWORD", "")).strip()
    MIKROTIK_TLS = _env_bool("MIKROTIK_HOTSPOT_TLS", _env_bool("MIKROTIK_TLS", False))

    # =========================================================
    # Optional safety validation (only when router is enabled)
    # =========================================================
    if ROUTER_AGENT_ENABLED or ROUTER_AUTOMATION_ENABLED:
        missing: list[str] = []

        # PPPoE
        if not MIKROTIK_PPPOE_HOST:
            missing.append("MIKROTIK_PPPOE_HOST")
        if not MIKROTIK_PPPOE_USER:
            missing.append("MIKROTIK_PPPOE_USER")
        if not MIKROTIK_PPPOE_PASS:
            missing.append("MIKROTIK_PPPOE_PASS")

        # Hotspot
        if not MIKROTIK_HOST:
            missing.append("MIKROTIK_HOTSPOT_HOST (or MIKROTIK_HOST)")
        if not MIKROTIK_USER:
            missing.append("MIKROTIK_HOTSPOT_USER (or MIKROTIK_USER)")
        if not MIKROTIK_PASSWORD:
            missing.append("MIKROTIK_HOTSPOT_PASS (or MIKROTIK_PASSWORD)")

        if missing:
            raise RuntimeError("Router automation enabled but missing: " + ", ".join(missing))

    # =========================================================
    # M-Pesa (STK Push)
    # =========================================================
    MPESA_ENV = os.getenv("MPESA_ENV", "sandbox").strip().lower()  # sandbox | production
    if MPESA_ENV not in ("sandbox", "production"):
        raise RuntimeError("MPESA_ENV must be 'sandbox' or 'production'")

    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "").strip()
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "").strip()
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "").strip()
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "").strip()
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "").strip()

    # Support both naming styles:
    # - preferred: MPESA_STK_ACCOUNT_REF / MPESA_STK_DESC
    # - legacy:    MPESA_ACCOUNT_REF / MPESA_TX_DESC
    MPESA_STK_ACCOUNT_REF = os.getenv("MPESA_STK_ACCOUNT_REF", os.getenv("MPESA_ACCOUNT_REF", "DmpolinConnect")).strip()
    MPESA_STK_DESC = os.getenv("MPESA_STK_DESC", os.getenv("MPESA_TX_DESC", "Internet subscription")).strip()

    if MPESA_ENV == "production" and not MPESA_CALLBACK_URL:
        raise RuntimeError("MPESA_CALLBACK_URL is not set (required in production)")

    # =========================================================
    # Portal / API URLs (used in SMS, redirects, UI)
    # =========================================================
    PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "").rstrip("/")
    API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")

    ROUTER_AGENT_TOKEN = os.getenv("ROUTER_AGENT_TOKEN", "")

