# app/config.py
from __future__ import annotations

import os


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
    # - Prefer REDIS_URL when available
    # - Fall back to memory:// for local dev
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")

    # =========================================================
    # Router Automation Master Switch
    # =========================================================
    # Hard-disable all router-touching code unless explicitly enabled.
    ROUTER_AGENT_ENABLED = os.getenv("ROUTER_AGENT_ENABLED", "false").strip().lower() == "true"

    # =========================================================
    # MikroTik PPPoE Router (Core)
    # =========================================================
    MIKROTIK_PPPOE_HOST = os.getenv("MIKROTIK_PPPOE_HOST", "192.168.230.1").strip()
    MIKROTIK_PPPOE_PORT = int(os.getenv("MIKROTIK_PPPOE_PORT", "8728"))
    MIKROTIK_PPPOE_USER = os.getenv("MIKROTIK_PPPOE_USER", "admin").strip()
    MIKROTIK_PPPOE_PASS = os.getenv("MIKROTIK_PPPOE_PASS", "")
    MIKROTIK_PPPOE_TLS = os.getenv("MIKROTIK_PPPOE_TLS", "false").strip().lower() == "true"

    # =========================================================
    # MikroTik Hotspot Router (separate, later)
    # =========================================================
    MIKROTIK_HOTSPOT_HOST = os.getenv("MIKROTIK_HOTSPOT_HOST", "192.168.240.1").strip()
    MIKROTIK_HOTSPOT_PORT = int(os.getenv("MIKROTIK_HOTSPOT_PORT", "8728"))
    MIKROTIK_HOTSPOT_USER = os.getenv("MIKROTIK_HOTSPOT_USER", "hotspotapi").strip()
    MIKROTIK_HOTSPOT_PASS = os.getenv("MIKROTIK_HOTSPOT_PASS", "")
    MIKROTIK_HOTSPOT_TLS = os.getenv("MIKROTIK_HOTSPOT_TLS", "false").strip().lower() == "true"

    # =========================================================
    # Optional safety validation (only when router agent enabled)
    # =========================================================
    if ROUTER_AGENT_ENABLED:
        missing: list[str] = []
        if not MIKROTIK_PPPOE_HOST:
            missing.append("MIKROTIK_PPPOE_HOST")
        if not MIKROTIK_PPPOE_USER:
            missing.append("MIKROTIK_PPPOE_USER")
        if not MIKROTIK_PPPOE_PASS:
            missing.append("MIKROTIK_PPPOE_PASS")

        if missing:
            raise RuntimeError("ROUTER_AGENT_ENABLED=true but missing: " + ", ".join(missing))

    # =========================================================
    # M-Pesa (STK Push)
    # =========================================================
    MPESA_ENV = os.getenv("MPESA_ENV", "sandbox").strip().lower()  # sandbox | production

    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")

    MPESA_ACCOUNT_REF = os.getenv("MPESA_ACCOUNT_REF", "DMPOLIN-HOTSPOT")
    MPESA_TX_DESC = os.getenv("MPESA_TX_DESC", "Dmpolin Connect Hotspot")

    if MPESA_ENV not in ("sandbox", "production"):
        raise RuntimeError("MPESA_ENV must be 'sandbox' or 'production'")

    if MPESA_ENV == "production" and not MPESA_CALLBACK_URL:
        raise RuntimeError("MPESA_CALLBACK_URL is not set (required in production)")

    # =========================================================
    # Portal / API URLs (used in SMS, redirects, UI)
    # =========================================================
    PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "").rstrip("/")
    API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")
