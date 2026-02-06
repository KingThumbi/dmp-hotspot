# app/routes.py
from __future__ import annotations

import base64
import json
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
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

# For proration we treat a "month" as 30 days to match fixed-month billing.
PPPOE_BILLING_PERIOD = timedelta(days=30)

# Guard rail: ignore silly packages (e.g., KES 1)
MIN_CUSTOMER_PRICE_KES = 10

# Session key for "Home Internet customer portal" (no password flow)
HI_SESSION_KEY = "hi_customer_id"


# =========================================================
# Time helpers
# =========================================================
def now_utc_naive() -> datetime:
    """DB stores UTC-naive timestamps (datetime.utcnow())."""
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

    if p.startswith("0") and len(p) == 10 and p[1:].isdigit():
        return "254" + p[1:]

    if p.startswith("7") and len(p) == 9 and p.isdigit():
        return "254" + p

    if p.startswith("254") and len(p) >= 12 and p[3:].isdigit():
        return p

    return p


def is_valid_kenyan_mobile(phone_2547: str) -> bool:
    """Strictly require 2547XXXXXXXX format."""
    return bool(re.fullmatch(r"2547\d{8}", phone_2547 or ""))


def _parse_account_identifier(identifier: str) -> Optional[int]:
    """
    Parse account number like:
      D001, d001, D 001, D000123 -> returns Subscription.id (int) or None
    """
    if not identifier:
        return None
    compact = identifier.replace(" ", "").strip()
    m = re.fullmatch(r"[dD](\d{1,6})", compact)
    if not m:
        return None
    return int(m.group(1))


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


def is_pppoe_package(pkg: Package) -> bool:
    return (pkg.code or "").lower().startswith("pppoe_")


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
    """
    existing_active = get_active_hotspot_subscription(customer.phone)
    if existing_active:
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
        hotspot_username=customer.phone,
        pppoe_username=None,
        router_username=None,  # legacy: avoid
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
    """
    now = now_utc_naive()
    minutes = int(getattr(package, "duration_minutes", 0) or 0)
    if minutes <= 0:
        minutes = 60  # safety fallback

    # Ensure username exists (for old rows)
    if (sub.service_type or "").lower() == "hotspot" and not sub.hotspot_username:
        try:
            if sub.customer and sub.customer.phone:
                sub.hotspot_username = sub.customer.phone
        except Exception:
            pass

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


def pppoe_extend_or_activate(sub: Subscription, pkg: Package, tx: Transaction) -> None:
    """
    PPPoE renewal rule:
      - If expires_at in future: extend from expires_at (early renewal keeps remaining days)
      - Else: starts from now
    Duration:
      - Uses package.duration_minutes when present, else defaults to 30 days.
    """
    now = now_utc_naive()
    minutes = int(getattr(pkg, "duration_minutes", 0) or 0)
    if minutes <= 0:
        minutes = int(PPPOE_BILLING_PERIOD.total_seconds() // 60)

    if sub.expires_at and sub.expires_at > now:
        sub.expires_at = sub.expires_at + timedelta(minutes=minutes)
        sub.status = "active"
        if not sub.starts_at:
            sub.starts_at = now
    else:
        sub.status = "active"
        sub.starts_at = now
        sub.expires_at = now + timedelta(minutes=minutes)

    sub.last_tx_id = tx.id


def _extract_speed_mbps(pkg: Package) -> Optional[int]:
    src = f"{pkg.code or ''} {pkg.name or ''}".lower()
    m = re.search(r"(\d+)\s*mbps", src)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    m = re.search(r"pppoe[_\- ]?(\d+)", src)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def list_pppoe_customer_plans_dedup() -> list[dict]:
    """
    Customer-facing plan list:
      - PPPoE only
      - Dedup by speed (cheapest per speed)
      - Excludes test/internal codes
      - Excludes silly low prices
    """
    rows = (
        Package.query.filter(Package.code.ilike("pppoe%"))
        .filter(~Package.code.ilike("%test%"))
        .filter(Package.price_kes >= MIN_CUSTOMER_PRICE_KES)
        .order_by(Package.price_kes.asc())
        .all()
    )

    def tier_for_speed(speed: Optional[int]) -> str:
        if speed is None:
            return "Home Internet"
        if speed <= 5:
            return "Home Basic"
        if speed <= 10:
            return "Home Plus"
        if speed <= 20:
            return "Home Pro"
        return "Home Ultra"

    plans_by_speed: dict[int, dict] = {}
    for p in rows:
        spd = _extract_speed_mbps(p)
        if not spd:
            continue
        if spd not in plans_by_speed or int(p.price_kes) < int(plans_by_speed[spd]["price_kes"]):
            plans_by_speed[spd] = {
                "id": p.id,
                "code": p.code,
                "speed": spd,
                "tier": tier_for_speed(spd),
                "price_kes": int(p.price_kes),
            }

    plans = list(plans_by_speed.values())
    plans.sort(key=lambda x: x["speed"])
    return plans


# =========================================================
# Home Internet session gate (NO password)
# =========================================================
def home_internet_customer_required() -> int:
    """
    Customer gate for Home Internet portal WITHOUT password.
    This session is set after lookup on /home-internet/accounts.
    """
    cid = session.get(HI_SESSION_KEY)
    if not cid:
        # send them to accounts lookup
        return redirect(url_for("main.home_internet_accounts"))
    return int(cid)


@main.get("/home-internet/logout")
def home_internet_logout():
    session.pop(HI_SESSION_KEY, None)
    return redirect(url_for("main.home_internet_accounts"))


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

    account_ref = (current_app.config.get("MPESA_ACCOUNT_REF") or "DMPOLIN").strip()
    tx_desc = (current_app.config.get("MPESA_TX_DESC") or "Dmpolin Connect").strip()

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
        "TransactionType": "CustomerPayBillOnline",
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
    stk = payload.get("Body", {}).get("stkCallback", {}) or {}
    meta = stk.get("CallbackMetadata", {}) or {}
    items = meta.get("Item", []) or []
    for item in items:
        if item.get("Name") == "MpesaReceiptNumber":
            return item.get("Value")
    return None


# =========================================================
# Transaction creation helper (Hotspot + Home Internet)
# =========================================================
def initiate_stk_transaction(
    *,
    phone: str,
    customer: Customer,
    package: Package,
    amount: int,
    subscription: Optional[Subscription],
    allow_pppoe: bool,
    meta: Optional[dict] = None,
) -> Tuple[bool, Dict[str, Any], Optional[Transaction]]:
    """
    Create Transaction + send STK push.

    IMPORTANT:
    We persist init + meta inside tx.raw_callback_json so callback processing
    can apply correct business rules.
    """
    if is_pppoe_package(package) and not allow_pppoe:
        return False, {"error": "Home Internet payments require account access."}, None

    tx = Transaction(
        customer_id=customer.id,
        package_id=package.id,
        amount=int(amount),
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

    if subscription:
        subscription.last_tx_id = tx.id
        db.session.flush()

    ok, resp = stk_push(phone_2547=phone, amount=tx.amount, package_code=package.code)

    if ok:
        tx.checkout_request_id = resp.get("CheckoutRequestID") or resp.get("checkoutRequestID")
        tx.merchant_request_id = resp.get("MerchantRequestID") or resp.get("merchantRequestID")
        tx.result_desc = resp.get("CustomerMessage") or resp.get("ResponseDescription") or "STK Push initiated"

        payload = {"init": resp, "meta": meta or {}}
        try:
            tx.raw_callback_json = json.dumps(payload, ensure_ascii=False)
        except Exception:
            tx.raw_callback_json = str(payload)

        db.session.commit()
        return True, resp, tx

    tx.status = "failed"
    tx.result_desc = (resp.get("error") if isinstance(resp, dict) else str(resp))[:255]
    try:
        tx.raw_callback_json = json.dumps({"init_error": resp, "meta": meta or {}}, ensure_ascii=False)
    except Exception:
        tx.raw_callback_json = str(resp)

    db.session.commit()
    return False, resp, tx


def _tx_meta(tx: Transaction) -> dict:
    """Reads meta from tx.raw_callback_json stored by initiate_stk_transaction()."""
    try:
        raw = tx.raw_callback_json or ""
        obj = json.loads(raw) if raw and raw.strip().startswith("{") else {}
        meta = obj.get("meta") if isinstance(obj, dict) else None
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


# =========================================================
# PPPoE charge computation (final policy)
# =========================================================
def compute_pppoe_charge(
    *,
    current_sub: Subscription,
    current_pkg: Package,
    target_pkg: Package,
) -> Tuple[int, str]:
    """
    Returns: (amount_to_charge, mode)

    mode in:
      - "renewal"             -> expired/missing expiry, full price, period restarts now
      - "renew_extend"        -> same plan while active, full price, extend from current expiry
      - "upgrade_prorated"    -> mid-cycle upgrade, prorated difference, apply immediately, expiry unchanged
      - "downgrade_scheduled" -> mid-cycle downgrade, no charge, schedule pending_package_id
    """
    old_price = int(current_pkg.price_kes or 0)
    new_price = int(target_pkg.price_kes or 0)
    now = now_utc_naive()

    expired = (not current_sub.expires_at) or (current_sub.expires_at <= now)

    if expired:
        return new_price, "renewal"

    if new_price < old_price:
        return 0, "downgrade_scheduled"

    if new_price > old_price:
        diff = new_price - old_price
        period_seconds = int(PPPOE_BILLING_PERIOD.total_seconds())
        remaining_seconds = max(int((current_sub.expires_at - now).total_seconds()), 0)
        prorated = diff * (remaining_seconds / period_seconds) if period_seconds > 0 else float(diff)
        amount = int(math.ceil(prorated))
        return max(amount, 0), "upgrade_prorated"

    return new_price, "renew_extend"


# =========================================================
# Public routes
# =========================================================
@main.get("/")
def home():
    return redirect(url_for("main.pay_page"))


@main.get("/pay")
def pay_page():
    """Public pay page is hotspot-only (captive portal)."""
    packages = (
        Package.query.filter(~Package.code.ilike("pppoe%"))
        .filter(~Package.code.ilike("%test%"))
        .filter(Package.price_kes >= MIN_CUSTOMER_PRICE_KES)
        .order_by(Package.price_kes.asc())
        .all()
    )
    return render_template("pay.html", packages=packages)


@main.post("/pay")
def pay():
    """
    Hotspot-only STK initiation (captive portal).
    Expects JSON:
      { "phone": "0712...", "package": "weekly_1" }
    """
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(str(data.get("phone", "")).strip())
    package_code = str(data.get("package", "")).strip()

    if not phone or not package_code:
        return jsonify({"ok": False, "error": "phone and package are required"}), 400

    if not is_valid_kenyan_mobile(phone):
        return jsonify({"ok": False, "error": "Invalid phone. Use 0712345678 or 254712345678."}), 400

    package = get_package_by_code(package_code)

    if is_pppoe_package(package):
        return jsonify({"ok": False, "error": "Home Internet requires an account. Choose a Wi-Fi package."}), 400

    customer = get_or_create_customer(phone)
    subscription = get_or_create_hotspot_entitlement(customer, package)

    ok, resp, tx = initiate_stk_transaction(
        phone=customer.phone,
        customer=customer,
        package=package,
        amount=int(package.price_kes),
        subscription=subscription,
        allow_pppoe=False,
        meta={"flow": "hotspot", "package": package.code},
    )

    if ok and tx:
        return jsonify(
            {
                "ok": True,
                "transaction_id": tx.id,
                "checkout_request_id": tx.checkout_request_id,
                "merchant_request_id": tx.merchant_request_id,
                "message": tx.result_desc,
            }
        ), 200

    return jsonify(
        {"ok": False, "error": "STK push failed", "details": resp, "transaction_id": (tx.id if tx else None)}
    ), 502


# =========================================================
# Home Internet (customer-facing)
# =========================================================
@main.get("/home-internet")
def home_internet_page():
    plans = list_pppoe_customer_plans_dedup()
    return render_template("home_internet.html", plans=plans)


@main.post("/home-internet/request")
def home_internet_request():
    """
    Public Home Internet request form.
    Creates/gets Customer by phone, then creates an installation Ticket.

    NOTE:
    - Hotspot users do not get accounts from this flow.
    - This does NOT create a PPPoE subscription. Ops will provision after survey/installation.
    """
    from .models import AdminUser, Ticket  # local import to avoid circulars

    name = (request.form.get("name") or "").strip()
    phone_raw = (request.form.get("phone") or "").strip()
    area = (request.form.get("area") or "").strip()
    preferred_plan = (request.form.get("preferred_plan") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not name or not phone_raw or not area or not preferred_plan:
        flash("Please fill in your name, phone, area, and preferred speed.", "error")
        return redirect(url_for("main.home_internet_page"))

    phone = normalize_phone(phone_raw)
    if not is_valid_kenyan_mobile(phone):
        flash("Invalid phone number. Use 0712345678 or 254712345678.", "error")
        return redirect(url_for("main.home_internet_page"))

    pkg = get_package_by_code(preferred_plan)
    if not is_pppoe_package(pkg):
        flash("Please select a valid Home Internet plan.", "error")
        return redirect(url_for("main.home_internet_page"))

    customer = get_or_create_customer(phone)

    creator = (
        AdminUser.query.filter_by(is_active=True, is_superadmin=True).order_by(AdminUser.id.asc()).first()
        or AdminUser.query.filter_by(is_active=True).order_by(AdminUser.id.asc()).first()
    )
    if not creator:
        flash("System is missing an admin user. Please contact support.", "error")
        return redirect(url_for("main.home_internet_page"))

    year = datetime.utcnow().year

    t = Ticket(
        customer_id=customer.id,
        subscription_id=None,
        location_id=None,
        category="installation",
        priority="med",
        status="open",
        subject="Home Internet Installation Request",
        description=(
            f"Name: {name}\n"
            f"Phone: {phone}\n"
            f"Area/Estate: {area}\n"
            f"Preferred plan: {pkg.code} ({int(pkg.price_kes)} KES/month)\n"
            + (f"Notes: {notes}\n" if notes else "")
        ),
        created_by_admin_id=creator.id,
        assigned_to_admin_id=None,
        opened_at_utc=now_utc_naive(),
        created_at=now_utc_naive(),
        updated_at=now_utc_naive(),
        code="PENDING",
    )
    db.session.add(t)
    db.session.flush()  # gives t.id
    t.code = f"TCK-{year}-{t.id:06d}"
    db.session.commit()

    flash("Request received! We’ll contact you shortly to confirm location and schedule installation.", "success")
    return redirect(url_for("main.home_internet_page"))


@main.route("/home-internet/accounts", methods=["GET", "POST"])
def home_internet_accounts():
    """
    Existing customer lookup (NO password).
    Accepts:
      - Phone (0712.. or 2547..)
      - Account number (D001, D002...) -> maps to Subscription.id

    On success:
      - sets session[HI_SESSION_KEY] = customer.id (Home Internet portal access)
      - shows all PPPoE accounts for that customer
    """
    found_customer: Optional[Customer] = None
    subs: list[Subscription] = []
    error: Optional[str] = None

    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()

        if not identifier:
            error = "Enter your phone number or account number (e.g. D001)."
        else:
            sub_id = _parse_account_identifier(identifier)
            if sub_id is not None:
                sub = db.session.get(Subscription, sub_id)
                if not sub or (sub.service_type or "").lower() != "pppoe":
                    error = "Account not found."
                else:
                    found_customer = db.session.get(Customer, sub.customer_id)
            else:
                phone = normalize_phone(identifier)
                if not is_valid_kenyan_mobile(phone):
                    error = "Invalid phone. Use 0712345678 or 254712345678, or an account like D001."
                else:
                    found_customer = Customer.query.filter_by(phone=phone).first()
                    if not found_customer:
                        error = "No Home Internet account found for that phone number."

            if found_customer:
                subs = (
                    Subscription.query.filter_by(customer_id=found_customer.id, service_type="pppoe")
                    .order_by(Subscription.id.desc())
                    .all()
                )
                if not subs:
                    error = "No Home Internet accounts found for that phone number."
                    found_customer = None
                else:
                    session[HI_SESSION_KEY] = int(found_customer.id)

    return render_template("home_internet_accounts.html", customer=found_customer, subs=subs, error=error)


@main.route("/home-internet/pay/<int:account_id>", methods=["GET", "POST"])
def home_internet_pay(account_id: int):
    """
    Home Internet payment & plan-change page (NO password).
    Access is granted after lookup on /home-internet/accounts.

    Rules (final):
      - Same plan mid-cycle payment: full price, extend expiry from current expiry (do not reset)
      - Upgrade mid-cycle: pay prorated difference, apply immediately, expiry unchanged
      - Downgrade mid-cycle: no charge, schedule pending_package_id (applies at renewal)
      - Expired: full price renewal from now
      - Phone shown/auto-filled but customer may enter a different phone for this prompt only (not saved)
    """
    customer_id = home_internet_customer_required()

    sub = db.session.get(Subscription, account_id)
    if not sub or (sub.service_type or "").lower() != "pppoe":
        abort(404)

    if int(sub.customer_id) != int(customer_id):
        abort(403)

    customer = db.session.get(Customer, customer_id)
    if not customer:
        abort(403)

    current_pkg = db.session.get(Package, sub.package_id) if sub.package_id else None
    if not current_pkg:
        abort(400, description="Account has no plan assigned (or plan not found).")

    # Selectable plans (dedup by speed, cheapest per speed)
    plan_rows = (
        Package.query.filter(Package.code.ilike("pppoe%"))
        .filter(~Package.code.ilike("%test%"))
        .filter(Package.price_kes >= MIN_CUSTOMER_PRICE_KES)
        .order_by(Package.price_kes.asc())
        .all()
    )
    selectable: list[Package] = []
    seen_speeds: set[int] = set()
    for p in plan_rows:
        spd = _extract_speed_mbps(p)
        if not spd:
            continue
        if spd in seen_speeds:
            continue
        seen_speeds.add(spd)
        selectable.append(p)
    selectable.sort(key=lambda x: (_extract_speed_mbps(x) or 10**9))

    default_phone = customer.phone or ""

    def friendly_label(pkg: Package) -> str:
        spd = _extract_speed_mbps(pkg)
        if spd:
            return f"{spd} Mbps — KES {int(pkg.price_kes)} / month"
        return f"Home Internet — KES {int(pkg.price_kes)} / month"

    def build_vm() -> dict:
        return {
            "account_id": sub.id,
            "account_no": f"D{sub.id:03d}",
            "current_pkg_code": current_pkg.code,
            "current_pkg_name": current_pkg.name or "Home Internet",
            "current_speed": _extract_speed_mbps(current_pkg),
            "current_price": int(current_pkg.price_kes or 0),
            "status": sub.status or "",
            "starts_at": sub.starts_at,
            "expires_at": sub.expires_at,
            "pending_pkg": getattr(sub, "pending_package", None),
            "plans": [{"code": p.code, "label": friendly_label(p)} for p in selectable],
        }

    if request.method == "GET":
        amount_due, mode = compute_pppoe_charge(current_sub=sub, current_pkg=current_pkg, target_pkg=current_pkg)
        return render_template(
            "home_internet_pay.html",
            vm=build_vm(),
            phone=default_phone,
            selected_code=current_pkg.code,
            amount_due=int(amount_due),
            note=None,
            mode=mode,
        )

    # POST
    phone = normalize_phone((request.form.get("phone") or "").strip())
    selected_code = (request.form.get("pkg_code") or current_pkg.code or "").strip()

    if not is_valid_kenyan_mobile(phone):
        flash("Invalid phone number. Use 0712345678 or 254712345678.", "error")
        return render_template(
            "home_internet_pay.html",
            vm=build_vm(),
            phone=default_phone,
            selected_code=selected_code,
            amount_due=int(current_pkg.price_kes or 0),
            note="Please correct your phone number.",
            mode=None,
        )

    target_pkg = get_package_by_code(selected_code)
    if not is_pppoe_package(target_pkg):
        flash("Invalid plan selection.", "error")
        return render_template(
            "home_internet_pay.html",
            vm=build_vm(),
            phone=default_phone,
            selected_code=current_pkg.code,
            amount_due=int(current_pkg.price_kes or 0),
            note="Please select a valid Home Internet plan.",
            mode=None,
        )

    amount_due, mode = compute_pppoe_charge(current_sub=sub, current_pkg=current_pkg, target_pkg=target_pkg)

    # Downgrade mid-cycle: schedule for next renewal (no payment, no immediate change)
    if mode == "downgrade_scheduled":
        if not hasattr(sub, "pending_package_id"):
            abort(500, description="pending_package_id is required for scheduled downgrades (add field + migrate).")
        sub.pending_package_id = target_pkg.id
        db.session.commit()
        flash("Downgrade scheduled. It will apply at your next renewal.", "success")

        return render_template(
            "home_internet_pay.html",
            vm=build_vm(),
            phone=default_phone,
            selected_code=current_pkg.code,
            amount_due=0,
            note="Your downgrade has been scheduled. Your current speed remains active until renewal.",
            mode=mode,
        )

    meta = {
        "flow": "home_internet",
        "account_id": sub.id,
        "mode": mode,  # renewal | renew_extend | upgrade_prorated
        "old_package": current_pkg.code,
        "new_package": target_pkg.code,
    }

    ok, resp, tx = initiate_stk_transaction(
        phone=phone,
        customer=customer,
        package=target_pkg,
        amount=int(amount_due),
        subscription=sub,
        allow_pppoe=True,
        meta=meta,
    )

    if ok and tx:
        flash("Payment prompt sent. Check your phone to complete payment.", "success")
        return render_template(
            "home_internet_pay.html",
            vm=build_vm(),
            phone=default_phone,
            selected_code=target_pkg.code,
            amount_due=int(amount_due),
            note="Prompt sent. Complete payment on your phone.",
            mode=mode,
        )

    flash("Could not send payment prompt. Try again.", "error")
    return render_template(
        "home_internet_pay.html",
        vm=build_vm(),
        phone=default_phone,
        selected_code=target_pkg.code,
        amount_due=int(amount_due),
        note=str(resp),
        mode=mode,
    )


# =========================================================
# M-Pesa callback
# =========================================================
@main.post("/mpesa/callback")
def mpesa_callback():
    """
    Receives M-Pesa STK callback.
    Updates Transaction and applies entitlement changes.

    Idempotency:
      - If tx already success/failed, do not re-apply.
    """
    payload = request.get_json(force=True, silent=True) or {}
    stk = payload.get("Body", {}).get("stkCallback", {}) or {}
    checkout_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    result_desc = stk.get("ResultDesc")

    if not checkout_id:
        return jsonify({"ok": True, "note": "No CheckoutRequestID"}), 200

    tx = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
    if not tx:
        return jsonify({"ok": True, "note": "Transaction not found"}), 200

    # Merge callback into raw_callback_json without losing init/meta
    existing_meta = _tx_meta(tx)
    try:
        prior = json.loads(tx.raw_callback_json) if tx.raw_callback_json else {}
        if not isinstance(prior, dict):
            prior = {}
    except Exception:
        prior = {}
    prior["callback"] = payload
    prior["meta"] = existing_meta
    tx.raw_callback_json = json.dumps(prior, ensure_ascii=False)

    tx.result_code = str(result_code) if result_code is not None else None
    tx.result_desc = str(result_desc)[:255] if result_desc else None

    if tx.status in FINAL_TX_STATUSES:
        db.session.commit()
        return jsonify({"ok": True, "note": "Already processed"}), 200

    if str(result_code) != "0":
        tx.status = "failed"
        db.session.commit()
        return jsonify({"ok": True}), 200

    tx.status = "success"
    tx.mpesa_receipt = _extract_stk_receipt_from_callback(payload)

    pkg = db.session.get(Package, tx.package_id)
    meta = _tx_meta(tx)

    sub = Subscription.query.filter_by(last_tx_id=tx.id).order_by(desc(Subscription.id)).first()

    if not sub:
        try:
            customer = db.session.get(Customer, tx.customer_id)
            if customer and customer.phone:
                sub = get_active_hotspot_subscription(customer.phone)
        except Exception:
            sub = None

    if not sub or not pkg:
        log.warning("Callback success but subscription/package missing | tx_id=%s checkout_id=%s", tx.id, checkout_id)
        db.session.commit()
        return jsonify({"ok": True}), 200

    service = (sub.service_type or "").lower()

    if service == "hotspot":
        extend_or_activate_hotspot_subscription(sub, pkg, tx)
        db.session.commit()
        return jsonify({"ok": True}), 200

    if service == "pppoe":
        mode = (meta.get("mode") or "").strip()

        # Upgrade mid-period: change plan immediately; expiry unchanged.
        if mode == "upgrade_prorated":
            sub.package_id = pkg.id
            sub.status = "active"
            sub.last_tx_id = tx.id
            if not sub.starts_at:
                sub.starts_at = now_utc_naive()
            db.session.commit()
            return jsonify({"ok": True}), 200

        # Renewal / early renewal: apply pending downgrade at renewal moment if present.
        if getattr(sub, "pending_package_id", None):
            sub.package_id = int(sub.pending_package_id)
            sub.pending_package_id = None
            applied = db.session.get(Package, sub.package_id)
            if applied:
                pkg = applied
        else:
            sub.package_id = pkg.id

        pppoe_extend_or_activate(sub, pkg, tx)
        db.session.commit()
        return jsonify({"ok": True}), 200

    log.warning("Callback success for unsupported service_type=%s tx_id=%s sub_id=%s", service, tx.id, sub.id)
    db.session.commit()
    return jsonify({"ok": True}), 200


# =========================================================
# Health
# =========================================================
@main.get("/health")
def health():
    return jsonify({"ok": True, "time_utc": now_utc_naive().isoformat()}), 200
