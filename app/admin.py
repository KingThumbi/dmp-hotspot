# app/admin.py
from __future__ import annotations

import csv
import io
import json
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from flask import (
    Blueprint,
    Response,
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

from .authz import roles_required
from .extensions import db, limiter, login_manager
from .models import (
    AdminAuditLog,
    AdminUser,
    Asset,
    Customer,
    Expense,
    ExpenseCategory,
    ExpenseTemplate,
    Package,
    Subscription,
    Transaction,
)
from .router_agent import agent_enable
from .services.finance_reports import (
    expense_breakdown_by_category_range,
    last_n_months_summary,
    profit_snapshot_range,
)

admin = Blueprint("admin", __name__, template_folder="templates")

NAIROBI = ZoneInfo("Africa/Nairobi")


# =========================================================
# Time helpers (DB stores naive UTC; UI displays EAT)
# =========================================================
def utcnow_naive() -> datetime:
    return datetime.utcnow()


def to_nairobi(dt_utc_naive: datetime | None) -> datetime | None:
    if not dt_utc_naive:
        return None
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(NAIROBI)


def _month_range_utc_naive(now_utc_naive: datetime) -> tuple[datetime, datetime]:
    start = datetime(now_utc_naive.year, now_utc_naive.month, 1)
    if now_utc_naive.month == 12:
        end = datetime(now_utc_naive.year + 1, 1, 1)
    else:
        end = datetime(now_utc_naive.year, now_utc_naive.month + 1, 1)
    return start, end


def _parse_date_range_args() -> tuple[datetime, datetime, str, str]:
    """
    Reads ?start=YYYY-MM-DD&end=YYYY-MM-DD from query string.
    Returns (start_utc_naive, end_utc_naive_exclusive, start_str, end_str)

    - DB uses naive UTC.
    - end is made EXCLUSIVE by adding 1 day at 00:00.
    - Default: current month [start, end).
    """
    now = utcnow_naive()
    default_start, default_end = _month_range_utc_naive(now)

    start_str = (request.args.get("start") or "").strip()
    end_str = (request.args.get("end") or "").strip()

    start = default_start
    end_excl = default_end

    if start_str:
        try:
            start = datetime.fromisoformat(start_str)  # YYYY-MM-DD
        except ValueError:
            start = default_start

    if end_str:
        try:
            end_inclusive = datetime.fromisoformat(end_str)
            end_excl = end_inclusive + timedelta(days=1)
        except ValueError:
            end_excl = default_end

    if end_excl <= start:
        start = default_start
        end_excl = default_end
        start_str = ""
        end_str = ""

    if not start_str:
        start_str = start.strftime("%Y-%m-%d")
    if not end_str:
        end_str = (end_excl - timedelta(days=1)).strftime("%Y-%m-%d")

    return start, end_excl, start_str, end_str


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
# Subscription identity helpers
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
    return f"D{n:03d}" if series == 0 else f"DA{n:04d}"


def _next_pppoe_username() -> str:
    """
    Find next available PPPoE username:
      D001..D999 then DA0001...
    Looks at both customers + subscriptions to avoid collisions.
    """
    existing: set[str] = set()

    # Customer.pppoe_username (if model has it)
    try:
        rows = (
            db.session.query(Customer.pppoe_username)
            .filter(Customer.pppoe_username.isnot(None))
            .all()
        )
        existing.update((r[0] or "").strip().upper() for r in rows)
    except Exception:
        pass

    # Subscription.pppoe_username
    rows2 = (
        db.session.query(Subscription.pppoe_username)
        .filter(Subscription.pppoe_username.isnot(None))
        .all()
    )
    existing.update((r[0] or "").strip().upper() for r in rows2)

    best_series = -1
    best_n = 0
    for u in existing:
        parsed = _parse_pppoe_username(u)
        if not parsed:
            continue
        series, n = parsed
        if series > best_series or (series == best_series and n > best_n):
            best_series, best_n = series, n

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
    audit("login_success", {"email": email, "role": getattr(user, "role", None), "super": getattr(user, "is_superadmin", None)})
    flash("Welcome back.", "success")

    # Only allow relative paths
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

    # Finance snapshot: current UTC month using range helper (avoid missing imports)
    now_utc_naive = utcnow_naive()
    start_utc, end_utc = _month_range_utc_naive(now_utc_naive)
    finance = profit_snapshot_range(start_utc, end_utc) or {"income_kes": 0, "expenses_kes": 0, "profit_kes": 0}

    return render_template(
        "admin/dashboard.html",
        customers_count=customers_count,
        active_subs=active_subs,
        pending_tx=pending_tx,
        success_tx=success_tx,
        failed_tx=failed_tx,
        recent=recent,
        finance=finance,
    )


# =========================================================
# Finance Dashboard (Phase D working)
# =========================================================
@admin.route("/dashboard/finance", methods=["GET"])
@roles_required("finance", "admin")
def dashboard_finance():
    """
    Finance dashboard supports:
      - preset ranges via ?preset=today|week|month|last_month|last_30
      - custom ranges via ?start=YYYY-MM-DD&end=YYYY-MM-DD
    DB stores naive UTC; UI displays EAT (Africa/Nairobi).
    """
    preset = (request.args.get("preset") or "").strip().lower()

    if preset in {"today", "week", "month", "last_month", "last_30"}:
        now_local = datetime.now(NAIROBI)
        start_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        if preset == "today":
            start_local = start_today_local
            end_local_excl = start_local + timedelta(days=1)

        elif preset == "week":
            start_local = start_today_local - timedelta(days=start_today_local.weekday())
            end_local_excl = start_local + timedelta(days=7)

        elif preset == "month":
            start_local = start_today_local.replace(day=1)
            if start_local.month == 12:
                end_local_excl = start_local.replace(year=start_local.year + 1, month=1, day=1)
            else:
                end_local_excl = start_local.replace(month=start_local.month + 1, day=1)

        elif preset == "last_month":
            first_this_month = start_today_local.replace(day=1)
            if first_this_month.month == 1:
                start_local = first_this_month.replace(year=first_this_month.year - 1, month=12, day=1)
            else:
                start_local = first_this_month.replace(month=first_this_month.month - 1, day=1)
            end_local_excl = first_this_month

        else:  # last_30
            start_local = start_today_local - timedelta(days=29)
            end_local_excl = start_today_local + timedelta(days=1)

        start = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end = end_local_excl.astimezone(timezone.utc).replace(tzinfo=None)

        start_str = start_local.strftime("%Y-%m-%d")
        end_str = (end_local_excl - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start, end, start_str, end_str = _parse_date_range_args()

    this_period = profit_snapshot_range(start, end)
    breakdown = expense_breakdown_by_category_range(start, end)
    summary = last_n_months_summary(6)

    this_period["start_eat"] = to_nairobi(this_period["start_utc"])
    this_period["end_eat_inclusive"] = to_nairobi(this_period["end_utc"] - timedelta(seconds=1))

    return render_template(
        "admin/dashboard_finance.html",
        this_month=this_period,  # keep template variable name unchanged
        last_month=None,
        breakdown=breakdown,
        summary=summary,
        now_eat=to_nairobi(utcnow_naive()),
        start_str=start_str,
        end_str=end_str,
    )


@admin.get("/dashboard/finance.csv")
@roles_required("finance", "admin")
def dashboard_finance_csv():
    start, end, start_str, end_str = _parse_date_range_args()

    snap = profit_snapshot_range(start, end)
    breakdown = expense_breakdown_by_category_range(start, end)

    output = io.StringIO()
    w = csv.writer(output)

    w.writerow(["Dmpolin Connect - Finance Export"])
    w.writerow(["Start (UTC)", start_str])
    w.writerow(["End (UTC)", end_str])
    w.writerow([])

    w.writerow(["Snapshot"])
    w.writerow(["Income (KES)", snap.get("income_kes", 0)])
    w.writerow(["Expenses (KES)", snap.get("expenses_kes", 0)])
    w.writerow(["Profit (KES)", snap.get("profit_kes", 0)])
    w.writerow([])

    w.writerow(["Expense Breakdown (KES)"])
    w.writerow(["Category", "Total (KES)"])
    for row in (breakdown or []):
        w.writerow([row.get("category_name"), row.get("total_kes", 0)])

    filename = f"finance_{start_str}_to_{end_str}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =========================================================
# Customers (Support/Admin)
# =========================================================
@admin.get("/customers")
@roles_required("support", "admin")
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
@roles_required("support", "admin")
def customer_detail(customer_id: int):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    subs = Subscription.query.filter_by(customer_id=customer_id).order_by(Subscription.created_at.desc()).all()
    txs = Transaction.query.filter_by(customer_id=customer_id).order_by(Transaction.created_at.desc()).limit(200).all()

    return render_template("admin/customer_detail.html", customer=customer, subs=subs, txs=txs)


# =========================================================
# PPPoE admin creation (Ops/Admin)
# =========================================================
@admin.get("/pppoe/new")
@roles_required("ops", "admin")
def pppoe_new():
    pppoe_packages = (
        Package.query.filter(Package.code.like("pppoe_%"))
        .order_by(Package.price_kes.asc())
        .all()
    )
    return render_template(
        "admin/pppoe_new.html",
        packages=pppoe_packages,
        suggested_username=_next_pppoe_username(),
    )


@admin.post("/pppoe/create")
@roles_required("ops", "admin")
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

    if not pppoe_username:
        pppoe_username = _next_pppoe_username()

    if not _parse_pppoe_username(pppoe_username):
        flash("Invalid PPPoE username format. Use D001..D999 or DA0001..", "error")
        return redirect(url_for("admin.pppoe_new"))

    customer = Customer.query.filter_by(phone=phone).first()
    if not customer:
        customer = Customer(phone=phone)
        db.session.add(customer)
        db.session.flush()

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

    if set_customer_pppoe:
        if hasattr(customer, "pppoe_username"):
            if getattr(customer, "pppoe_username", None) and customer.pppoe_username != pppoe_username:
                flash(f"Customer already has PPPoE username {customer.pppoe_username}. Not overwritten.", "warning")
            else:
                customer.pppoe_username = pppoe_username

        if hasattr(customer, "pppoe_password") and not getattr(customer, "pppoe_password", None):
            customer.pppoe_password = _gen_pppoe_password()

    now = utcnow_naive()

    duration_minutes = int(package.duration_minutes or 0)
    if duration_minutes <= 0:
        duration_minutes = 43200  # 30 days fallback
    expires_at = now + timedelta(minutes=duration_minutes * months)

    sub = Subscription(
        customer_id=customer.id,
        package_id=package.id,
        service_type="pppoe",
        status="active",
        starts_at=now,
        expires_at=expires_at,
        pppoe_username=pppoe_username,
        hotspot_username=None,
        router_username=None,  # legacy; do not use
    )
    db.session.add(sub)
    db.session.flush()

    tx = Transaction(
        customer_id=customer.id,
        package_id=package.id,
        amount=int(package.price_kes or 0),
        status="success",
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

    router_enabled = bool(current_app.config.get("ROUTER_AGENT_ENABLED", False))

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
                audit("pppoe_router_provision_failed", {"sub_id": sub.id, "pppoe_username": pppoe_username, "error": str(e)})

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
# Subscriptions (Ops/Support/Admin)
# =========================================================
@admin.get("/subscriptions")
@roles_required("ops", "support", "admin")
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
        items.append({"s": s, "remaining": remaining, "is_expired": is_expired, "identity": sub_identity(s)})

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
@roles_required("ops", "admin")
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
            agent_enable(current_app, username, sub.package.mikrotik_profile, 0, comment="Enabled by admin")
        else:
            agent_enable(current_app, username, sub.package.mikrotik_profile, remaining_minutes, comment="Enabled by admin")

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
# Transactions (Finance/Admin)
# =========================================================
@admin.get("/transactions")
@roles_required("finance", "admin")
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
@roles_required("finance", "admin")
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


# =========================================================
# Assets (Ops/Admin) — minimal list endpoint for nav safety
# =========================================================
@admin.get("/assets")
@roles_required("ops", "admin")
def assets():
    rows = Asset.query.order_by(Asset.created_at.desc()).limit(300).all()
    return render_template("admin/assets.html", assets=rows)


# =========================================================
# Phase D.3.2 — Expense Categories (Finance/Admin)
# =========================================================
@admin.get("/expense-categories")
@roles_required("finance", "admin")
def expense_categories_list():
    categories = (
        ExpenseCategory.query
        .order_by(ExpenseCategory.parent_id.asc().nullsfirst(), ExpenseCategory.name.asc())
        .all()
    )
    return render_template("admin/expense_categories.html", categories=categories)


@admin.post("/expense-categories")
@roles_required("finance", "admin")
def expense_categories_create():
    name = (request.form.get("name") or "").strip()
    parent_id_raw = (request.form.get("parent_id") or "").strip()

    if not name:
        flash("Category name is required.", "error")
        return redirect(url_for("admin.expense_categories_list"))

    parent_id = int(parent_id_raw) if parent_id_raw else None

    existing = ExpenseCategory.query.filter_by(parent_id=parent_id, name=name).first()
    if existing:
        flash("That category already exists under the selected parent.", "warning")
        return redirect(url_for("admin.expense_categories_list"))

    c = ExpenseCategory(name=name, parent_id=parent_id, is_active=True)
    db.session.add(c)
    db.session.commit()

    flash("Category created.", "success")
    return redirect(url_for("admin.expense_categories_list"))


# =========================================================
# Phase D.3.2 — Expense Templates (Finance/Admin)
# =========================================================
@admin.get("/expense-templates")
@roles_required("finance", "admin")
def expense_templates_list():
    categories = (
        ExpenseCategory.query
        .filter(ExpenseCategory.is_active.is_(True))
        .order_by(ExpenseCategory.parent_id.asc().nullsfirst(), ExpenseCategory.name.asc())
        .all()
    )

    templates = (
        ExpenseTemplate.query
        .join(ExpenseCategory, ExpenseTemplate.category_id == ExpenseCategory.id)
        .order_by(ExpenseTemplate.is_active.desc(), ExpenseCategory.name.asc(), ExpenseTemplate.name.asc())
        .all()
    )

    return render_template(
        "admin/expense_templates.html",
        templates=templates,
        categories=categories,
    )


@admin.post("/expense-templates")
@roles_required("finance", "admin")
def expense_templates_create():
    name = (request.form.get("name") or "").strip()
    category_id_raw = (request.form.get("category_id") or "").strip()
    default_amount_raw = (request.form.get("default_amount") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not name:
        flash("Template name is required.", "error")
        return redirect(url_for("admin.expense_templates_list"))

    if not category_id_raw:
        flash("Please select a category.", "error")
        return redirect(url_for("admin.expense_templates_list"))

    category_id = int(category_id_raw)

    default_amount = None
    if default_amount_raw:
        try:
            default_amount = int(default_amount_raw)
        except ValueError:
            flash("Default amount must be a number.", "error")
            return redirect(url_for("admin.expense_templates_list"))

    existing = ExpenseTemplate.query.filter_by(category_id=category_id, name=name).first()
    if existing:
        flash("That template already exists under this category.", "warning")
        return redirect(url_for("admin.expense_templates_list"))

    t = ExpenseTemplate(
        category_id=category_id,
        name=name,
        default_amount=default_amount,
        notes=notes or None,
        is_active=True,
    )
    db.session.add(t)
    db.session.commit()

    flash("Template created.", "success")
    return redirect(url_for("admin.expense_templates_list"))


# =========================================================
# Phase D.3.2 — Record Expense (Finance/Admin)
# =========================================================
@admin.get("/expenses/new")
@roles_required("finance", "admin")
def expense_new():
    categories = (
        ExpenseCategory.query
        .filter(ExpenseCategory.is_active.is_(True))
        .order_by(ExpenseCategory.parent_id.asc().nullsfirst(), ExpenseCategory.name.asc())
        .all()
    )

    templates = (
        ExpenseTemplate.query
        .filter(ExpenseTemplate.is_active.is_(True))
        .order_by(ExpenseTemplate.name.asc())
        .all()
    )

    assets_rows = Asset.query.order_by(Asset.id.desc()).limit(200).all()

    return render_template(
        "admin/expense_new.html",
        categories=categories,
        templates=templates,
        assets=assets_rows,
    )


@admin.post("/expenses/new")
@roles_required("finance", "admin")
def expense_create():
    template_id_raw = (request.form.get("template_id") or "").strip()
    category_id_raw = (request.form.get("category_id") or "").strip()
    amount_raw = (request.form.get("amount") or "").strip()
    description = (request.form.get("description") or "").strip()
    asset_id_raw = (request.form.get("asset_id") or "").strip()
    incurred_at_raw = (request.form.get("incurred_at") or "").strip()

    if not amount_raw:
        flash("Amount is required.", "error")
        return redirect(url_for("admin.expense_new"))

    try:
        amount = int(amount_raw)
    except ValueError:
        flash("Amount must be a number.", "error")
        return redirect(url_for("admin.expense_new"))

    # HTML datetime-local => "YYYY-MM-DDTHH:MM"
    if incurred_at_raw:
        try:
            incurred_at = datetime.fromisoformat(incurred_at_raw)
        except ValueError:
            flash("Invalid incurred date/time.", "error")
            return redirect(url_for("admin.expense_new"))
    else:
        incurred_at = utcnow_naive()

    template_id = int(template_id_raw) if template_id_raw else None
    category_id = int(category_id_raw) if category_id_raw else None
    asset_id = int(asset_id_raw) if asset_id_raw else None

    legacy_category = "other"
    if category_id:
        c = db.session.get(ExpenseCategory, category_id)
        if c:
            legacy_category = c.name

    e = Expense(
        category=legacy_category,  # legacy not-null column
        category_id=category_id,
        template_id=template_id,
        amount=amount,
        description=description or None,
        asset_id=asset_id,
        incurred_at=incurred_at,
        recorded_by_admin=getattr(current_user, "id", None),
    )
    db.session.add(e)
    db.session.commit()

    audit("expense_recorded", {"expense_id": e.id, "amount": amount, "category_id": category_id, "template_id": template_id})
    flash("Expense recorded.", "success")
    return redirect(url_for("admin.expense_new"))

# =========================================================
# Phase E: System Users (Admin-only)
# =========================================================

@admin.route("/admin/users", methods=["GET"])
@login_required
@roles_required("admin")
def users_list():
    users = (
        AdminUser.query
        .order_by(AdminUser.is_superadmin.desc(), AdminUser.role.asc(), AdminUser.email.asc())
        .all()
    )
    return render_template("admin/users_list.html", users=users)


@admin.route("/admin/users/new", methods=["GET"])
@login_required
@roles_required("admin")
def users_new_get():
    return render_template("admin/users_new.html")


@admin.route("/admin/users/new", methods=["POST"])
@login_required
@roles_required("admin")
def users_new_post():
    email = (request.form.get("email") or "").strip().lower()
    name = (request.form.get("name") or "").strip() or None
    role = (request.form.get("role") or "admin").strip().lower()
    password = (request.form.get("password") or "").strip()

    allowed_roles = {"admin", "finance", "ops", "support"}

    if not email or "@" not in email:
        flash("Valid email is required.", "warning")
        return redirect(url_for("admin.users_new_get"))

    if role not in allowed_roles:
        flash("Invalid role selected.", "warning")
        return redirect(url_for("admin.users_new_get"))

    if len(password) < 10:
        flash("Password must be at least 10 characters.", "warning")
        return redirect(url_for("admin.users_new_get"))

    if AdminUser.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "warning")
        return redirect(url_for("admin.users_new_get"))

    u = AdminUser(email=email, name=name, role=role, is_active=True, is_superadmin=False)
    u.set_password(password)

    try:
        db.session.add(u)
        db.session.commit()
        flash("User created successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to create user. Please try again.", "error")

    return redirect(url_for("admin.users_list"))


@admin.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@roles_required("admin")
def users_toggle(user_id: int):
    if user_id == getattr(current_user, "id", None):
        flash("You cannot disable your own account.", "warning")
        return redirect(url_for("admin.users_list"))

    u = AdminUser.query.get_or_404(user_id)

    if u.is_superadmin:
        flash("Superadmin account cannot be disabled from this screen.", "warning")
        return redirect(url_for("admin.users_list"))

    u.is_active = not bool(u.is_active)

    try:
        db.session.commit()
        flash(f"User {'enabled' if u.is_active else 'disabled'} successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to update user.", "error")

    return redirect(url_for("admin.users_list"))

