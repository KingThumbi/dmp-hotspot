# app/services/mpesa_daraja.py
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

import requests


@dataclass(frozen=True)
class MpesaConfig:
    env: str
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    callback_url: str
    account_ref: str
    desc: str


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if val is None or not val.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return val.strip()


def load_mpesa_config() -> MpesaConfig:
    env = (os.getenv("MPESA_ENV") or "sandbox").strip().lower()
    if env not in {"sandbox", "production"}:
        raise RuntimeError("MPESA_ENV must be 'sandbox' or 'production'")

    return MpesaConfig(
        env=env,
        consumer_key=_require_env("MPESA_CONSUMER_KEY"),
        consumer_secret=_require_env("MPESA_CONSUMER_SECRET"),
        shortcode=_require_env("MPESA_SHORTCODE"),
        passkey=_require_env("MPESA_PASSKEY"),
        callback_url=_require_env("MPESA_CALLBACK_URL"),
        account_ref=(os.getenv("MPESA_STK_ACCOUNT_REF") or "DmpolinConnect").strip(),
        desc=(os.getenv("MPESA_STK_DESC") or "Internet subscription").strip(),
    )


def _mpesa_base_url(env: str) -> str:
    return "https://api.safaricom.co.ke" if env == "production" else "https://sandbox.safaricom.co.ke"


def get_access_token(cfg: MpesaConfig) -> str:
    url = f"{_mpesa_base_url(cfg.env)}/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(cfg.consumer_key, cfg.consumer_secret), timeout=30)
    r.raise_for_status()
    data = r.json() or {}
    token = data.get("access_token")
    if not token:
        raise RuntimeError("OAuth response missing access_token")
    return token


def _stk_password(shortcode: str, passkey: str, timestamp: str) -> str:
    raw = f"{shortcode}{passkey}{timestamp}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def stk_push(*, phone_254: str, amount: int, cfg: MpesaConfig | None = None) -> Dict[str, Any]:
    """
    Initiate STK push.
    phone_254 must be in 2547XXXXXXXX format.
    """
    amount_int = int(amount)
    if amount_int <= 0:
        raise ValueError("amount must be a positive integer")

    cfg = cfg or load_mpesa_config()

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    password = _stk_password(cfg.shortcode, cfg.passkey, timestamp)
    token = get_access_token(cfg)

    url = f"{_mpesa_base_url(cfg.env)}/mpesa/stkpush/v1/processrequest"
    payload: Dict[str, Any] = {
        "BusinessShortCode": cfg.shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount_int,
        "PartyA": phone_254,
        "PartyB": cfg.shortcode,
        "PhoneNumber": phone_254,
        "CallBackURL": cfg.callback_url,
        "AccountReference": cfg.account_ref,
        "TransactionDesc": cfg.desc,
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json() or {}
