from __future__ import annotations

import base64
import datetime as dt
from typing import Any, Dict

import requests


def _base_url(env: str) -> str:
    """
    Safaricom base URL depending on environment.
    Expected env values: "sandbox" or "production" (anything else treated as production).
    """
    return "https://sandbox.safaricom.co.ke" if (env or "").lower() == "sandbox" else "https://api.safaricom.co.ke"


def _require_config(app, key: str) -> str:
    """
    Fetch required config value or raise a clear error.
    """
    val = app.config.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise RuntimeError(f"Missing required config: {key}")
    return val


def get_access_token(app) -> str:
    """
    Get OAuth access token from Safaricom.
    Uses Basic auth (requests handles this via auth=(key, secret)).
    """
    env = _require_config(app, "MPESA_ENV")
    key = _require_config(app, "MPESA_CONSUMER_KEY")
    secret = _require_config(app, "MPESA_CONSUMER_SECRET")

    url = _base_url(env) + "/oauth/v1/generate?grant_type=client_credentials"

    r = requests.get(url, auth=(key, secret), timeout=30)
    r.raise_for_status()

    data = r.json() or {}
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Safaricom token response missing access_token")
    return token


def stk_push(app, phone_254: str, amount: int) -> Dict[str, Any]:
    """
    Initiate STK push to phone.
    phone_254 must be like 2547XXXXXXXX.
    Returns Safaricom JSON response (contains CheckoutRequestID, MerchantRequestID on success).

    Required config keys:
      - MPESA_ENV: "sandbox" or "production"
      - MPESA_CONSUMER_KEY
      - MPESA_CONSUMER_SECRET
      - MPESA_SHORTCODE
      - MPESA_PASSKEY
      - MPESA_CALLBACK_URL
      - MPESA_ACCOUNT_REF
      - MPESA_TX_DESC
    """
    # Validate inputs
    phone_254 = (phone_254 or "").strip()
    if not (phone_254.isdigit() and phone_254.startswith("254") and len(phone_254) == 12):
        raise ValueError("phone_254 must be numeric and in format 2547XXXXXXXX (12 digits)")

    amount = int(amount)
    if amount <= 0:
        raise ValueError("amount must be a positive integer")

    # Required config
    env = _require_config(app, "MPESA_ENV")
    shortcode = _require_config(app, "MPESA_SHORTCODE")
    passkey = _require_config(app, "MPESA_PASSKEY")
    callback_url = _require_config(app, "MPESA_CALLBACK_URL")
    account_ref = _require_config(app, "MPESA_ACCOUNT_REF")
    tx_desc = _require_config(app, "MPESA_TX_DESC")

    url = _base_url(env) + "/mpesa/stkpush/v1/processrequest"

    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    token = get_access_token(app)

    payload: Dict[str, Any] = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_254,
        "PartyB": shortcode,
        "PhoneNumber": phone_254,
        "CallBackURL": callback_url,
        "AccountReference": account_ref,
        "TransactionDesc": tx_desc,
    }

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()

    data = r.json() or {}
    # Helpful sanity check: Safaricom returns ResponseCode == "0" on accepted request
    # If they return an error structure, we still return it for debugging/upstream handling.
    return data
