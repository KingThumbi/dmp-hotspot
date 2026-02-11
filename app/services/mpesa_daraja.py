from __future__ import annotations

import base64
import os
from datetime import datetime
import requests


def _mpesa_base_url() -> str:
    env = (os.getenv("MPESA_ENV") or "sandbox").strip().lower()
    if env == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def _basic_auth() -> str:
    key = os.getenv("MPESA_CONSUMER_KEY", "")
    secret = os.getenv("MPESA_CONSUMER_SECRET", "")
    raw = f"{key}:{secret}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def get_access_token() -> str:
    url = f"{_mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    headers = {"Authorization": f"Basic {_basic_auth()}"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _stk_password(shortcode: str, passkey: str, timestamp: str) -> str:
    raw = f"{shortcode}{passkey}{timestamp}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def stk_push(phone: str, amount: int) -> dict:
    shortcode = os.getenv("MPESA_SHORTCODE", "").strip()
    passkey = os.getenv("MPESA_PASSKEY", "").strip()
    callback_url = os.getenv("MPESA_CALLBACK_URL", "").strip()
    account_ref = os.getenv("MPESA_STK_ACCOUNT_REF", "DmpolinConnect").strip()
    desc = os.getenv("MPESA_STK_DESC", "Internet subscription").strip()

    # timestamp format: YYYYMMDDHHMMSS
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    password = _stk_password(shortcode, passkey, timestamp)

    token = get_access_token()
    url = f"{_mpesa_base_url()}/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_ref,
        "TransactionDesc": desc,
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()
