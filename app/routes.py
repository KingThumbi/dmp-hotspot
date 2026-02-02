# app/routes.py
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy import desc, func

from .extensions import db
from .models import Customer, Package, Subscription, Transaction

# =========================================================
# Blueprint + Logging
# =========================================================
main = Blueprint("main", __name__)
NAIROBI = ZoneInfo("Africa/Nairobi")
log = logging.getLogger("app.routes")

FINAL_TX_STATUSES = {"success", "failed"}


# =========================================================
# Time helpers
# =========================================================
def now_utc_naive() -> datetime:
    """
    DB stores naive UTC (datetime.utcnow()).
    Always write/read DB timestamps as UTC-naive for consistency.
    """
    return datetime.utcnow()


def nairobi_range_starts_utc_naive() -> Dict[str, datetime]:
    """
    Returns UTC-naive datetimes matching Nairobi day/week/month boundaries.
    Useful for revenue totals.
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
# Domain helpers
# =========================================================
def normalize_phone(phone: str) -> str:
    """
    Normalize Kenyan phone into 2547XXXXXXXX format (best-effort).
    Accepts:
      - 0712345678
      - 712345678
      - +254712345678
      - 254712345678
      - 254 712 345 678
    """
    if not phone:
        return ""
    p = phone.strip().replace(" ", "")
    if p.startswith("+"):
        p = p[1:]

    # 0712...
    if p.startswith("0") and len(p) == 10 and p[1:].isdigit():
        return "254" + p[1:]

    # 712...
    if p.startswith("7") and len(p) == 9 and p.isdigit():
        return "254" + p

    # 2547...
    if p.startswith("254") and len(p) >= 12 and p[3:].isdigit():
        return p

    # fallback: return as-is (lets admin/test handle odd formats)
    return p


def get_or_create_customer(phone_norm: str) -> Customer:
    """Customer keyed by phone (treated as unique)."""
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


def get_active_hotspot_subscription(hotspot_username: str) -> Optional[Subscription]:
    """
    With uq_active_hotspot_username (partial unique index),
    there can be at most ONE active hotspot subscription per hotspot_username.
    """
    return (
        Subscription.query.filter(
            Subscription.service_type == "hotspot",
            Subscription.status == "active",
            Subscription.hotspot_username == hotspot_username,
        )
        .order_by(desc(Subscription.id))
        .first()
    )


def get_or_create_hotspot_entitlement(customer: Customer, package: Package) -> Subscription:
    """
    Hotspot entitlement rule:
      - If an ACTIVE entitlement exists for this hotspot_username, reuse it.
      - Otherwise create a new PENDING entitlement row.

    This is unique-index safe and audit friendly.
    """
    existing_active = get_active_hotspot_subscription(customer.phone)
    if existing_active:
        # keep the package updated for UI/reporting (optional)
        if existing_active.package_id != package.id:
            existing_active.package_id = package.id
        return existing_active

    sub = Subscription(
        customer_id=customer.id,
        package_id=package.id,
        service_type="hotspot",
        status="pending",
        starts_at=None,
        expires_at=None,
        hotspot_username=customer.phone,  # ✅ identity column
        pppoe_username=None,
        router_username=None,            # ✅ legacy: never write
        last_tx_id=None,
        created_at=now_utc_naive(),
    )
    db.session.add(sub)
    db.session.flush()
    return sub


def extend_or_activate_hotspot_subscription(sub: Subscription, package: Package, tx: Transaction) -> None:
    """
    Hotspot rule:
      - If already ACTIVE: extend from max(expires_at, now)
      - Else: activate from now

    Always keeps ONE entitlement row ACTIVE per user.
    """
    now = now_utc_naive()
    minutes = int(getattr(package, "duration_minutes", 0) or 0)
    if minutes <= 0:
        minutes = 60  # safety fallback

    # Ensure identity columns are correct
    if (sub.service_type or "").lower() == "hotspot" and not sub.hotspot_username:
        # Prefer customer phone
        if getattr(sub, "customer", None) and sub.customer and sub.customer.phone:
            sub.hotspot_username = sub.customer.phone

    if sub.status == "active" and sub.expires_at:
        base = sub.expires_at if sub.expires_at > now else now
        sub.expires_at = base + timedelta(minutes=minutes)
        if not sub.starts_at:
            sub.starts_at = now
    else:
        sub.status = "active"
        sub.starts_at = now
        sub.expires_at = now + timedelta(minutes=minutes)

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
        "TransactionType": "CustomerPayBillOnline",  # Till -> CustomerBuyGoodsOnline
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
        data = r.json() if (r.headers.get("content-type", "") or "").startswith("application/json") else {"raw": r.text}
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
    """
    Public pay page is hotspot-focused.
    PPPoE provisioning is admin-only.
    """
    packages = Package.query.order_by(Package.price_kes.asc()).all()
    return render_template("pay.html", packages=packages)


@main.post("/pay")
def pay():
    """
    Initiate payment (STK push).
    Expects JSON:
      { "phone": "0712...", "package": "weekly_1" }

    Creates:
      - Customer (if needed)
      - Hotspot entitlement subscription (pending or reuse active)
      - Transaction (pending)
    Attempts STK push.
    """
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(str(data.get("phone", "")).strip())
    package_code = str(data.get("package", "")).strip()

    if not phone or not package_code:
        return jsonify({"ok": False, "error": "phone and package are required"}), 400

    package = get_package_by_code(package_code)

    # Public route is hotspot-only
    if (package.code or "").lower().startswith("pppoe_"):
        return jsonify({"ok": False, "error": "PPPoE packages are admin-provisioned. Choose a hotspot package."}), 400

    customer = get_or_create_customer(phone)

    # Entitlement: reuse active row if exists
    subscription = get_or_create_hotspot_entitlement(customer, package)

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
        created_at=now_utc_naive(),
    )
    db.session.add(tx)
    db.session.flush()

    # Link entitlement to tx (even while pending)
    subscription.last_tx_id = tx.id
    db.session.flush()

    ok, resp = stk_push(phone_2547=customer.phone, amount=tx.amount, package_code=package.code)

    if ok:
        tx.checkout_request_id = resp.get("CheckoutRequestID") or resp.get("checkoutRequestID") or tx.checkout_request_id
        tx.merchant_request_id = resp.get("MerchantRequestID") or resp.get("merchantRequestID") or tx.merchant_request_id
        tx.result_desc = resp.get("CustomerMessage") or resp.get("ResponseDescription") or "STK Push initiated"
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
        tx.result_desc = (resp.get("error") or "STK push failed")[:255]
        try:
            tx.raw_callback_json = json.dumps(resp, ensure_ascii=False)
        except Exception:
            tx.raw_callback_json = str(resp)
    else:
        tx.result_desc = str(resp)[:255]
        tx.raw_callback_json = str(resp)

    db.session.commit()
    return jsonify({"ok": False, "error": "STK push failed", "details": resp, "transaction_id": tx.id}), 502


@main.post("/mpesa/callback")
def mpesa_callback():
    """
    Receives M-Pesa STK callback.
    Updates Transaction and applies hotspot entitlement.

    Idempotency:
      - If tx already success/failed, we do not re-apply.
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

    # Store callback always
    tx.raw_callback_json = raw_text
    tx.result_code = str(result_code) if result_code is not None else None
    tx.result_desc = str(result_desc)[:255] if result_desc else None

    # Idempotency: already processed
    if tx.status in FINAL_TX_STATUSES:
        db.session.commit()
        return jsonify({"ok": True, "note": "Already processed"}), 200

    if str(result_code) == "0":
        tx.status = "success"
        tx.mpesa_receipt = _extract_stk_receipt_from_callback(payload)

        pkg = db.session.get(Package, tx.package_id)

        # Prefer entitlement row explicitly linked to tx
        sub = (
            Subscription.query.filter_by(last_tx_id=tx.id)
            .order_by(desc(Subscription.id))
            .first()
        )

        # Fallback: sometimes entitlement row link may be missing
        if not sub:
            try:
                customer = db.session.get(Customer, tx.customer_id)
                if customer and customer.phone:
                    sub = get_active_hotspot_subscription(customer.phone)
            except Exception:
                sub = None

        if sub and pkg:
            if (sub.service_type or "").lower() == "hotspot":
                extend_or_activate_hotspot_subscription(sub, pkg, tx)
            else:
                log.warning(
                    "Callback success for non-hotspot subscription | tx_id=%s sub_id=%s service_type=%s",
                    tx.id,
                    sub.id,
                    sub.service_type,
                )
        else:
            log.warning(
                "Callback success but subscription/package missing | tx_id=%s checkout_id=%s sub=%s pkg=%s",
                tx.id,
                checkout_id,
                bool(sub),
                bool(pkg),
            )

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
