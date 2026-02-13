# app/mpesa.py
from __future__ import annotations

import base64
import datetime as dt
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple

import requests
from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import MpesaPayment  # must match your model/table name

mpesa_bp = Blueprint("mpesa", __name__, url_prefix="/api/mpesa")

@mpesa_bp.errorhandler(Exception)
def mpesa_bp_errorhandler(e):
    current_app.logger.exception("Unhandled error in /api/mpesa/*")
    return jsonify({"ok": False, "error": "Internal Server Error"}), 500

# ----------------------------
# Helpers / Config
# ----------------------------
@dataclass(frozen=True)
class MpesaConfig:
    env: str
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    callback_url: str
    timeout_url: str
    account_ref: str
    tx_desc: str


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _base_url(env: str) -> str:
    env = (env or "").strip().lower()
    return "https://sandbox.safaricom.co.ke" if env == "sandbox" else "https://api.safaricom.co.ke"


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if val is None or not val.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return val.strip()


def load_mpesa_config() -> MpesaConfig:
    """
    Loads required Daraja config from environment variables.
    Keeps defaults safe and explicit.
    """
    return MpesaConfig(
        env=os.getenv("MPESA_ENV", "sandbox").strip(),
        consumer_key=_require_env("MPESA_CONSUMER_KEY"),
        consumer_secret=_require_env("MPESA_CONSUMER_SECRET"),
        shortcode=_require_env("MPESA_SHORTCODE"),
        passkey=_require_env("MPESA_PASSKEY"),
        callback_url=_require_env("MPESA_CALLBACK_URL"),
        timeout_url=os.getenv("MPESA_TIMEOUT_URL", "").strip(),
        account_ref=os.getenv("MPESA_STK_ACCOUNT_REF", "DmpolinConnect").strip(),
        tx_desc=os.getenv("MPESA_STK_DESC", "Internet subscription").strip(),
    )


def normalize_phone_to_254(phone: str) -> str:
    """
    Accepts formats like:
      - 0712345678
      - 712345678
      - +254712345678
      - 254712345678
    Returns: 2547XXXXXXXX (12 digits)
    """
    p = (phone or "").strip().replace(" ", "")
    if p.startswith("+"):
        p = p[1:]

    if p.startswith("0") and len(p) == 10:
        p = "254" + p[1:]
    elif len(p) == 9 and p.startswith("7"):
        p = "254" + p

    if not (p.isdigit() and p.startswith("254") and len(p) == 12):
        raise ValueError("Phone must be a valid Kenyan number (e.g. 0712345678 or 254712345678).")
    return p


def _oauth_token(cfg: MpesaConfig) -> str:
    url = f"{_base_url(cfg.env)}/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(cfg.consumer_key, cfg.consumer_secret), timeout=30)
    if r.status_code >= 400:
        # Helpful logs when credentials/env are wrong
        current_app.logger.error("OAuth failed status=%s body=%s", r.status_code, r.text)
    r.raise_for_status()
    data = r.json() or {}
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Safaricom OAuth response missing access_token.")
    return token


def _stk_password(shortcode: str, passkey: str, timestamp: str) -> str:
    raw = f"{shortcode}{passkey}{timestamp}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def stk_push(
    cfg: MpesaConfig,
    phone_254: str,
    amount: int,
    *,
    account_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initiate STK push.
    Returns Safaricom JSON response (includes CheckoutRequestID, MerchantRequestID on success).
    """
    amount_int = int(amount)
    if amount_int <= 0:
        raise ValueError("amount must be a positive integer.")

    url = f"{_base_url(cfg.env)}/mpesa/stkpush/v1/processrequest"

    timestamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    password = _stk_password(cfg.shortcode, cfg.passkey, timestamp)

    token = _oauth_token(cfg)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

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
        # ✅ dynamic account reference (pppoe/hotspot identity) if provided
        "AccountReference": (account_ref or cfg.account_ref),
        "TransactionDesc": cfg.tx_desc,
    }

    # Queue timeout URL is optional
    if cfg.timeout_url:
        payload["QueueTimeOutURL"] = cfg.timeout_url

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code >= 400:
        current_app.logger.error(
            "STK push failed status=%s body=%s payload=%s",
            r.status_code,
            r.text,
            payload,
        )
    r.raise_for_status()
    return r.json() or {}


def _extract_stk_callback(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[int], str, Dict[str, Any]]:
    """
    Returns: (checkout_request_id, result_code_int, result_desc, metadata_map)
    """
    stk = (payload.get("Body") or {}).get("stkCallback") or {}
    checkout_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    result_desc = stk.get("ResultDesc") or ""

    meta_items = (stk.get("CallbackMetadata") or {}).get("Item") or []
    meta_map: Dict[str, Any] = {}
    for item in meta_items:
        if isinstance(item, dict) and item.get("Name"):
            meta_map[item["Name"]] = item.get("Value")

    try:
        result_code_int = int(result_code) if result_code is not None else None
    except Exception:
        result_code_int = None

    return checkout_id, result_code_int, result_desc, meta_map


def _utcnow_naive() -> dt.datetime:
    """UTC-naive timestamp (matches your DB convention)."""
    return dt.datetime.utcnow()


def _activate_or_extend_subscription(sub, *, now: dt.datetime) -> None:
    """
    Time-based billing:
    - If current expires_at is in the future, extend from expires_at
    - Else extend from now
    """
    minutes = int(getattr(sub.package, "duration_minutes", 0) or 0)
    if minutes <= 0:
        raise RuntimeError("Package duration_minutes is missing/invalid")

    base = sub.expires_at if (sub.expires_at and sub.expires_at > now) else now
    new_expires = base + dt.timedelta(minutes=minutes)

    sub.status = "active"
    if not getattr(sub, "starts_at", None):
        sub.starts_at = now
    sub.expires_at = new_expires


def _hotspot_enable_now(app, sub, *, tx_ref: str) -> None:
    """
    Immediate hotspot enable:
      - ensure user exists + enabled with correct profile
      - kick active sessions so policy applies immediately
    """
    from app.services.mikrotik_hotspot import ensure_hotspot_user, kick_hotspot_active

    username = (getattr(sub, "hotspot_username", "") or "").strip()
    profile = (getattr(getattr(sub, "package", None), "mikrotik_profile", "") or "").strip()

    if not username or not profile:
        current_app.logger.warning(
            "Hotspot router enable skipped (missing username/profile) sub_id=%s username=%s profile=%s",
            getattr(sub, "id", None),
            username or "-",
            profile or "-",
        )
        return

    ensure_hotspot_user(
        app,
        username=username,
        profile=profile,
        expires_at=sub.expires_at,
        comment_extra=f"tx={tx_ref}",
    )
    kick_hotspot_active(app, username)


# ----------------------------
# Routes
# ----------------------------
@mpesa_bp.get("/ping")
def mpesa_ping():
    return jsonify({"ok": True, "where": "mpesa_bp", "prefix": "/api/mpesa"}), 200


@mpesa_bp.post("/stkpush")
def mpesa_stkpush_route():
    """
    Request body:
      { "phone": "0712345678", "amount": 1000, "customer_id": 1, "subscription_id": 6, "account_ref": "optional" }

    Notes:
    - customer_id/subscription_id are optional but recommended for linking later.
    - We create a payment row first for audit, then update it with CheckoutRequestID.
    - AccountReference precedence:
        1) data.account_ref (if provided)
        2) subscription.identity() (pppoe_username/hotspot_username) if subscription_id provided
        3) cfg.account_ref fallback inside stk_push
    """
    # 1) Load config
    try:
        cfg = load_mpesa_config()
    except Exception as e:
        current_app.logger.exception("M-Pesa config error")
        return jsonify({"ok": False, "error": str(e)}), 500

    # 2) Parse request body
    data = request.get_json(force=True, silent=True) or {}
    phone_raw = (data.get("phone") or "").strip()
    amount = data.get("amount")

    if not phone_raw or amount is None:
        return jsonify({"ok": False, "error": "phone and amount are required"}), 400

    # 3) Validate and normalize
    try:
        phone_254 = normalize_phone_to_254(phone_raw)

        amount_int = int(amount)
        if amount_int <= 0:
            raise ValueError("Amount must be a positive integer.")

        # Store Decimal(12,2) in DB
        amount_money = Decimal(str(amount_int)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    # 4) Optional linking fields
    customer_id = data.get("customer_id")
    subscription_id = data.get("subscription_id")

    # 5) Resolve AccountReference (optional, dynamic)
    #    First: explicit input; else: subscription identity; else: stk_push will fallback to cfg.account_ref
    account_ref = (data.get("account_ref") or "").strip() or None
    if not account_ref and subscription_id:
        try:
            from app.models import Subscription  # local import avoids circulars

            sub = Subscription.query.get(int(subscription_id))
            if sub:
                ident = (sub.identity() or "").strip()
                if ident:
                    account_ref = ident
        except Exception:
            current_app.logger.exception("Failed resolving subscription identity for AccountReference")

    # 6) Create payment row first (audit trail)
    payment = MpesaPayment(
        customer_id=customer_id,
        subscription_id=subscription_id,
        phone=phone_254,
        amount=amount_money,
        status="pending",
        raw_callback=None,
    )
    db.session.add(payment)
    db.session.commit()

    # 7) Call Daraja STK push
    try:
        resp = stk_push(
            cfg=cfg,
            phone_254=phone_254,
            amount=amount_int,          # Daraja expects int
            account_ref=account_ref,    # can be None
        )
    except requests.HTTPError as e:
        payment.status = "failed"
        payment.raw_callback = {"error": "http_error", "details": str(e)}
        db.session.commit()
        current_app.logger.exception("STK push HTTP error")
        return jsonify({"ok": False, "error": "STK push failed", "payment_id": payment.id}), 502
    except Exception as e:
        payment.status = "failed"
        payment.raw_callback = {"error": "exception", "details": str(e)}
        db.session.commit()
        current_app.logger.exception("STK push error")
        return jsonify({"ok": False, "error": "STK push failed", "payment_id": payment.id}), 500

    # 8) Update payment with Daraja identifiers + status
    payment.checkout_request_id = resp.get("CheckoutRequestID")
    payment.merchant_request_id = resp.get("MerchantRequestID")

    if resp.get("ResponseCode") == "0":
        payment.status = "pending"
    else:
        payment.status = "failed"
        payment.raw_callback = {"daraja_response": resp}

    db.session.commit()

    return jsonify({"ok": True, "payment_id": payment.id, "daraja": resp}), 200

@mpesa_bp.post("/callback")
def mpesa_callback_route():
    """
    Safaricom STK callback endpoint.
    MUST always return 200 OK quickly.
    DB activate/extend first; router enable after DB commit.
    """
    payload = request.get_json(force=True, silent=True) or {}
    checkout_id, result_code_int, result_desc, meta = _extract_stk_callback(payload)

    if not checkout_id:
        current_app.logger.warning("Callback missing CheckoutRequestID: %s", payload)
        return jsonify({"ok": True, "status": "received_unmatched"}), 200

    # Load + lock payment row to prevent race/double-extend
    payment = (
        db.session.query(MpesaPayment)
        .filter(MpesaPayment.checkout_request_id == checkout_id)
        .order_by(MpesaPayment.id.desc())
        .with_for_update(of=MpesaPayment, nowait=False)
        .first()
    )

    if not payment:
        current_app.logger.warning("Unmatched callback checkout_id=%s", checkout_id)
        return jsonify({"ok": True, "status": "received_unmatched", "checkout_request_id": checkout_id}), 200

    # Always store raw callback for audit
    payment.raw_callback = payload

    # Idempotency: already success? ACK and exit (do NOT extend again)
    if (payment.status or "").strip().lower() == "success":
        try:
            db.session.add(payment)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed committing idempotent callback save")
        return jsonify({"ok": True, "status": "success"}), 200

    # --------------------
    # Success path
    # --------------------
    if result_code_int == 0:
        payment.status = "success"
        payment.paid_at = dt.datetime.now(dt.timezone.utc)

        receipt = meta.get("MpesaReceiptNumber")
        if receipt:
            payment.mpesa_receipt = str(receipt)

        if meta.get("Amount") is not None:
            payment.amount = Decimal(str(meta.get("Amount"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if meta.get("PhoneNumber") is not None:
            # callback phone might be numeric
            payment.phone = str(meta.get("PhoneNumber"))

        # Activate/extend subscription, commit DB, then router enable
        try:
            from app.models import Subscription  # local import to avoid circulars

            sub = Subscription.query.get(payment.subscription_id) if payment.subscription_id else None
            now = _utcnow_naive()
            app_obj = current_app._get_current_object()

            if sub:
                _activate_or_extend_subscription(sub, now=now)
                db.session.add(sub)

            db.session.add(payment)
            db.session.commit()

            # Router actions AFTER commit (guarded)
            if sub:
                tx_ref = payment.mpesa_receipt or checkout_id or f"pay_id={payment.id}"

                # Hotspot immediate enable
                if (getattr(sub, "service_type", "") or "").strip().lower() == "hotspot":
                    try:
                        _hotspot_enable_now(app_obj, sub, tx_ref=tx_ref)
                    except Exception:
                        current_app.logger.exception("Hotspot router enable hook failed (payment success)")

                # Optional generic reconnect hook (PPPoE etc.)
                enabled = _bool_env("ROUTER_AUTOMATION_ENABLED", False)
                dry_run = _bool_env("ROUTER_AUTOMATION_DRY_RUN", True)
                if enabled:
                    try:
                        from app.services.router_actions import reconnect_subscription
                        reconnect_subscription(sub, reason="payment_received", dry_run=dry_run)
                    except Exception:
                        current_app.logger.exception("Router reconnect hook failed")

            return jsonify({"ok": True, "status": "success"}), 200

        except Exception:
            # Payment still success; persist it even if activation/router fails
            current_app.logger.exception("Payment success but subscription/router activation failed")
            try:
                db.session.rollback()
            except Exception:
                pass
            try:
                payment.status = "success"
                db.session.add(payment)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({"ok": True, "status": "success"}), 200

    # --------------------
    # Failure path
    # --------------------
    try:
        payment.status = "failed"
        db.session.add(payment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed saving failed payment callback")

    return jsonify({"ok": True, "status": "failed", "result_desc": result_desc}), 200
