from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, jsonify, request

from .extensions import db, limiter
from .models import Customer, Package, Subscription, Transaction
from .mpesa import stk_push
from .router_agent import agent_enable

api = Blueprint("api", __name__)


# =========================================================
# Helpers
# =========================================================
def normalize_phone(phone: str) -> str:
    """
    Normalize Kenyan phone numbers to 2547XXXXXXXX format.
    Accepts: 0712..., 712..., +254712..., 254712...
    """
    p = re.sub(r"\s+", "", (phone or "")).replace("+", "")
    if p.startswith("0") and len(p) == 10:
        return "254" + p[1:]
    if p.startswith("7") and len(p) == 9:
        return "254" + p
    if p.startswith("254") and len(p) == 12:
        return p
    raise ValueError("Invalid phone number. Use 07XXXXXXXX, 7XXXXXXXX, or 2547XXXXXXXX.")


def _json() -> Dict[str, Any]:
    return request.get_json(silent=True) or {}


def _safe_commit() -> None:
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


# =========================================================
# Routes
# =========================================================
@api.get("/health")
def health():
    return jsonify({"ok": True})


@api.get("/packages")
def packages():
    pkgs = Package.query.order_by(Package.price_kes.asc()).all()
    return jsonify(
        [
            {
                "code": p.code,
                "name": p.name,
                "price_kes": p.price_kes,
                "duration_minutes": p.duration_minutes,
                "mikrotik_profile": p.mikrotik_profile,
            }
            for p in pkgs
        ]
    )


@api.post("/pay")
@limiter.limit("5 per minute")
def pay():
    """
    Create a pending Transaction + pending Subscription, then initiate STK push.
    Returns CheckoutRequestID.
    """
    data = _json()
    raw_phone = (data.get("phone") or "").strip()
    pkg_code = (data.get("package") or "").strip()

    if not raw_phone or not pkg_code:
        return jsonify({"ok": False, "error": "phone and package are required"}), 400

    try:
        phone = normalize_phone(raw_phone)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    pkg = Package.query.filter_by(code=pkg_code).first()
    if not pkg:
        return jsonify({"ok": False, "error": "Invalid package"}), 400

    # Find/create customer
    cust = Customer.query.filter_by(phone=phone).first()
    if not cust:
        cust = Customer(phone=phone)
        db.session.add(cust)
        db.session.flush()  # cust.id

    # Idempotency: if there's an in-flight tx with checkout id, reuse it
    recent_tx: Optional[Transaction] = (
        Transaction.query.filter_by(customer_id=cust.id, package_id=pkg.id, status="pending")
        .order_by(Transaction.id.desc())
        .first()
    )
    if recent_tx and recent_tx.checkout_request_id:
        _safe_commit()
        return jsonify({"ok": True, "checkout_request_id": recent_tx.checkout_request_id})

    # Create pending transaction
    tx = Transaction(
        customer_id=cust.id,
        package_id=pkg.id,
        amount=pkg.price_kes,
        status="pending",
    )
    db.session.add(tx)
    db.session.flush()  # tx.id

    # Avoid stacking many pending subscriptions: reuse latest pending sub
    existing_pending: Optional[Subscription] = (
        Subscription.query.filter_by(customer_id=cust.id, package_id=pkg.id, status="pending")
        .order_by(Subscription.id.desc())
        .first()
    )

    if existing_pending:
        sub = existing_pending
        sub.last_tx_id = tx.id
        sub.router_username = phone
    else:
        sub = Subscription(
            customer_id=cust.id,
            package_id=pkg.id,
            last_tx_id=tx.id,
            router_username=phone,
            status="pending",
        )
        db.session.add(sub)

    _safe_commit()  # commit before external request

    # Initiate STK push
    try:
        resp = stk_push(current_app, phone, pkg.price_kes) or {}
    except Exception as e:
        tx.status = "failed"
        tx.result_desc = f"STK push error: {e}"
        _safe_commit()
        return jsonify({"ok": False, "error": "STK push failed"}), 502

    tx.checkout_request_id = resp.get("CheckoutRequestID")
    tx.merchant_request_id = resp.get("MerchantRequestID")

    if not tx.checkout_request_id:
        tx.status = "failed"
        tx.result_desc = "STK push did not return CheckoutRequestID"
        _safe_commit()
        return jsonify({"ok": False, "error": "STK push failed"}), 502

    _safe_commit()
    return jsonify({"ok": True, "checkout_request_id": tx.checkout_request_id})


@api.post("/mpesa/callback")
@limiter.limit("120 per minute")
def mpesa_callback():
    """
    Safaricom STK callback endpoint.
    - Stores raw callback JSON (string) for audit
    - Updates transaction status (idempotent)
    - Activates / extends subscription on success
    - Optionally enables router access (MIKROTIK_ENABLED)
    """
    payload = request.get_json(silent=True) or {}
    stk = (payload.get("Body") or {}).get("stkCallback") or {}

    checkout_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    result_desc = stk.get("ResultDesc")

    if not checkout_id:
        return jsonify({"ok": True})

    tx = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
    if not tx:
        return jsonify({"ok": True})

    # Audit fields (raw_callback_json is Text column)
    tx.raw_callback_json = json.dumps(payload)
    tx.result_code = str(result_code) if result_code is not None else None
    tx.result_desc = result_desc

    # Idempotency: if already success, do nothing
    if tx.status == "success":
        _safe_commit()
        return jsonify({"ok": True})

    # Failure
    if str(result_code) != "0":
        tx.status = "failed"
        _safe_commit()
        return jsonify({"ok": True})

    # Success
    tx.status = "success"

    # Receipt number (if present)
    receipt = None
    items = ((stk.get("CallbackMetadata") or {}).get("Item")) or []
    for it in items:
        if it.get("Name") == "MpesaReceiptNumber":
            receipt = it.get("Value")
            break
    if receipt:
        tx.mpesa_receipt = receipt

    # Linked subscription (by last_tx_id)
    sub: Optional[Subscription] = (
        Subscription.query.filter_by(last_tx_id=tx.id).order_by(Subscription.id.desc()).first()
    )
    if not sub:
        _safe_commit()
        return jsonify({"ok": True})

    pkg = db.session.get(Package, sub.package_id)
    if not pkg:
        _safe_commit()
        return jsonify({"ok": True})

    now = datetime.utcnow()

    # Extend if still active; otherwise start from now
    base = sub.expires_at if (sub.expires_at and sub.expires_at > now) else now

    sub.status = "active"
    sub.starts_at = sub.starts_at or now
    sub.expires_at = base + timedelta(minutes=pkg.duration_minutes)

    if current_app.config.get("MIKROTIK_ENABLED", False):
        agent_enable(current_app, sub.router_username, pkg.mikrotik_profile, pkg.duration_minutes)

    _safe_commit()
    return jsonify({"ok": True})
