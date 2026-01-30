# app/routes.py
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy import desc, func

from .extensions import db
from .models import Customer, Package, Subscription, Transaction

# =========================================================
# Blueprint
# =========================================================
main = Blueprint("main", __name__)
NAIROBI = ZoneInfo("Africa/Nairobi")


# =========================================================
# Time helpers
# =========================================================
def now_utc_naive() -> datetime:
    """DB uses naive UTC via datetime.utcnow(). Keep consistent."""
    return datetime.utcnow()


def nairobi_range_starts_utc_naive() -> Dict[str, datetime]:
    """
    Returns UTC-naive datetimes that match Nairobi day/week/month boundaries.
    Useful for revenue totals (only if you ever show them on public pages).
    """
    now_local = datetime.now(NAIROBI)

    start_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week_local = start_today_local - timedelta(days=start_today_local.weekday())  # Monday
    start_month_local = start_today_local.replace(day=1)

    def to_utc_naive(dt_local: datetime) -> datetime:
        return dt_local.astimezone(timezone.utc).replace(tzinfo=None)

    return {
        "today": to_utc_naive(start_today_local),
        "week": to_utc_naive(start_week_local),
        "month": to_utc_naive(start_month_local),
    }


def compute_revenue_totals_success_only() -> Dict[str, int]:
    """Revenue totals based on successful transactions only."""
    starts = nairobi_range_starts_utc_naive()

    def _sum_since(dt_utc_naive: datetime) -> int:
        val = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(Transaction.status == "success", Transaction.created_at >= dt_utc_naive)
            .scalar()
        )
        return int(val or 0)

    return {
        "today": _sum_since(starts["today"]),
        "week": _sum_since(starts["week"]),
        "month": _sum_since(starts["month"]),
    }


# =========================================================
# Domain helpers (customers, packages, subscriptions)
# =========================================================
def normalize_phone(phone: str) -> str:
    """
    Normalize Kenyan phone into 2547XXXXXXXX format (best-effort).
    Accepts inputs like:
      - 0712345678
      - 712345678
      - +254712345678
      - 254712345678
    """
    if not phone:
        return ""
    p = phone.strip().replace(" ", "")
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0") and len(p) == 10:
        return "254" + p[1:]
    if p.startswith("7") and len(p) == 9:
        return "254" + p
    if p.startswith("254") and len(p) >= 12:
        return p
    return p


def get_or_create_customer(phone_norm: str) -> Customer:
    cust = Customer.query.filter_by(phone=phone_norm).first()
    if cust:
        return cust
    cust = Customer(phone=phone_norm)
    db.session.add(cust)
    db.session.flush()
    return cust


def get_package_by_code(code: str) -> Package:
    pkg = Package.query.filter_by(code=code).first()
    if not pkg:
        abort(400, description=f"Unknown package code: {code}")
    return pkg


def create_subscription_for_purchase(customer: Customer, package: Package) -> Subscription:
    """
    Create a 'pending' subscription record for this purchase.
    (One subscription row per payment attempt keeps clean audit.)
    """
    sub = Subscription(
        customer_id=customer.id,
        package_id=package.id,
        status="pending",
        router_username=customer.phone,
        starts_at=None,
        expires_at=None,
        last_tx_id=None,
    )
    db.session.add(sub)
    db.session.flush()
    return sub


def apply_success_to_subscription(sub: Subscription, package: Package, tx: Transaction) -> None:
    """Activate subscription from now and set expiry based on package duration."""
    now = now_utc_naive()
    sub.status = "active"
    sub.starts_at = now
    sub.expires_at = now + timedelta(minutes=int(package.duration_minutes))
    sub.last_tx_id = tx.id


# =========================================================
# M-Pesa Daraja (OAuth + STK Push)
# =========================================================
def _daraja_urls() -> Dict[str, str]:
    env = (current_app.config.get("MPESA_ENV") or "sandbox").lower()
    if env == "production":
        return {
            "oauth": "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            "stk": "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        }
    return {
        "oauth": "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        "stk": "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
    }


def _daraja_access_token() -> Tuple[bool, Dict[str, Any]]:
    key = (current_app.config.get("MPESA_CONSUMER_KEY") or "").strip()
    secret = (current_app.config.get("MPESA_CONSUMER_SECRET") or "").strip()
    if not key or not secret:
        return False, {"error": "MPESA_CONSUMER_KEY/MPESA_CONSUMER_SECRET not configured."}

    urls = _daraja_urls()
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    try:
        r = requests.get(urls["oauth"], headers=headers, timeout=30)
        data = r.json()
        if r.status_code >= 400:
            return False, {"error": "OAuth token request failed", "status_code": r.status_code, "response": data}
        token = data.get("access_token")
        if not token:
            return False, {"error": "No access_token in OAuth response", "response": data}
        return True, {"access_token": token}
    except Exception as e:
        return False, {"error": str(e)}


def stk_push(phone_2547: str, amount: int, package_code: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Initiate STK push via Safaricom Daraja.
    Returns: (ok, response_json_or_error)
    """
    shortcode = (current_app.config.get("MPESA_SHORTCODE") or "").strip()
    passkey = (current_app.config.get("MPESA_PASSKEY") or "").strip()
    callback_url = (current_app.config.get("MPESA_CALLBACK_URL") or "").strip()

    account_ref = (current_app.config.get("MPESA_ACCOUNT_REF") or "DMPOLIN-HOTSPOT").strip()
    tx_desc = (current_app.config.get("MPESA_TX_DESC") or "Dmpolin Connect Hotspot").strip()

    if not shortcode or not passkey or not callback_url:
        return False, {"error": "MPESA_SHORTCODE/MPESA_PASSKEY/MPESA_CALLBACK_URL not configured."}

    ok, tok = _daraja_access_token()
    if not ok:
        return False, tok

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    body = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",  # change to CustomerBuyGoodsOnline if you use Till
        "Amount": int(amount),
        "PartyA": phone_2547,
        "PartyB": shortcode,
        "PhoneNumber": phone_2547,
        "CallBackURL": callback_url,
        "AccountReference": account_ref,
        "TransactionDesc": f"{tx_desc} ({package_code})",
    }

    urls = _daraja_urls()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok['access_token']}"}

    try:
        r = requests.post(urls["stk"], json=body, headers=headers, timeout=30)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
        if r.status_code >= 400:
            return False, {"error": "STK push request failed", "status_code": r.status_code, "response": data}
        return True, data
    except Exception as e:
        return False, {"error": str(e)}


def _extract_stk_receipt_from_callback(payload: Dict[str, Any]) -> Optional[str]:
    """
    Standard callback structure:
      Body.stkCallback.CallbackMetadata.Item[{Name:'MpesaReceiptNumber', Value:'...'}]
    """
    stk = payload.get("Body", {}).get("stkCallback", {}) or {}
    meta = stk.get("CallbackMetadata", {}) or {}
    items = meta.get("Item", []) or []
    for item in items:
        if item.get("Name") == "MpesaReceiptNumber":
            return item.get("Value")
    return None


# =========================================================
# Public routes
# =========================================================
@main.get("/")
def home():
    return redirect(url_for("main.pay_page"))


@main.get("/pay")
def pay_page():
    packages = Package.query.order_by(Package.price_kes.asc()).all()
    return render_template("pay.html", packages=packages)


@main.post("/pay")
def pay():
    """
    Initiate payment (STK push).
    Expects JSON:
      { "phone": "0712...", "package": "weekly_1" }

    Always creates:
      Customer + Subscription(pending) + Transaction(pending)
    Then:
      - If STK starts: keep tx pending and store response
      - If STK fails: mark tx failed and store error response
    """
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(str(data.get("phone", "")).strip())
    package_code = str(data.get("package", "")).strip()

    if not phone or not package_code:
        return jsonify({"ok": False, "error": "phone and package are required"}), 400

    package = get_package_by_code(package_code)
    customer = get_or_create_customer(phone)
    subscription = create_subscription_for_purchase(customer, package)

    # Always create tx first (audit trail)
    tx = Transaction(
        customer_id=customer.id,
        package_id=package.id,
        amount=int(package.price_kes),
        status="pending",
        checkout_request_id=None,
        merchant_request_id=None,
        mpesa_receipt=None,
        result_code=None,
        result_desc=None,
        raw_callback_json=None,
    )
    db.session.add(tx)
    db.session.flush()

    subscription.last_tx_id = tx.id
    db.session.flush()

    ok, resp = stk_push(phone_2547=customer.phone, amount=tx.amount, package_code=package.code)

    if ok:
        tx.checkout_request_id = resp.get("CheckoutRequestID") or resp.get("checkoutRequestID") or tx.checkout_request_id
        tx.merchant_request_id = resp.get("MerchantRequestID") or resp.get("merchantRequestID") or tx.merchant_request_id
        tx.result_desc = resp.get("CustomerMessage") or resp.get("ResponseDescription") or "STK Push initiated"

        # Store response for “View callback JSON”
        try:
            tx.raw_callback_json = json.dumps(resp, ensure_ascii=False)
        except Exception:
            tx.raw_callback_json = str(resp)

        db.session.commit()
        return jsonify(
            {
                "ok": True,
                "transaction_id": tx.id,
                "checkout_request_id": tx.checkout_request_id,
                "merchant_request_id": tx.merchant_request_id,
                "message": tx.result_desc,
            }
        ), 200

    # STK failed: keep audit
    tx.status = "failed"
    if isinstance(resp, dict):
        tx.result_desc = resp.get("error") or "STK push failed"
        try:
            tx.raw_callback_json = json.dumps(resp, ensure_ascii=False)
        except Exception:
            tx.raw_callback_json = str(resp)
    else:
        tx.result_desc = str(resp)[:255]
        tx.raw_callback_json = str(resp)

    db.session.commit()
    return jsonify(
        {"ok": False, "error": "STK push failed", "details": resp, "transaction_id": tx.id}
    ), 502


@main.post("/mpesa/callback")
def mpesa_callback():
    """
    Receives M-Pesa callback.
    Updates Transaction:
      - status success/failed
      - result_code/result_desc
      - mpesa_receipt (if success)
      - raw_callback_json (stored)
    Activates linked subscription where Subscription.last_tx_id == tx.id
    """
    payload = request.get_json(force=True, silent=True) or {}
    raw_text = json.dumps(payload, ensure_ascii=False)

    stk = payload.get("Body", {}).get("stkCallback", {}) or {}
    checkout_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    result_desc = stk.get("ResultDesc")

    if not checkout_id:
        return jsonify({"ok": True, "note": "No CheckoutRequestID"}), 200

    tx = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
    if not tx:
        return jsonify({"ok": True, "note": "Transaction not found"}), 200

    tx.raw_callback_json = raw_text
    tx.result_code = str(result_code) if result_code is not None else None
    tx.result_desc = str(result_desc)[:255] if result_desc else None

    if str(result_code) == "0":
        tx.status = "success"
        tx.mpesa_receipt = _extract_stk_receipt_from_callback(payload)

        sub = (
            Subscription.query.filter_by(last_tx_id=tx.id)
            .order_by(desc(Subscription.id))
            .first()
        )
        if sub:
            apply_success_to_subscription(sub, tx.package, tx)
    else:
        tx.status = "failed"

    db.session.commit()
    return jsonify({"ok": True}), 200


# =========================================================
# Health
# =========================================================
@main.get("/health")
def health():
    return jsonify({"ok": True, "time_utc": now_utc_naive().isoformat()}), 200
