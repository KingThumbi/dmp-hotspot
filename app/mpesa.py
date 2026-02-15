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
from app.models import MpesaPayment

mpesa_bp = Blueprint("mpesa", __name__, url_prefix="/api/mpesa")


@mpesa_bp.errorhandler(Exception)
def mpesa_bp_errorhandler(e):
    current_app.logger.exception("Unhandled error in /api/mpesa/*")
    return jsonify({"ok": False, "error": "Internal Server Error"}), 500


# ======================================================
# Helpers / Config
# ======================================================
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
    env = os.getenv("MPESA_ENV", "sandbox").strip().lower()
    if env not in {"sandbox", "production"}:
        raise RuntimeError("MPESA_ENV must be 'sandbox' or 'production'")

    return MpesaConfig(
        env=env,
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
        "AccountReference": (account_ref or cfg.account_ref),
        "TransactionDesc": cfg.tx_desc,
    }

    if cfg.timeout_url:
        payload["QueueTimeOutURL"] = cfg.timeout_url

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code >= 400:
        current_app.logger.error("STK push failed status=%s body=%s payload=%s", r.status_code, r.text, payload)
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
    """UTC-naive timestamp (matches your DB convention for subscriptions)."""
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
    sub.status = "active"
    if not getattr(sub, "starts_at", None):
        sub.starts_at = now
    sub.expires_at = base + dt.timedelta(minutes=minutes)


# ======================================================
# Reconciliation/Activation helpers
# ======================================================
def mark_payment_failed(
    payment: MpesaPayment,
    *,
    status: str,
    result_code: Optional[int],
    result_desc: str,
    raw: Any,
    now: Optional[dt.datetime] = None,
    bump_reconcile: bool = True,
) -> None:
    """
    Mark payment failed/cancelled/timeout and persist.

    Also updates reconciliation tracking so callers (scheduler/timeout route)
    don't need to do extra commits.

    Args:
      status: "failed" | "cancelled" | "timeout" | etc.
      result_code/result_desc: from callback or stk query (optional)
      raw: payload to store for audit
      now: timezone-aware UTC datetime; defaults to dt.now(UTC)
      bump_reconcile: when True, increments reconcile_attempts and sets last_reconcile_at
    """
    ts = now or dt.datetime.now(dt.timezone.utc)

    payment.status = status
    payment.result_code = result_code
    payment.result_desc = result_desc
    payment.raw_callback = raw
    payment.external_updated_at = ts

    if bump_reconcile:
        payment.reconcile_attempts = int(payment.reconcile_attempts or 0) + 1
        payment.last_reconcile_at = ts

    # Keep updated_at consistent when you do non-callback updates
    try:
        payment.updated_at = ts
    except Exception:
        pass

    db.session.add(payment)
    db.session.commit()

def finalize_success_and_activate(
    payment: MpesaPayment,
    *,
    mpesa_receipt: Optional[str],
    paid_at: Optional[dt.datetime],
    raw: Any,
) -> None:
    """
    DB-first finalization, then subscription activation + router hooks.
    Safe to call multiple times.
    """
    # Idempotency: if already success and we have a receipt, do nothing
    if (payment.status or "").strip().lower() in {"success", "reconciled"} and payment.mpesa_receipt:
        return

    payment.status = "success"
    payment.paid_at = paid_at or dt.datetime.now(dt.timezone.utc)
    if mpesa_receipt:
        payment.mpesa_receipt = str(mpesa_receipt)
    payment.raw_callback = raw
    payment.external_updated_at = dt.datetime.now(dt.timezone.utc)

    db.session.add(payment)
    db.session.commit()  # commit first

    _activate_subscription_and_router(payment)


def _activate_subscription_and_router(payment: MpesaPayment) -> None:
    """
    Shared activation logic:
      - extend subscription in DB
      - commit
      - then router hooks via router_actions.reconnect_subscription (best-effort)

    If activation/router fails, mark payment activation_failed (but keep payment success).
    """
    try:
        from app.models import Subscription

        sub = Subscription.query.get(payment.subscription_id) if payment.subscription_id else None
        now = _utcnow_naive()

        if sub:
            _activate_or_extend_subscription(sub, now=now)
            db.session.add(sub)

        db.session.add(payment)
        db.session.commit()

        if not sub:
            return

        router_enabled = bool(current_app.config.get("ROUTER_AGENT_ENABLED", False))
        dry_run = _bool_env("ROUTER_AUTOMATION_DRY_RUN", True)

        if router_enabled:
            try:
                from app.services.router_actions import reconnect_subscription

                reconnect_subscription(sub, reason="payment_received", dry_run=dry_run)
            except Exception:
                current_app.logger.exception("Router reconnect hook failed (activation)")

    except Exception as e:
        try:
            payment.status = "activation_failed"
            payment.activation_attempts = (payment.activation_attempts or 0) + 1
            payment.last_activation_at = dt.datetime.now(dt.timezone.utc)
            payment.activation_error = str(e)
            db.session.add(payment)
            db.session.commit()
        except Exception:
            db.session.rollback()
        raise


# ======================================================
# Routes
# ======================================================
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
    try:
        cfg = load_mpesa_config()
    except Exception as e:
        current_app.logger.exception("M-Pesa config error")
        return jsonify({"ok": False, "error": str(e)}), 500

    data = request.get_json(force=True, silent=True) or {}
    phone_raw = (data.get("phone") or "").strip()
    amount = data.get("amount")

    if not phone_raw or amount is None:
        return jsonify({"ok": False, "error": "phone and amount are required"}), 400

    try:
        phone_254 = normalize_phone_to_254(phone_raw)

        amount_int = int(amount)
        if amount_int <= 0:
            raise ValueError("Amount must be a positive integer.")

        amount_money = Decimal(str(amount_int)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    customer_id = data.get("customer_id")
    subscription_id = data.get("subscription_id")

    account_ref = (data.get("account_ref") or "").strip() or None
    if not account_ref and subscription_id:
        try:
            from app.models import Subscription

            sub = Subscription.query.get(int(subscription_id))
            if sub:
                ident = (sub.identity() or "").strip()
                if ident:
                    account_ref = ident
        except Exception:
            current_app.logger.exception("Failed resolving subscription identity for AccountReference")

    # Create payment row first (audit trail)
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

    # Call Daraja STK push
    try:
        resp = stk_push(cfg=cfg, phone_254=phone_254, amount=amount_int, account_ref=account_ref)
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

    # Update payment with Daraja identifiers + status
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
    DB activate/extend first; router action after DB commit.
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
    if (payment.status or "").strip().lower() in {"success", "reconciled"}:
        try:
            db.session.add(payment)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed committing idempotent callback save")
        return jsonify({"ok": True, "status": "success"}), 200

    if result_code_int == 0:
        receipt = meta.get("MpesaReceiptNumber")
        paid_at = dt.datetime.now(dt.timezone.utc)

        # Amount/phone updates (from callback)
        if meta.get("Amount") is not None:
            try:
                payment.amount = Decimal(str(meta.get("Amount"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except Exception:
                current_app.logger.exception("Failed to parse callback Amount")

        if meta.get("PhoneNumber") is not None:
            payment.phone = str(meta.get("PhoneNumber"))

        try:
            finalize_success_and_activate(
                payment,
                mpesa_receipt=str(receipt) if receipt else None,
                paid_at=paid_at,
                raw=payload,
            )
            return jsonify({"ok": True, "status": "success"}), 200
        except Exception:
            current_app.logger.exception("Payment success finalize/activation failed")
            # Always ACK 200 to Safaricom
            return jsonify({"ok": True, "status": "success"}), 200

    # Failure path
    try:
        mark_payment_failed(
            payment,
            status="cancelled" if result_code_int == 1032 else "failed",
            result_code=result_code_int,
            result_desc=result_desc or "Payment failed",
            raw=payload,
            now=dt.datetime.now(dt.timezone.utc),
            bump_reconcile=False,  # LIVE callback, not reconciliation
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed saving failed payment callback")

        final_status = "cancelled" if result_code_int == 1032 else "failed"
        return jsonify({"ok": True, "status": final_status, "result_desc": result_desc}), 200


@mpesa_bp.post("/timeout")
def mpesa_timeout_route():
    """
    Safaricom QueueTimeOutURL endpoint for STK Push.
    MUST return 200 OK quickly.

    We best-effort map to a payment by CheckoutRequestID and mark it as timeout.
    This is considered "reconcile-like", so we bump reconcile counters.
    """
    payload = request.get_json(force=True, silent=True) or {}

    checkout_id = (
        payload.get("CheckoutRequestID")
        or payload.get("checkoutRequestID")
        or ((payload.get("Body") or {}).get("stkCallback") or {}).get("CheckoutRequestID")
    )

    now = dt.datetime.now(dt.timezone.utc)

    try:
        if not checkout_id:
            current_app.logger.warning("STK timeout received without CheckoutRequestID: %s", payload)
            return jsonify({"ok": True, "status": "received_unmatched"}), 200

        payment = (
            MpesaPayment.query
            .filter(MpesaPayment.checkout_request_id == str(checkout_id))
            .order_by(MpesaPayment.id.desc())
            .first()
        )

        if not payment:
            current_app.logger.warning("Unmatched STK timeout checkout_id=%s payload=%s", checkout_id, payload)
            return jsonify({"ok": True, "status": "received_unmatched", "checkout_request_id": checkout_id}), 200

        current_status = (payment.status or "").strip().lower()
        if current_status in {"success", "reconciled"}:
            # still store payload for audit, but don't change status
            payment.raw_callback = payload
            payment.external_updated_at = now
            db.session.add(payment)
            db.session.commit()
            return jsonify({"ok": True, "status": current_status}), 200

        # If still pending (or anything not finalized), mark as timeout via helper
        mark_payment_failed(
            payment,
            status="timeout",
            result_code=None,
            result_desc="Queue timeout (Safaricom QueueTimeOutURL).",
            raw=payload,
            now=now,
            bump_reconcile=True,
        )

        return jsonify({"ok": True, "status": "timeout"}), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed handling STK timeout callback")
        return jsonify({"ok": True, "status": "error_ack"}), 200
