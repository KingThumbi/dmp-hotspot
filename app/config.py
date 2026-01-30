import os


class Config:
    # =========================================================
    # Core Flask
    # =========================================================
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL is not set")


    # =========================================================
    # MikroTik (Hotspot / PPPoE integration)
    # =========================================================
    MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "10.5.50.1")
    MIKROTIK_API_PORT = int(os.getenv("MIKROTIK_API_PORT", "8728"))
    MIKROTIK_USER = os.getenv("MIKROTIK_USER", "hotspotapi")
    MIKROTIK_PASS = os.getenv("MIKROTIK_PASS", "")

    # Optional safety flag (lets you disable router access globally)
    MIKROTIK_ENABLED = os.getenv("MIKROTIK_ENABLED", "true").lower() == "true"


    # =========================================================
    # M-Pesa (STK Push)
    # =========================================================
    MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")  # sandbox | production

    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")

    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")

    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")

    MPESA_ACCOUNT_REF = os.getenv("MPESA_ACCOUNT_REF", "DMPOLIN-HOTSPOT")
    MPESA_TX_DESC = os.getenv("MPESA_TX_DESC", "Dmpolin Connect Hotspot")

    # Enforce critical M-Pesa config (fail fast instead of silent 500s)
    if MPESA_ENV not in ("sandbox", "production"):
        raise RuntimeError("MPESA_ENV must be 'sandbox' or 'production'")

    # Only enforce callback URL in production
    if MPESA_ENV == "production" and not MPESA_CALLBACK_URL:
        raise RuntimeError("MPESA_CALLBACK_URL is not set (required in production)")



    # =========================================================
    # Portal / API URLs (used in SMS, redirects, UI)
    # =========================================================
    PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "").rstrip("/")
    API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")

    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")


