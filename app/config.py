import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mikrotik
    MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "10.5.50.1")
    MIKROTIK_API_PORT = int(os.getenv("MIKROTIK_API_PORT", "8728"))
    MIKROTIK_USER = os.getenv("MIKROTIK_USER", "hotspotapi")
    MIKROTIK_PASS = os.getenv("MIKROTIK_PASS", "")

    # M-Pesa
    MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")
    MPESA_ACCOUNT_REF = os.getenv("MPESA_ACCOUNT_REF", "DMPOLIN-HOTSPOT")
    MPESA_TX_DESC = os.getenv("MPESA_TX_DESC", "Dmpolin Connect Hotspot")

    PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "")
    API_BASE_URL = os.getenv("API_BASE_URL", "")
