from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import AdminUser, Customer, Subscription, Transaction

admin = Blueprint("admin", __name__, template_folder="templates")


@admin.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


@admin.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = AdminUser.query.filter_by(email=email).first()
    if not user or not user.is_active or not user.check_password(password):
        flash("Invalid credentials", "error")
        return redirect(url_for("admin.login"))

    login_user(user)
    return redirect(url_for("admin.dashboard"))


@admin.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin.get("/")
@login_required
def dashboard():
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    stats = {
        "customers": Customer.query.count(),
        "subs_active": Subscription.query.filter_by(status="active").count(),
        "subs_pending": Subscription.query.filter_by(status="pending").count(),
        "tx_success_today": Transaction.query.filter(Transaction.status == "success", Transaction.created_at >= day_ago).count(),
        "tx_success_7d": Transaction.query.filter(Transaction.status == "success", Transaction.created_at >= week_ago).count(),
        "tx_failed_7d": Transaction.query.filter(Transaction.status == "failed", Transaction.created_at >= week_ago).count(),
    }

    recent_tx = Transaction.query.order_by(Transaction.id.desc()).limit(20).all()
    recent_subs = Subscription.query.order_by(Subscription.id.desc()).limit(20).all()

    return render_template("admin/dashboard.html", stats=stats, recent_tx=recent_tx, recent_subs=recent_subs)


@admin.get("/customers")
@login_required
def customers():
    q = (request.args.get("q") or "").strip()
    query = Customer.query
    if q:
        query = query.filter(Customer.phone.ilike(f"%{q}%"))
    rows = query.order_by(Customer.id.desc()).limit(200).all()
    return render_template("admin/customers.html", rows=rows, q=q)


@admin.get("/subscriptions")
@login_required
def subscriptions():
    status = (request.args.get("status") or "").strip()
    query = Subscription.query
    if status:
        query = query.filter(Subscription.status == status)
    rows = query.order_by(Subscription.id.desc()).limit(200).all()
    return render_template("admin/subscriptions.html", rows=rows, status=status)


@admin.get("/transactions")
@login_required
def transactions():
    status = (request.args.get("status") or "").strip()
    query = Transaction.query
    if status:
        query = query.filter(Transaction.status == status)
    rows = query.order_by(Transaction.id.desc()).limit(200).all()
    return render_template("admin/transactions.html", rows=rows, status=status)

@admin.get("/public-leads")
@login_required
def public_leads_list():
    """
    Admin view: list public leads coming from the marketing website forms.
    Supports filters:
      - ?kind=coverage|quote
      - ?q=search (name/phone/estate)
    """
    kind = (request.args.get("kind") or "").strip().lower()
    q = (request.args.get("q") or "").strip()
    limit = 200

    where = []
    params = {"limit": limit}

    if kind in {"coverage", "quote"}:
        where.append("kind = :kind")
        params["kind"] = kind

    if q:
        where.append(
            "(name ILIKE :q OR phone ILIKE :q OR estate ILIKE :q OR coalesce(message,'') ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    where_sql = (" where " + " and ".join(where)) if where else ""

    rows = db.session.execute(
        db.text(
            f"""
            select id, kind, name, phone, estate, message, source, created_at
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
    )
