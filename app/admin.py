# app/admin.py
from __future__ import annotations

import csv
import io
import json
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from sqlalchemy import and_

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
    CustomerLocation,
    Ticket,
    TicketUpdate,
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
from app.models import CustomerLocation

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

def parse_datetime_local_eat_to_utc_naive(value: str) -> datetime:
    """
    Takes HTML datetime-local ('YYYY-MM-DDTHH:MM') assumed in Africa/Nairobi (EAT),
    returns UTC-naive datetime for DB (your DB stores naive UTC).
    """
    if not value:
        raise ValueError("paid_at is required")

    # datetime-local is naive; treat it as Nairobi time
    local_naive = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    local = local_naive.replace(tzinfo=NAIROBI)
    return local.astimezone(timezone.utc).replace(tzinfo=None)

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

def compute_new_expiry_from_paid_at(sub, paid_at_utc_naive: datetime) -> datetime:
    minutes = int(getattr(sub.package, "duration_minutes", 0) or 0)
    if minutes <= 0:
        raise ValueError("Package duration_minutes is missing/invalid")

    current_expires = getattr(sub, "expires_at", None)
    base = current_expires if (current_expires and current_expires > paid_at_utc_naive) else paid_at_utc_naive
    return base + timedelta(minutes=minutes)

# ---------------------------------------------------------
# Helpers: void-safe checks + recompute expiry from history
# ---------------------------------------------------------

def _is_voided_tx(tx: Transaction) -> bool:
    """
    We treat a tx as voided if:
      - status == 'voided'
      OR
      - result_desc contains 'voided=1' (legacy-safe)
    """
    st = (getattr(tx, "status", "") or "").strip().lower()
    if st == "voided":
        return True

    desc = (getattr(tx, "result_desc", "") or "").lower()
    return "voided=1" in desc


def _is_success_tx(tx: Transaction) -> bool:
    return (getattr(tx, "status", "") or "").strip().lower() == "success"


def _is_manual_tx(tx: Transaction) -> bool:
    return (getattr(tx, "result_code", "") or "").strip().upper() == "MANUAL"


def _append_desc_flag(desc: str, flag: str) -> str:
    desc = (desc or "").strip()
    if not desc:
        return flag
    if flag.lower() in desc.lower():
        return desc
    return f"{desc} | {flag}"


def recompute_subscription_expiry_from_valid_payments(sub: Subscription) -> None:
    """
    Rebuilds sub.expires_at and sub.last_tx_id from historical TXs.

    Assumptions (based on your current schema):
      - Transaction has customer_id, package_id, status, created_at
      - Subscription has customer_id, package_id, expires_at, starts_at, last_tx_id
      - DB timestamps are UTC-naive (your convention)
    """
    if not sub or not sub.customer_id or not sub.package_id:
        return

    # Need duration for billing
    duration_minutes = int(getattr(sub.package, "duration_minutes", 0) or 0)
    if duration_minutes <= 0:
        duration_minutes = 43200  # 30 days fallback

    # Pull all SUCCESS tx for this customer+package
    txs = (
        Transaction.query
        .filter(
            Transaction.customer_id == sub.customer_id,
            Transaction.package_id == sub.package_id,
            Transaction.status == "success",
        )
        .order_by(Transaction.created_at.asc(), Transaction.id.asc())
        .all()
    )

    # Keep only non-voided
    valid = [t for t in txs if not _is_voided_tx(t)]

    if not valid:
        # No valid payments left
        sub.last_tx_id = None
        # leave expires_at as-is or clear — safest is keep but mark expired if past
        # If you prefer: sub.expires_at = None
        now = utcnow_naive()
        if sub.expires_at and sub.expires_at <= now:
            sub.status = "expired"
        return

    # Rebuild expiry by applying each payment in chronological order
    expires = None
    for t in valid:
        paid_at = getattr(t, "created_at", None)
        if not paid_at:
            continue

        # starts_at: first-ever payment time
        if not getattr(sub, "starts_at", None):
            sub.starts_at = paid_at

        base = expires if (expires and expires > paid_at) else paid_at
        expires = base + timedelta(minutes=duration_minutes)

    if expires is not None:
        sub.expires_at = expires

    # last_tx_id = newest valid tx
    sub.last_tx_id = valid[-1].id

    # status based on expiry vs now
    now = utcnow_naive()
    sub.status = "active" if (sub.expires_at and sub.expires_at > now) else "expired"

    if hasattr(sub, "updated_at"):
        sub.updated_at = utcnow_naive()


# ---------------------------------------------------------
# Route: void a MANUAL tx (no delete), then recompute expiry
# ---------------------------------------------------------
@admin.post("/transactions/<int:tx_id>/void")
@roles_required("support", "admin")  # or ("finance","admin") if you prefer
@limiter.limit("30 per minute")
def transaction_void(tx_id: int):
    """
    Void a manually entered payment:
      - Marks tx as voided (auditable, no deletion)
      - Recomputes subscription expiry from remaining valid tx history
    """
    tx = db.session.get(Transaction, tx_id)
    if not tx:
        flash("Transaction not found.", "error")
        return redirect(url_for("admin.transactions"))

    # Only allow voiding MANUAL payments (protects real M-Pesa records)
    if not _is_manual_tx(tx):
        flash("Only manually entered payments can be voided.", "error")
        return redirect(request.referrer or url_for("admin.transactions"))

    # Already voided?
    if _is_voided_tx(tx):
        flash("This payment is already voided.", "warning")
        return redirect(request.referrer or url_for("admin.transactions"))

    reason = (request.form.get("void_reason") or "").strip()
    if not reason:
        flash("Please provide a reason for voiding.", "error")
        return redirect(request.referrer or url_for("admin.transactions"))

    now = utcnow_naive()

    # Mark tx as voided
    tx.status = "voided"

    # Keep a readable audit trail in result_desc
    desc = (tx.result_desc or "Manual payment entry").strip()
    desc = _append_desc_flag(desc, "voided=1")
    desc = _append_desc_flag(desc, f"void_reason={reason}")
    tx.result_desc = desc

    # If your model has updated_at, set safely
    if hasattr(tx, "updated_at"):
        tx.updated_at = now

    try:
        db.session.add(tx)

        # Find the most likely subscription to recompute:
        # Your manual payments route applies to a selected subscription,
        # but Transaction doesn't store subscription_id in your snippet.
        #
        # Best-effort mapping: use the customer's latest subscription for that package.
        sub = (
            Subscription.query
            .filter(
                Subscription.customer_id == tx.customer_id,
                Subscription.package_id == tx.package_id,
            )
            .order_by(Subscription.id.desc())
            .first()
        )

        if sub:
            recompute_subscription_expiry_from_valid_payments(sub)
            db.session.add(sub)

        db.session.commit()

        audit(
            "manual_payment_voided",
            {
                "tx_id": tx.id,
                "customer_id": tx.customer_id,
                "package_id": tx.package_id,
                "reason": reason,
                "subscription_id": getattr(sub, "id", None) if sub else None,
            },
        )

        flash("Payment voided. Subscription recalculated.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Failed to void payment: {e}", "error")

    return redirect(request.referrer or url_for("admin.transactions"))
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

    # Finance snapshot: current UTC month
    now_utc_naive = utcnow_naive()
    start_utc, end_utc = _month_range_utc_naive(now_utc_naive)
    finance = profit_snapshot_range(start_utc, end_utc) or {"income_kes": 0, "expenses_kes": 0, "profit_kes": 0}

    # -----------------------------
    # Tickets KPIs
    # -----------------------------
    open_tickets = Ticket.query.filter(Ticket.status == "open").count()
    assigned_tickets = Ticket.query.filter(Ticket.status == "assigned").count()
    in_progress_tickets = Ticket.query.filter(Ticket.status == "in_progress").count()

    urgent_open_tickets = (
        Ticket.query
        .filter(Ticket.priority == "urgent", Ticket.status.in_(["open", "assigned", "in_progress", "waiting_customer"]))
        .count()
    )

    my_active_tickets = 0
    try:
        # show “my tickets” only when user has ops/support/admin role
        if getattr(current_user, "role", None) in {"ops", "support", "admin"}:
            my_active_tickets = (
                Ticket.query
                .filter(
                    Ticket.assigned_to_admin_id == getattr(current_user, "id", None),
                    Ticket.status.in_(["open", "assigned", "in_progress", "waiting_customer"]),
                )
                .count()
            )
    except Exception:
        my_active_tickets = 0

    tickets_kpis = {
        "open": int(open_tickets or 0),
        "assigned": int(assigned_tickets or 0),
        "in_progress": int(in_progress_tickets or 0),
        "urgent_active": int(urgent_open_tickets or 0),
        "my_active": int(my_active_tickets or 0),
    }

    return render_template(
        "admin/dashboard.html",
        customers_count=customers_count,
        active_subs=active_subs,
        pending_tx=pending_tx,
        success_tx=success_tx,
        failed_tx=failed_tx,
        recent=recent,
        finance=finance,
        tickets_kpis=tickets_kpis,
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

    return render_template("admin/customer_detail.html", customer=customer, subs=subs, txs=txs, sub_identity=sub_identity)

@admin.post("/customers/<int:customer_id>/payments/manual")
@roles_required("support", "admin")
@limiter.limit("30 per minute")
def customer_manual_payment(customer_id: int):
    """
    Manual payment entry (UI):
    - Creates Transaction(status=success) so it shows in the existing UI immediately
    - Extends subscription expiry from the admin-entered paid_at (historical), NOT from "now"
    - Supports optional admin expiry override (expires_at_override)
    - Updates subscription.last_tx_id
    """
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    # -----------------------------
    # Read form inputs
    # -----------------------------
    subscription_id = request.form.get("subscription_id", type=int)
    amount_raw = (request.form.get("amount") or "").strip()
    paid_at_raw = (request.form.get("paid_at") or "").strip()
    receipt = (request.form.get("receipt") or "").strip() or None
    note = (request.form.get("note") or "").strip() or None
    expires_override_raw = (request.form.get("expires_at_override") or "").strip()

    if not subscription_id:
        flash("Select a subscription.", "error")
        return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    sub = db.session.get(Subscription, int(subscription_id))
    if not sub or sub.customer_id != customer_id:
        flash("Subscription not found for this customer.", "error")
        return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    if not sub.package:
        flash("Subscription package missing.", "error")
        return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    # -----------------------------
    # Validate amount
    # -----------------------------
    try:
        amount_int = int(amount_raw)
        if amount_int <= 0:
            raise ValueError()
    except Exception:
        flash("Amount must be a positive whole number (e.g. 1000).", "error")
        return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    # -----------------------------
    # Parse paid_at: EAT datetime-local -> UTC naive (DB convention)
    # -----------------------------
    try:
        paid_at_utc_naive = parse_datetime_local_eat_to_utc_naive(paid_at_raw)
    except Exception as e:
        flash(f"Invalid Paid At: {e}", "error")
        return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    # -----------------------------
    # Optional expiry override: EAT datetime-local -> UTC naive
    # -----------------------------
    expires_override_utc_naive = None
    if expires_override_raw:
        try:
            expires_override_utc_naive = parse_datetime_local_eat_to_utc_naive(expires_override_raw)
        except Exception as e:
            flash(f"Invalid Expiry Override: {e}", "error")
            return redirect(url_for("admin.customer_detail", customer_id=customer_id))

        if expires_override_utc_naive <= paid_at_utc_naive:
            flash("Expiry override must be AFTER the paid date/time.", "error")
            return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    # -----------------------------
    # Compute expiry from PAID TIME (historical correctness)
    # -----------------------------
    duration_minutes = int(getattr(sub.package, "duration_minutes", 0) or 0)
    if duration_minutes <= 0:
        duration_minutes = 43200  # fallback 30 days

    base = sub.expires_at if (sub.expires_at and sub.expires_at > paid_at_utc_naive) else paid_at_utc_naive
    computed_expires = base + timedelta(minutes=duration_minutes)

    sub.status = "active"
    if not getattr(sub, "starts_at", None):
        sub.starts_at = paid_at_utc_naive

    sub.expires_at = expires_override_utc_naive or computed_expires

    # Avoid crash if Subscription has no updated_at
    if hasattr(sub, "updated_at"):
        sub.updated_at = utcnow_naive()

    # -----------------------------
    # Create Transaction (use paid_at as tx time)
    # -----------------------------
    desc = "Manual payment entry"
    if note:
        desc += f" | {note}"
    if expires_override_utc_naive is not None:
        desc += " | expiry_override=1"

    tx = Transaction(
        customer_id=customer.id,
        package_id=sub.package_id,
        amount=amount_int,
        status="success",
        checkout_request_id=None,
        merchant_request_id=None,
        mpesa_receipt=receipt,
        result_code="MANUAL",
        result_desc=desc,
        raw_callback_json=None,
    )

    # Stamp tx timestamps defensively (models differ)
    now = utcnow_naive()
    if hasattr(tx, "created_at") and not getattr(tx, "created_at", None):
        tx.created_at = paid_at_utc_naive
    if hasattr(tx, "updated_at"):
        tx.updated_at = now

    # -----------------------------
    # Persist atomically
    # -----------------------------
    try:
        db.session.add(tx)
        db.session.flush()  # tx.id available

        sub.last_tx_id = tx.id

        db.session.add(sub)
        db.session.commit()

        audit(
            "manual_payment_recorded",
            {
                "customer_id": customer.id,
                "sub_id": sub.id,
                "tx_id": tx.id,
                "amount": amount_int,
                "paid_at_utc": paid_at_utc_naive.isoformat(),
                "receipt": receipt,
                "note": note,
                "expiry_override": bool(expires_override_utc_naive),
                "expires_at_utc": (sub.expires_at.isoformat() if sub.expires_at else None),
            },
        )

        flash("Manual payment saved. Subscription updated.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Failed to save manual payment: {e}", "error")

    return redirect(url_for("admin.customer_detail", customer_id=customer_id))

# =========================================================
# Phase B — Customer Locations (Ops/Support/Admin)
# =========================================================

@admin.get("/customers/<int:customer_id>/locations")
@roles_required("ops", "support", "admin")
def customer_locations(customer_id: int):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    locations = (
        CustomerLocation.query
        .filter_by(customer_id=customer_id)
        .order_by(CustomerLocation.active.desc(), CustomerLocation.active_from_utc.desc(), CustomerLocation.id.desc())
        .all()
    )

    return render_template(
        "admin/customer_locations.html",
        customer=customer,
        locations=locations,
        now_eat=to_nairobi(utcnow_naive()),
    )


@admin.get("/customers/<int:customer_id>/locations/new")
@roles_required("ops", "admin")
def customer_location_new_get(customer_id: int):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    return render_template(
        "admin/location_form.html",
        customer=customer,
        loc=None,
        mode="new",
    )


@admin.post("/customers/<int:customer_id>/locations/new")
@roles_required("ops", "admin")
@limiter.limit("30 per minute")
def customer_location_new_post(customer_id: int):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    # fields
    label = (request.form.get("label") or "").strip() or None
    county = (request.form.get("county") or "").strip() or None
    town = (request.form.get("town") or "").strip() or None
    estate = (request.form.get("estate") or "").strip() or None
    apartment_name = (request.form.get("apartment_name") or "").strip() or None
    house_no = (request.form.get("house_no") or "").strip() or None
    landmark = (request.form.get("landmark") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    gps_lat_raw = (request.form.get("gps_lat") or "").strip()
    gps_lng_raw = (request.form.get("gps_lng") or "").strip()

    make_active = request.form.get("make_active") == "on"

    gps_lat = None
    gps_lng = None
    try:
        if gps_lat_raw:
            gps_lat = float(gps_lat_raw)
        if gps_lng_raw:
            gps_lng = float(gps_lng_raw)
    except ValueError:
        flash("GPS coordinates must be numbers.", "error")
        return redirect(url_for("admin.customer_location_new_get", customer_id=customer_id))

    now = utcnow_naive()

    loc = CustomerLocation(
        customer_id=customer.id,
        label=label,
        county=county,
        town=town,
        estate=estate,
        apartment_name=apartment_name,
        house_no=house_no,
        landmark=landmark,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        notes=notes,
        active=False,
        active_from_utc=now,  # will be used if activated
        active_to_utc=None,
        created_by_admin_id=getattr(current_user, "id", None),
        created_at=now,
        updated_at=now,
    )
    db.session.add(loc)
    db.session.flush()

    if make_active:
        # deactivate any existing active location + activate this one
        try:
            _activate_location_tx(customer.id, loc.id)
        except IntegrityError:
            db.session.rollback()
            flash("Could not activate location (another active location exists). Try again.", "error")
            return redirect(url_for("admin.customer_locations", customer_id=customer_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to activate location: {e}", "error")
            return redirect(url_for("admin.customer_locations", customer_id=customer_id))

    try:
        db.session.commit()
        flash("Location saved.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to save location: {e}", "error")

    return redirect(url_for("admin.customer_locations", customer_id=customer_id))


@admin.get("/locations/<int:location_id>/edit")
@roles_required("ops", "admin")
def customer_location_edit_get(location_id: int):
    loc = db.session.get(CustomerLocation, location_id)
    if not loc:
        flash("Location not found.", "error")
        return redirect(url_for("admin.customers"))

    customer = db.session.get(Customer, loc.customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.customers"))

    return render_template(
        "admin/location_form.html",
        customer=customer,
        loc=loc,
        mode="edit",
    )


@admin.post("/locations/<int:location_id>/edit")
@roles_required("ops", "admin")
@limiter.limit("30 per minute")
def customer_location_edit_post(location_id: int):
    loc = db.session.get(CustomerLocation, location_id)
    if not loc:
        flash("Location not found.", "error")
        return redirect(url_for("admin.customers"))

    # fields
    loc.label = (request.form.get("label") or "").strip() or None
    loc.county = (request.form.get("county") or "").strip() or None
    loc.town = (request.form.get("town") or "").strip() or None
    loc.estate = (request.form.get("estate") or "").strip() or None
    loc.apartment_name = (request.form.get("apartment_name") or "").strip() or None
    loc.house_no = (request.form.get("house_no") or "").strip() or None
    loc.landmark = (request.form.get("landmark") or "").strip() or None
    loc.notes = (request.form.get("notes") or "").strip() or None

    gps_lat_raw = (request.form.get("gps_lat") or "").strip()
    gps_lng_raw = (request.form.get("gps_lng") or "").strip()

    try:
        loc.gps_lat = float(gps_lat_raw) if gps_lat_raw else None
        loc.gps_lng = float(gps_lng_raw) if gps_lng_raw else None
    except ValueError:
        flash("GPS coordinates must be numbers.", "error")
        return redirect(url_for("admin.customer_location_edit_get", location_id=location_id))

    loc.updated_at = utcnow_naive()

    try:
        db.session.commit()
        flash("Location updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update location: {e}", "error")

    return redirect(url_for("admin.customer_locations", customer_id=loc.customer_id))


def _activate_location_tx(customer_id: int, location_id: int) -> None:
    """
    Transaction-safe activation:
    - Close any currently active location
    - Activate the chosen location
    DB enforces "one active" via partial unique index.
    """
    now = utcnow_naive()

    # close current active
    active_loc = (
        CustomerLocation.query
        .filter(CustomerLocation.customer_id == customer_id, CustomerLocation.active.is_(True))
        .with_for_update(of=CustomerLocation)
        .first()
    )
    if active_loc and active_loc.id != location_id:
        active_loc.active = False
        active_loc.active_to_utc = now
        active_loc.updated_at = now

    # activate selected
    loc = (
        CustomerLocation.query
        .filter(CustomerLocation.id == location_id, CustomerLocation.customer_id == customer_id)
        .with_for_update(of=CustomerLocation)
        .first()
    )
    if not loc:
        raise ValueError("Location not found for that customer.")

    loc.active = True
    # If it was previously active then closed, keep history clean by starting new active_from
    loc.active_from_utc = now
    loc.active_to_utc = None
    loc.updated_at = now


@admin.post("/locations/<int:location_id>/activate")
@roles_required("ops", "admin")
@limiter.limit("30 per minute")
def customer_location_activate(location_id: int):
    loc = db.session.get(CustomerLocation, location_id)
    if not loc:
        flash("Location not found.", "error")
        return redirect(url_for("admin.customers"))

    try:
        _activate_location_tx(loc.customer_id, loc.id)
        db.session.commit()
        flash("Location activated.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Could not activate location (another active exists). Try again.", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to activate location: {e}", "error")

    return redirect(url_for("admin.customer_locations", customer_id=loc.customer_id))


# =========================================================
# Phase B — Tickets (Ops/Support/Admin)
# =========================================================

def _ticket_code_for_id(ticket_id: int, opened_at_utc: datetime | None = None) -> str:
    year = (opened_at_utc or utcnow_naive()).year
    return f"TCK-{year}-{ticket_id:06d}"


@admin.get("/tickets")
@roles_required("ops", "support", "admin")
def tickets():
    status = (request.args.get("status") or "").strip().lower()
    priority = (request.args.get("priority") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    q = (request.args.get("q") or "").strip()
    assigned_to = (request.args.get("assigned_to") or "").strip().lower()

    query = Ticket.query

    # -----------------------------
    # Standard filters
    # -----------------------------
    if status:
        query = query.filter(Ticket.status == status)

    if priority:
        query = query.filter(Ticket.priority == priority)

    if category:
        query = query.filter(Ticket.category == category)

    # -----------------------------
    # Assigned-to filter (NEW)
    # -----------------------------
    if assigned_to:
        if assigned_to == "me":
            if current_user.is_authenticated:
                query = query.filter(
                    Ticket.assigned_to_admin_id == getattr(current_user, "id", None)
                )
        elif assigned_to.isdigit():
            query = query.filter(
                Ticket.assigned_to_admin_id == int(assigned_to)
            )

    # -----------------------------
    # Search
    # -----------------------------
    if q:
        query = (
            query.join(Customer, Ticket.customer_id == Customer.id)
            .outerjoin(Subscription, Ticket.subscription_id == Subscription.id)
            .filter(
                or_(
                    Ticket.code.ilike(f"%{q}%"),
                    Ticket.subject.ilike(f"%{q}%"),
                    Customer.phone.ilike(f"%{q}%"),
                    Subscription.pppoe_username.ilike(f"%{q}%"),
                    Subscription.hotspot_username.ilike(f"%{q}%"),
                )
            )
        )

    rows = query.order_by(Ticket.created_at.desc()).limit(400).all()

    # technician list (for filters / assignment UI)
    techs = (
        AdminUser.query
        .filter(AdminUser.is_active.is_(True))
        .filter(AdminUser.role.in_(["ops", "support", "admin"]))
        .order_by(AdminUser.role.asc(), AdminUser.email.asc())
        .all()
    )

    return render_template(
        "admin/tickets_list.html",
        tickets=rows,
        status=status,
        priority=priority,
        category=category,
        q=q,
        assigned_to=assigned_to,
        techs=techs,
    )


@admin.get("/tickets/new")
@roles_required("ops", "support", "admin")
def ticket_new_get():
    customer_id_raw = (request.args.get("customer_id") or "").strip()
    customer = db.session.get(Customer, int(customer_id_raw)) if customer_id_raw.isdigit() else None

    # simple picklists
    categories = ["outage", "relocation", "installation", "billing", "speed", "hardware", "other"]
    priorities = ["low", "med", "high", "urgent"]

    # technicians
    techs = (
        AdminUser.query
        .filter(AdminUser.is_active.is_(True))
        .filter(AdminUser.role.in_(["ops", "support", "admin"]))
        .order_by(AdminUser.role.asc(), AdminUser.email.asc())
        .all()
    )

    # customer subscriptions + locations if customer preselected
    subs = []
    locs = []
    if customer:
        subs = Subscription.query.filter_by(customer_id=customer.id).order_by(Subscription.created_at.desc()).limit(30).all()
        locs = CustomerLocation.query.filter_by(customer_id=customer.id).order_by(CustomerLocation.active.desc(), CustomerLocation.id.desc()).all()

    pre_sub_id = (request.args.get("subscription_id") or "").strip()
    pre_loc_id = (request.args.get("location_id") or "").strip()

    # If no location explicitly passed, auto-pick active location
    if customer and not pre_loc_id:
        active_loc = (
            CustomerLocation.query
            .filter_by(customer_id=customer.id, active=True)
            .order_by(CustomerLocation.active_from_utc.desc())
            .first()
        )
        if active_loc:
            pre_loc_id = str(active_loc.id)

    return render_template(
        "admin/ticket_new.html",
        customer=customer,
        categories=categories,
        priorities=priorities,
        techs=techs,
        subs=subs,
        locs=locs,
        pre_sub_id=pre_sub_id,
        pre_loc_id=pre_loc_id,
    )

@admin.post("/tickets/new")
@roles_required("ops", "support", "admin")
@limiter.limit("30 per minute")
def ticket_new_post():
    customer_id_raw = (request.form.get("customer_id") or "").strip()
    subject = (request.form.get("subject") or "").strip()
    description = (request.form.get("description") or "").strip()

    category = (request.form.get("category") or "outage").strip().lower()
    priority = (request.form.get("priority") or "med").strip().lower()

    subscription_id_raw = (request.form.get("subscription_id") or "").strip()
    location_id_raw = (request.form.get("location_id") or "").strip()

    assigned_to_raw = (request.form.get("assigned_to_admin_id") or "").strip()

    if not customer_id_raw.isdigit():
        flash("Select a valid customer.", "error")
        return redirect(url_for("admin.ticket_new_get"))

    customer = db.session.get(Customer, int(customer_id_raw))
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("admin.ticket_new_get"))

    if not subject:
        flash("Subject is required.", "error")
        return redirect(url_for("admin.ticket_new_get", customer_id=customer.id))

    subscription_id = int(subscription_id_raw) if subscription_id_raw.isdigit() else None
    location_id = int(location_id_raw) if location_id_raw.isdigit() else None
    assigned_to_admin_id = int(assigned_to_raw) if assigned_to_raw.isdigit() else None

    now = utcnow_naive()

    # Temporary code, then replace after flush with deterministic code from ID
    tmp_code = f"TCK-TMP-{secrets.token_hex(4).upper()}"

    t = Ticket(
        code=tmp_code,
        customer_id=customer.id,
        subscription_id=subscription_id,
        location_id=location_id,
        category=category or "outage",
        priority=priority or "med",
        status="open",
        subject=subject,
        description=description or None,
        opened_at_utc=now,
        created_by_admin_id=getattr(current_user, "id", None),
        assigned_to_admin_id=assigned_to_admin_id,
        created_at=now,
        updated_at=now,
    )
    db.session.add(t)
    db.session.flush()

    # Final code from ID
    t.code = _ticket_code_for_id(t.id, t.opened_at_utc)

    # Auto-status if assigned
    if assigned_to_admin_id:
        t.status = "assigned"

    # Timeline seed
    u0 = TicketUpdate(
        ticket_id=t.id,
        actor_admin_id=getattr(current_user, "id", None),
        message="Ticket opened.",
        status_from=None,
        status_to=t.status,
        assigned_from_admin_id=None,
        assigned_to_admin_id=assigned_to_admin_id,
        created_at=now,
    )
    db.session.add(u0)

    try:
        db.session.commit()
        flash(f"Ticket created: {t.code}", "success")
    except IntegrityError:
        db.session.rollback()
        flash("DB conflict while creating ticket. Please retry.", "error")
        return redirect(url_for("admin.ticket_new_get", customer_id=customer.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create ticket: {e}", "error")
        return redirect(url_for("admin.ticket_new_get", customer_id=customer.id))

    return redirect(url_for("admin.ticket_detail", ticket_id=t.id))


@admin.get("/tickets/<int:ticket_id>")
@roles_required("ops", "support", "admin")
def ticket_detail(ticket_id: int):
    t = db.session.get(Ticket, ticket_id)
    if not t:
        flash("Ticket not found.", "error")
        return redirect(url_for("admin.tickets"))

    # preload dropdowns
    techs = (
        AdminUser.query
        .filter(AdminUser.is_active.is_(True))
        .filter(AdminUser.role.in_(["ops", "support", "admin"]))
        .order_by(AdminUser.role.asc(), AdminUser.email.asc())
        .all()
    )

    categories = ["outage", "relocation", "installation", "billing", "speed", "hardware", "other"]
    priorities = ["low", "med", "high", "urgent"]
    statuses = ["open", "assigned", "in_progress", "waiting_customer", "resolved", "closed", "cancelled"]

    updates = (
        TicketUpdate.query
        .filter_by(ticket_id=t.id)
        .order_by(TicketUpdate.created_at.asc(), TicketUpdate.id.asc())
        .all()
    )

    return render_template(
        "admin/ticket_detail.html",
        t=t,
        updates=updates,
        techs=techs,
        categories=categories,
        priorities=priorities,
        statuses=statuses,
        now_eat=to_nairobi(utcnow_naive()),
    )


@admin.post("/tickets/<int:ticket_id>/update")
@roles_required("ops", "support", "admin")
@limiter.limit("60 per minute")
def ticket_add_update(ticket_id: int):
    t = db.session.get(Ticket, ticket_id)
    if not t:
        flash("Ticket not found.", "error")
        return redirect(url_for("admin.tickets"))

    msg = (request.form.get("message") or "").strip()
    if not msg:
        flash("Update message cannot be empty.", "error")
        return redirect(url_for("admin.ticket_detail", ticket_id=t.id))

    now = utcnow_naive()

    u = TicketUpdate(
        ticket_id=t.id,
        actor_admin_id=getattr(current_user, "id", None),
        message=msg,
        created_at=now,
    )
    db.session.add(u)
    t.updated_at = now

    try:
        db.session.commit()
        flash("Update added.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to add update: {e}", "error")

    return redirect(url_for("admin.ticket_detail", ticket_id=t.id))


@admin.post("/tickets/<int:ticket_id>/assign")
@roles_required("ops", "support", "admin")
@limiter.limit("60 per minute")
def ticket_assign(ticket_id: int):
    t = db.session.get(Ticket, ticket_id)
    if not t:
        flash("Ticket not found.", "error")
        return redirect(url_for("admin.tickets"))

    assigned_to_raw = (request.form.get("assigned_to_admin_id") or "").strip()
    assigned_to_admin_id = int(assigned_to_raw) if assigned_to_raw.isdigit() else None

    now = utcnow_naive()
    prev = t.assigned_to_admin_id

    t.assigned_to_admin_id = assigned_to_admin_id
    if assigned_to_admin_id and (t.status in {"open"}):
        t.status = "assigned"
    t.updated_at = now

    u = TicketUpdate(
        ticket_id=t.id,
        actor_admin_id=getattr(current_user, "id", None),
        message=None,
        assigned_from_admin_id=prev,
        assigned_to_admin_id=assigned_to_admin_id,
        status_from=None,
        status_to=t.status,
        created_at=now,
    )
    db.session.add(u)

    try:
        db.session.commit()
        flash("Assignment updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update assignment: {e}", "error")

    return redirect(url_for("admin.ticket_detail", ticket_id=t.id))


@admin.post("/tickets/<int:ticket_id>/status")
@roles_required("ops", "support", "admin")
@limiter.limit("60 per minute")
def ticket_set_status(ticket_id: int):
    t = db.session.get(Ticket, ticket_id)
    if not t:
        flash("Ticket not found.", "error")
        return redirect(url_for("admin.tickets"))

    status_to = (request.form.get("status") or "").strip().lower()
    allowed = {"open", "assigned", "in_progress", "waiting_customer", "resolved", "closed", "cancelled"}
    if status_to not in allowed:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.ticket_detail", ticket_id=t.id))

    now = utcnow_naive()
    prev = t.status

    t.status = status_to
    t.updated_at = now

    if status_to == "resolved" and not t.resolved_at_utc:
        t.resolved_at_utc = now
    if status_to in {"closed", "cancelled"} and not t.closed_at_utc:
        t.closed_at_utc = now

    u = TicketUpdate(
        ticket_id=t.id,
        actor_admin_id=getattr(current_user, "id", None),
        message=None,
        status_from=prev,
        status_to=status_to,
        created_at=now,
    )
    db.session.add(u)

    try:
        db.session.commit()
        flash("Status updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update status: {e}", "error")

    return redirect(url_for("admin.ticket_detail", ticket_id=t.id))

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
    pppoe_username_raw = (request.form.get("pppoe_username") or "").strip().upper()
    months_raw = (request.form.get("months") or "1").strip()

    enable_now = request.form.get("enable_now") == "on"
    set_customer_pppoe = request.form.get("set_customer_pppoe") == "on"

    # -----------------------------
    # Validate phone
    # -----------------------------
    phone = normalize_phone(phone_raw)
    if not phone or not phone.startswith("2547"):
        flash("Phone is required (use 0712… or 2547… format).", "error")
        return redirect(url_for("admin.pppoe_new"))

    # -----------------------------
    # Validate package
    # -----------------------------
    try:
        package_id = int(package_id_raw)
    except Exception:
        flash("Select a valid PPPoE package.", "error")
        return redirect(url_for("admin.pppoe_new"))

    package = db.session.get(Package, package_id)
    if not package or not (package.code or "").startswith("pppoe_"):
        flash("Select a valid PPPoE package.", "error")
        return redirect(url_for("admin.pppoe_new"))

    # -----------------------------
    # Validate months (ALLOW 0)
    # -----------------------------
    try:
        months = int(months_raw)
        if months < 0 or months > 36:
            raise ValueError()
    except Exception:
        flash("Months must be between 0 and 36.", "error")
        return redirect(url_for("admin.pppoe_new"))

    # -----------------------------
    # Username (auto-suggest if blank)
    # -----------------------------
    pppoe_username = pppoe_username_raw or _next_pppoe_username()
    if not _parse_pppoe_username(pppoe_username):
        flash("Invalid PPPoE username format. Use D001..D999 or DA0001..", "error")
        return redirect(url_for("admin.pppoe_new"))

    # -----------------------------
    # Find/create customer
    # -----------------------------
    customer = Customer.query.filter_by(phone=phone).first()
    if not customer:
        customer = Customer(phone=phone)
        db.session.add(customer)
        db.session.flush()

    # -----------------------------
    # Prevent username collisions with ACTIVE subs
    # -----------------------------
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

    # -----------------------------
    # Optionally set customer PPPoE creds
    # -----------------------------
    if set_customer_pppoe:
        if hasattr(customer, "pppoe_username"):
            if getattr(customer, "pppoe_username", None) and customer.pppoe_username != pppoe_username:
                flash(f"Customer already has PPPoE username {customer.pppoe_username}. Not overwritten.", "warning")
            else:
                customer.pppoe_username = pppoe_username

        if hasattr(customer, "pppoe_password") and not getattr(customer, "pppoe_password", None):
            customer.pppoe_password = _gen_pppoe_password()

    # -----------------------------
    # Build subscription (0 months => pending shell)
    # -----------------------------
    now = utcnow_naive()

    duration_minutes = int(getattr(package, "duration_minutes", 0) or 0)
    if duration_minutes <= 0:
        duration_minutes = 43200  # 30 days fallback

    if months == 0:
        status = "pending"
        starts_at = None
        expires_at = None
        # If they chose enable_now but months=0, we can't enable on router
        if enable_now:
            flash("0 months creates a pending subscription. Router enable skipped.", "warning")
            enable_now = False
    else:
        status = "active"
        starts_at = now
        expires_at = now + timedelta(minutes=duration_minutes * months)

    sub = Subscription(
        customer_id=customer.id,
        package_id=package.id,
        service_type="pppoe",
        status=status,
        starts_at=starts_at,
        expires_at=expires_at,
        pppoe_username=pppoe_username,
        hotspot_username=None,
        router_username=None,  # legacy; do not use
    )
    db.session.add(sub)
    db.session.flush()

    # -----------------------------
    # Create Transaction ONLY if months > 0
    # -----------------------------
    tx = None
    if months > 0:
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

    # -----------------------------
    # Commit
    # -----------------------------
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

    # -----------------------------
    # Optional router provisioning
    # -----------------------------
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
                audit(
                    "pppoe_router_provision_failed",
                    {"sub_id": sub.id, "pppoe_username": pppoe_username, "error": str(e)},
                )

    # -----------------------------
    # Audit + redirect
    # -----------------------------
    audit(
        "pppoe_subscription_created",
        {
            "sub_id": sub.id,
            "customer_id": customer.id,
            "phone": phone,
            "pppoe_username": pppoe_username,
            "package_code": getattr(package, "code", None),
            "months": months,
            "status": status,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "router_enabled": router_enabled,
            "router_provision_attempted": bool(enable_now),
        },
    )

    if months == 0:
        flash(f"PPPoE subscription shell created: {pppoe_username} (pending; no expiry set)", "success")
        return redirect(url_for("admin.subscriptions", svc="pppoe", status="pending", q=pppoe_username))

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


@admin.route("/users/new", methods=["POST"])
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

@admin.get("/public-leads")
@login_required
def public_leads_list():
    kind = (request.args.get("kind") or "").strip().lower()
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip().lower()  # "", "open", "handled"
    limit = 200

    where = []
    params = {"limit": limit}

    if kind in {"coverage", "quote"}:
        where.append("kind = :kind")
        params["kind"] = kind

    if status in {"open", "handled"}:
        where.append("handled = :handled")
        params["handled"] = (status == "handled")

    if q:
        where.append(
            "(name ILIKE :q OR phone ILIKE :q OR estate ILIKE :q OR coalesce(message,'') ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    where_sql = (" where " + " and ".join(where)) if where else ""

    rows = db.session.execute(
        db.text(
            f"""
            select id, kind, name, phone, estate, message, source, created_at,
                   handled, handled_at, handled_by
            from public_leads
            {where_sql}
            order by id desc
            limit :limit
            """
        ),
        params,
    ).mappings().all()

    return render_template(
        "admin/public_leads.html",
        items=[dict(r) for r in rows],
        kind=kind,
        q=q,
        status=status,
    )

@admin.post("/public-leads/<int:lead_id>/handle")
@login_required
@roles_required("admin")
def public_lead_handle(lead_id: int):
    db.session.execute(
        db.text("""
            update public_leads
               set handled = true,
                   handled_at = now(),
                   handled_by = :by
             where id = :id
        """),
        {"id": lead_id, "by": (getattr(current_user, "email", None) or getattr(current_user, "name", None) or "admin")}
    )
    db.session.commit()
    flash("Lead marked as handled.", "success")
    return redirect(url_for("admin.public_leads_list"))

@admin.post("/public-leads/<int:lead_id>/unhandle")
@login_required
@roles_required("admin")
def public_lead_unhandle(lead_id: int):
    db.session.execute(
        db.text("""
            update public_leads
               set handled = false,
                   handled_at = null,
                   handled_by = null
             where id = :id
        """),
        {"id": lead_id}
    )
    db.session.commit()
    flash("Lead marked as unhandled.", "success")
    return redirect(url_for("admin.public_leads_list"))

