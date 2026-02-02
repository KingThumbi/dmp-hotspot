# app/admin.py
from __future__ import annotations

import json
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from .extensions import db, limiter, login_manager
from .models import AdminAuditLog, AdminUser, Customer, Package, Subscription, Transaction
from .router_agent import agent_enable

admin = Blueprint("admin", __name__, template_folder="templates")
NAIROBI = ZoneInfo("Africa/Nairobi")


# =========================================================
# Time helpers
# =========================================================
def utcnow_naive() -> datetime:
    """DB stores naive UTC (datetime.utcnow). Keep consistent."""
    return datetime.utcnow()


def to_nairobi(dt_utc_naive: datetime | None) -> datetime | None:
    """Convert naive-UTC datetime from DB to aware Nairobi time for display."""
    if not dt_utc_naive:
        return None
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(NAIROBI)


# =========================================================
# Phone normalization (Kenya)
# =========================================================
def normalize_phone(phone: str) -> str:
    """
    Normalize Kenyan phone into 2547XXXXXXXX format (best-effort).
    Accepts:
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


# =========================================================
# Subscription identity helpers (NEW SCHEMA)
# =========================================================
def sub_identity(s: Subscription) -> str:
    """
    Returns the correct 'user identity' for display/search:
      - pppoe   -> pppoe_username
      - hotspot -> hotspot_username (phone)
    """
    svc = (s.service_type or "").strip().lower()
    if svc == "pppoe":
        return (s.pppoe_username or "").strip()
    return (s.hotspot_username or "").strip()


def sub_identity_for_router(s: Subscription) -> str:
    """
    Router identity uses split columns.
    NEVER depends on legacy router_username.
    """
    return sub_identity(s)


# =========================================================
# PPPoE username generation
# =========================================================
def _gen_pppoe_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _parse_pppoe_username(u: str) -> tuple[int, int] | None:
    """
    Parses:
      - D001..D999 -> (0, 1..999)
      - DA0001..   -> (1, 1..)
    Returns (series, n) where series 0=D, 1=DA.
    """
    if not u:
        return None
    u = u.strip().upper()

    if u.startswith("DA"):
        tail = u[2:]
        if tail.isdigit() and len(tail) >= 4:
            return (1, int(tail))

    if u.startswith("D"):
        tail = u[1:]
        if tail.isdigit() and len(tail) >= 3:
            return (0, int(tail))

    return None


def _format_pppoe_username(series: int, n: int) -> str:
    if series == 0:
        return f"D{n:03d}"
    return f"DA{n:04d}"


def _next_pppoe_username() -> str:
    """
    Find next available PPPoE username:
      D001..D999 then DA0001...
    Looks at both customers + subscriptions to avoid collisions.
    """
    existing: set[str] = set()

    # Customer.pppoe_username (if model has it)
    try:
        rows = db.session.query(Customer.pppoe_username).filter(Customer.pppoe_username.isnot(None)).all()
        existing.update((r[0] or "").strip().upper() for r in rows)
    except Exception:
        pass

    # Subscription.pppoe_username
    rows2 = db.session.query(Subscription.pppoe_username).filter(Subscription.pppoe_username.isnot(None)).all()
    existing.update((r[0] or "").strip().upper() for r in rows2)

    best_series = -1
    best_n = 0

    for u in existing:
        parsed = _parse_pppoe_username(u)
        if not parsed:
            continue
        s, n = parsed
        if s > best_series or (s == best_series and n > best_n):
            best_series, best_n = s, n

    if best_series == -1:
        return "D001"

    if best_series == 0 and best_n < 999:
        return _format_pppoe_username(0, best_n + 1)

    if best_series == 0 and best_n >= 999:
        return _format_pppoe_username(1, 1)

    return _format_pppoe_username(1, best_n + 1)


# =========================================================
# Flask-Login user loader
# =========================================================
@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(AdminUser, int(user_id))
    except Exception:
        return None


# =========================================================
# Audit logging
# =========================================================
def _client_ip() -> str | None:
    try:
        return request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr
    except Exception:
        return None


def audit(action: str, meta: dict | None = None, admin_user_id: int | None = None) -> None:
    """Best-effort admin audit logging. Never breaks user flow."""
    try:
        uid = admin_user_id or (getattr(current_user, "id", None) if current_user.is_authenticated else None)
        if not uid:
            return

        row = AdminAuditLog(
            admin_user_id=int(uid),
            action=action,
            ip_address=_client_ip(),
            user_agent=(request.headers.get("User-Agent") or "")[:255] or None,
            meta_json=json.dumps(meta, ensure_ascii=False) if meta else None,
            created_at=utcnow_naive(),
        )
        db.session.add(row)
        db.session.commit()
    except Exception:
        db.session.rollback()


# =========================================================
# Password policy + account password change
# =========================================================
def _validate_admin_password(pw: str) -> tuple[bool, str]:
    if len(pw) < 12:
        return False, "Passwords should be 12 characters or longer and include letters, numbers, and symbols."
    if not re.search(r"[a-z]", pw):
        return False, "Add at least one lowercase letter."
    if not re.search(r"[A-Z]", pw):
        return False, "Add at least one uppercase letter."
    if not re.search(r"\d", pw):
        return False, "Add at least one number."
    if not re.search(r"[^a-zA-Z0-9]", pw):
        return False, "Add at least one symbol (e.g. ! @ # $)."
    return True, "OK"


@admin.get("/account/password")
@login_required
def account_password_get():
    return render_template("admin/account_password.html")


@admin.post("/account/password")
@login_required
@limiter.limit("10 per minute")
def account_password_post():
    current_pw = request.form.get("current_password") or ""
    new_pw = request.form.get("new_password") or ""
    confirm = request.form.get("confirm_password") or ""

    if not current_pw or not new_pw or not confirm:
        flash("All fields are required.", "error")
        return redirect(url_for("admin.account_password_get"))

    if new_pw != confirm:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("admin.account_password_get"))

    if not current_user.check_password(current_pw):
        audit("password_change_failed", {"reason": "wrong_current_password"})
        flash("Current password is incorrect.", "error")
        return redirect(url_for("admin.account_password_get"))

    if current_user.check_password(new_pw):
        audit("password_change_failed", {"reason": "reused_password"})
        flash("New password must be different from the current password.", "error")
        return redirect(url_for("admin.account_password_get"))

    ok, msg = _validate_admin_password(new_pw)
    if not ok:
        audit("password_change_failed", {"reason": "weak_password"})
        flash(msg, "error")
        return redirect(url_for("admin.account_password_get"))

    current_user.set_password(new_pw)
    db.session.commit()

    audit("password_changed")

    logout_user()
    session.clear()

    flash("Password updated. Please log in again.", "success")
    return redirect(url_for("admin.login_get"))


# =========================================================
# Revenue helpers
# =========================================================
def nairobi_range_starts_utc_naive() -> dict[str, datetime]:
    now_local = datetime.now(NAIROBI)
    start_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week_local = start_today_local - timedelta(days=start_today_local.weekday())
    start_month_local = start_today_local.replace(day=1)

    def to_utc_naive(dt_local: datetime) -> datetime:
        return dt_local.astimezone(timezone.utc).replace(tzinfo=None)

    return {
        "today": to_utc_naive(start_today_local),
        "week": to_utc_naive(start_week_local),
        "month": to_utc_naive(start_month_local),
    }


def revenue_totals() -> dict[str, int]:
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
# Root
# =========================================================
@admin.get("/")
def admin_root():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login_get"))


# =========================================================
# Auth
# =========================================================
@admin.get("/login")
@limiter.limit("30 per minute")
def login_get():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


@admin.post("/login")
@limiter.limit("10 per minute")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = (request.form.get("next") or "").strip()

    if not email or not password:
        flash("Email and password are required.", "error")
        return redirect(url_for("admin.login_get"))

    user = AdminUser.query.filter_by(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        audit("login_failed", {"email": email})
        flash("Invalid credentials.", "error")
        return redirect(url_for("admin.login_get"))

    login_user(user)
    audit("login_success")
    flash("Welcome back.", "success")

    if next_url.startswith("/"):
        return redirect(next_url)

    return redirect(url_for("admin.dashboard"))


@admin.get("/logout")
@login_required
def logout():
    audit("logout")
    logout_user()
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("admin.login_get"))


# =========================================================
# Dashboard
# =========================================================
@admin.get("/dashboard")
@login_required
def dashboard():
    customers_count = Customer.query.count()
    active_subs = Subscription.query.filter_by(status="active").count()

    pending_tx = Transaction.query.filter_by(status="pending").count()
    success_tx = Transaction.query.filter_by(status="success").count()
    failed_tx = Transaction.query.filter_by(status="failed").count()

    recent = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        customers_count=customers_count,
        active_subs=active_subs,
        pending_tx=pending_tx,
        success_tx=success_tx,
        failed_tx=failed_tx,
        recent=recent,
    )


# =========================================================
# Customers
# =========================================================
@admin.get("/customers")
@login_required
def customers():
    q = (request.args.get("q") or "").strip()

    latest_sub = (
        db.session.query(
            Subscription.customer_id.label("customer_id"),
            sa.func.max(Subscription.id).label("sub_id"),
        )
        .group_by(Subscription.customer_id)
        .subquery()
    )

    cust_q = db.session.query(Customer)
    if q:
        cust_q = cust_q.filter(Customer.phone.ilike(f"%{q}%"))
    cust_q = cust_q.order_by(Customer.created_at.desc()).limit(300).subquery()

    rows = (
        db.session.query(Customer, Subscription, Transaction)
        .select_from(cust_q)
        .join(Customer, Customer.id == cust_q.c.id)
        .outerjoin(latest_sub, latest_sub.c.customer_id == Customer.id)
        .outerjoin(Subscription, Subscription.id == latest_sub.c.sub_id)
        .outerjoin(Transaction, Transaction.id == Subscription.last_tx_id)
        .order_by(Customer.created_at.desc())
        .all()
    )

    return render_template("admin/customers.html", rows=rows, q=q)


@admin.get("/customers/<int:customer_id>")
@login_required
def customer_detail(customer_id: int):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    subs = (
        Subscription.query.filter_by(customer_id=customer_id)
        .order_by(Subscription.created_at.desc())
        .all()
    )

    txs = (
        Transaction.query.filter_by(customer_id=customer_id)
        .order_by(Transaction.created_at.desc())
        .limit(200)
        .all()
    )

    return render_template("admin/customer_detail.html", customer=customer, subs=subs, txs=txs)


# =========================================================
# PPPoE admin creation
# =========================================================
@admin.get("/pppoe/new")
@login_required
def pppoe_new():
    pppoe_packages = (
        Package.query
        .filter(Package.code.like("pppoe_%"))
        .order_by(Package.price_kes.asc())
        .all()
    )
    return render_template(
        "admin/pppoe_new.html",
        packages=pppoe_packages,
        suggested_username=_next_pppoe_username(),
    )


@admin.post("/pppoe/create")
@login_required
@limiter.limit("20 per minute")
def pppoe_create():
    phone_raw = (request.form.get("phone") or "").strip()
    package_id_raw = (request.form.get("package_id") or "").strip()
    pppoe_username = (request.form.get("pppoe_username") or "").strip().upper()
    months_raw = (request.form.get("months") or "1").strip()

    enable_now = request.form.get("enable_now") == "on"
    set_customer_pppoe = request.form.get("set_customer_pppoe") == "on"

    phone = normalize_phone(phone_raw)
    if not phone or not phone.startswith("2547"):
        flash("Phone is required (use 0712… or 2547… format).", "error")
        return redirect(url_for("admin.pppoe_new"))

    try:
        package_id = int(package_id_raw)
    except Exception:
        flash("Select a valid PPPoE package.", "error")
        return redirect(url_for("admin.pppoe_new"))

    package = db.session.get(Package, package_id)
    if not package or not (package.code or "").startswith("pppoe_"):
        flash("Select a valid PPPoE package.", "error")
        return redirect(url_for("admin.pppoe_new"))

    try:
        months = int(months_raw)
        if months < 1 or months > 36:
            raise ValueError()
    except Exception:
        flash("Months must be between 1 and 36.", "error")
        return redirect(url_for("admin.pppoe_new"))

    # allocate username if blank
    if not pppoe_username:
        pppoe_username = _next_pppoe_username()

    if not _parse_pppoe_username(pppoe_username):
        flash("Invalid PPPoE username format. Use D001..D999 or DA0001..", "error")
        return redirect(url_for("admin.pppoe_new"))

    # customer
    customer = Customer.query.filter_by(phone=phone).first()
    if not customer:
        customer = Customer(phone=phone)
        db.session.add(customer)
        db.session.flush()

    # prevent duplicate active PPPoE username
    exists_active = (
        Subscription.query.filter(
            Subscription.service_type == "pppoe",
            Subscription.status == "active",
            Subscription.pppoe_username == pppoe_username,
        )
        .first()
    )
    if exists_active:
        flash(f"PPPoE username {pppoe_username} already has an ACTIVE subscription.", "error")
        return redirect(url_for("admin.pppoe_new"))

    # Optionally save credentials on customer
    if set_customer_pppoe:
        if hasattr(customer, "pppoe_username"):
            if getattr(customer, "pppoe_username", None) and customer.pppoe_username != pppoe_username:
                flash(
                    f"Customer already has PPPoE username {customer.pppoe_username}. Not overwritten.",
                    "warning",
                )
            else:
                customer.pppoe_username = pppoe_username

        if hasattr(customer, "pppoe_password"):
            if not getattr(customer, "pppoe_password", None):
                customer.pppoe_password = _gen_pppoe_password()

    now = utcnow_naive()

    # Duration logic:
    # - Package duration_minutes represents 30 days (43200) for PPPoE.
    # - Multiply by months.
    duration_minutes = int(package.duration_minutes or 0)
    if duration_minutes <= 0:
        # fallback: 30 days
        duration_minutes = 43200

    expires_at = now + timedelta(minutes=duration_minutes * months)

    # Create subscription (ACTIVE)
    sub = Subscription(
        customer_id=customer.id,
        package_id=package.id,
        service_type="pppoe",
        status="active",
        starts_at=now,
        expires_at=expires_at,
        pppoe_username=pppoe_username,
        hotspot_username=None,
        router_username=None,  # legacy; don't use going forward
    )
    db.session.add(sub)
    db.session.flush()

    # Create an admin audit transaction row (recommended)
    # This keeps your reporting consistent even though it's not M-Pesa.
    tx = Transaction(
        customer_id=customer.id,
        package_id=package.id,
        amount=int(package.price_kes or 0),
        status="success",  # treat as successful provisioning payment (admin action)
        checkout_request_id=None,
        merchant_request_id=None,
        mpesa_receipt=None,
        result_code="ADMIN",
        result_desc=f"Admin PPPoE activation ({months} month(s))",
        raw_callback_json=None,
    )
    db.session.add(tx)
    db.session.flush()

    sub.last_tx_id = tx.id
    db.session.add(sub)

    router_enabled = bool(current_app.config.get("ROUTER_AGENT_ENABLED", False))

    # Commit subscription + tx first (DB is source of truth)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("DB conflict. That PPPoE username may already exist. Try a different username.", "error")
        return redirect(url_for("admin.pppoe_new"))
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create PPPoE subscription: {e}", "error")
        return redirect(url_for("admin.pppoe_new"))

    # Optional router provisioning (do NOT rollback DB changes)
    if enable_now:
        if not router_enabled:
            flash("Router automation is OFF (ROUTER_AGENT_ENABLED=false). Subscription created in DB only.", "warning")
        else:
            try:
                agent_enable(
                    current_app,
                    pppoe_username,
                    package.mikrotik_profile,
                    0,
                    comment=f"PPPoE provisioned by admin (sub_id={sub.id})",
                )
                flash("PPPoE provisioned/enabled on router.", "success")
            except Exception as e:
                flash(f"Router provisioning failed: {e}", "error")
                audit(
                    "pppoe_router_provision_failed",
                    {"sub_id": sub.id, "pppoe_username": pppoe_username, "error": str(e)},
                )

    audit(
        "pppoe_subscription_created",
        {
            "sub_id": sub.id,
            "customer_id": customer.id,
            "phone": phone,
            "pppoe_username": pppoe_username,
            "package_code": getattr(package, "code", None),
            "months": months,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "router_enabled": router_enabled,
            "router_provision_attempted": enable_now,
        },
    )

    flash(f"PPPoE subscription created: {pppoe_username} (expires {expires_at})", "success")
    return redirect(url_for("admin.subscriptions", svc="pppoe", status="active", q=pppoe_username))


# =========================================================
# Subscriptions
# =========================================================
@admin.get("/subscriptions")
@login_required
def subscriptions():
    status = (request.args.get("status") or "").strip().lower()
    svc = (request.args.get("svc") or "").strip().lower()
    q = (request.args.get("q") or "").strip()
    pkg = (request.args.get("pkg") or "").strip()

    query = Subscription.query

    if status in {"pending", "active", "expired"}:
        query = query.filter(Subscription.status == status)

    if svc in {"hotspot", "pppoe"}:
        query = query.filter(Subscription.service_type == svc)

    if q:
        query = query.filter(
            or_(
                Subscription.hotspot_username.ilike(f"%{q}%"),
                Subscription.pppoe_username.ilike(f"%{q}%"),
                Subscription.router_username.ilike(f"%{q}%"),  # legacy fallback
            )
        )

    if pkg:
        query = query.join(Subscription.package).filter(Package.code == pkg)

    rows = query.order_by(Subscription.created_at.desc()).limit(300).all()

    now = utcnow_naive()

    def fmt_remaining(expires_at: datetime | None) -> str:
        if not expires_at:
            return "-"
        seconds = int((expires_at - now).total_seconds())
        if seconds <= 0:
            return "Expired"

        mins_total = seconds // 60
        hrs = mins_total // 60
        mins = mins_total % 60

        if hrs >= 24:
            days = hrs // 24
            hrs = hrs % 24
            return f"{days}d {hrs}h {mins}m"

        return f"{hrs}h {mins}m"

    items = []
    for s in rows:
        remaining = fmt_remaining(s.expires_at)
        is_expired = (s.expires_at is not None and s.expires_at <= now) or s.status == "expired"
        items.append(
            {"s": s, "remaining": remaining, "is_expired": is_expired, "identity": sub_identity(s)}
        )

    pkg_codes = [p.code for p in Package.query.order_by(Package.price_kes.asc()).all()]

    return render_template(
        "admin/subscriptions.html",
        items=items,
        status=status,
        svc=svc,
        q=q,
        pkg=pkg,
        pkg_codes=pkg_codes,
    )


@admin.post("/subscriptions/<int:sub_id>/enable")
@login_required
@limiter.limit("20 per minute")
def subscription_enable(sub_id: int):
    sub = db.session.get(Subscription, sub_id)
    if not sub:
        flash("Subscription not found.", "error")
        return redirect(url_for("admin.subscriptions"))

    now = utcnow_naive()

    if sub.status != "active":
        flash("Only ACTIVE subscriptions can be enabled on the router.", "error")
        return redirect(url_for("admin.subscriptions"))

    if not sub.expires_at or sub.expires_at <= now:
        flash("This subscription is expired; cannot enable.", "error")
        return redirect(url_for("admin.subscriptions"))

    if not sub.package:
        flash("Package not found for this subscription.", "error")
        return redirect(url_for("admin.subscriptions"))

    if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
        flash("Router control is OFF (ROUTER_AGENT_ENABLED=false).", "error")
        return redirect(url_for("admin.subscriptions"))

    username = sub_identity_for_router(sub)
    if not username:
        flash("Missing username (pppoe_username/hotspot_username).", "error")
        audit("router_enable_failed", {"sub_id": sub.id, "service_type": sub.service_type, "reason": "missing_username"})
        return redirect(url_for("admin.subscriptions"))

    try:
        remaining_minutes = int((sub.expires_at - now).total_seconds() // 60)
        remaining_minutes = max(1, remaining_minutes)

        svc = (sub.service_type or "hotspot").lower().strip()

        if svc == "pppoe":
            agent_enable(
                current_app,
                username,
                sub.package.mikrotik_profile,
                0,
                comment="Enabled by admin",
            )
        else:
            agent_enable(
                current_app,
                username,
                sub.package.mikrotik_profile,
                remaining_minutes,
                comment="Enabled by admin",
            )

        flash("Router enable command sent.", "success")
        audit(
            "router_enable_sent",
            {
                "sub_id": sub.id,
                "service_type": sub.service_type,
                "username": username,
                "profile": sub.package.mikrotik_profile,
                "remaining_minutes": remaining_minutes,
            },
        )
    except Exception as e:
        audit(
            "router_enable_failed",
            {
                "sub_id": sub.id,
                "service_type": sub.service_type,
                "username": username,
                "profile": getattr(sub.package, "mikrotik_profile", None),
                "error": str(e),
            },
        )
        flash(f"Router enable failed: {e}", "error")

    return redirect(url_for("admin.subscriptions"))


# =========================================================
# Transactions
# =========================================================
@admin.get("/transactions")
@login_required
def transactions():
    status = (request.args.get("status") or "").strip().lower()
    query = Transaction.query

    if status in {"pending", "success", "failed"}:
        query = query.filter(Transaction.status == status)

    totals = revenue_totals()
    rows = query.order_by(Transaction.created_at.desc()).limit(500).all()
    items = [{"t": t, "created_local": to_nairobi(t.created_at)} for t in rows]

    return render_template("admin/transactions.html", items=items, status=status, totals=totals)


@admin.get("/transactions/<int:tx_id>/callback")
@login_required
def transaction_callback_json(tx_id: int):
    tx = db.session.get(Transaction, tx_id)
    if not tx:
        abort(404)

    pretty = None
    if tx.raw_callback_json:
        try:
            pretty = json.dumps(json.loads(tx.raw_callback_json), indent=2, ensure_ascii=False)
        except Exception:
            pretty = tx.raw_callback_json

    return render_template("admin/transaction_callback.html", tx=tx, pretty_json=pretty)
