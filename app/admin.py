# app/admin.py
from __future__ import annotations

import json
import re
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
from sqlalchemy import func

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
    # If you later put this behind a proxy, add ProxyFix and then trust X-Forwarded-For.
    try:
        return request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr
    except Exception:
        return None


def audit(action: str, meta: dict | None = None, admin_user_id: int | None = None) -> None:
    """
    Best-effort admin audit logging. Never breaks user flow.
    """
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

    # Update password
    current_user.set_password(new_pw)
    db.session.commit()

    # Audit success
    audit("password_changed")

    # 🔄 Force re-login after password change
    logout_user()
    session.clear()

    flash("Password updated. Please log in again.", "success")
    return redirect(url_for("admin.login_get"))


# =========================================================
# Revenue helpers (Nairobi boundaries; DB stores naive UTC)
# =========================================================
def nairobi_range_starts_utc_naive() -> dict:
    """
    Returns UTC-naive datetimes that match Nairobi day/week/month boundaries.
    DB stores naive UTC (datetime.utcnow).
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


def revenue_totals() -> dict:
    """Totals for successful payments only."""
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

    # Safe redirect (internal only)
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
# Subscriptions
# =========================================================
@admin.get("/subscriptions")
@login_required
def subscriptions():
    status = (request.args.get("status") or "").strip().lower()
    q = (request.args.get("q") or "").strip()
    pkg = (request.args.get("pkg") or "").strip()

    query = Subscription.query

    if status in {"pending", "active", "expired"}:
        query = query.filter(Subscription.status == status)

    if q:
        query = query.filter(Subscription.router_username.ilike(f"%{q}%"))

    if pkg:
        query = query.join(Subscription.package).filter(Package.code == pkg)

    rows = query.order_by(Subscription.created_at.desc()).limit(300).all()

    now = utcnow_naive()

    def fmt_remaining(expires_at):
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
        items.append({"s": s, "remaining": remaining, "is_expired": is_expired})

    pkg_codes = [p.code for p in Package.query.order_by(Package.price_kes.asc()).all()]

    return render_template(
        "admin/subscriptions.html",
        items=items,
        status=status,
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

    if not current_app.config.get("MIKROTIK_ENABLED", False):
        flash("Router control is OFF (MIKROTIK_ENABLED=false).", "error")
        return redirect(url_for("admin.subscriptions"))

    try:
        remaining_minutes = int((sub.expires_at - now).total_seconds() // 60)
        remaining_minutes = max(1, remaining_minutes)

        agent_enable(
            current_app,
            sub.router_username,
            sub.package.mikrotik_profile,
            remaining_minutes,
        )
        flash("Router enable command sent.", "success")
    except Exception as e:
        flash(f"Router enable failed: {e}", "error")

    return redirect(url_for("admin.subscriptions"))


# =========================================================
# Transactions (filters + totals + Nairobi display time)
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

    return render_template(
        "admin/transactions.html",
        items=items,
        status=status,
        totals=totals,
    )


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
