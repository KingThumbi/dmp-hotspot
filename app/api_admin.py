from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import or_

from .models import db, Customer, PublicLead, Subscription, Ticket, Transaction

api_admin_bp = Blueprint("api_admin", __name__)


# =========================================================
# Core helpers
# =========================================================

def _json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def _user_is_authenticated() -> bool:
    try:
        return bool(getattr(current_user, "is_authenticated", False))
    except Exception:
        return False


def _user_role() -> str | None:
    role = getattr(current_user, "role", None)
    if role is None:
        return None
    return str(role).strip().lower()


def _is_admin_user() -> bool:
    """
    Best-effort admin check.

    Conservative but flexible:
    - requires an authenticated user
    - if a role exists, it must look like an admin/staff role
    - if no role attribute exists, authenticated user is allowed

    If your production auth uses a stricter decorator/helper, swap this logic.
    """
    if not _user_is_authenticated():
        return False

    role = _user_role()
    if role is None:
        return True

    return role in {
        "admin",
        "superadmin",
        "super_admin",
        "ops",
        "operations",
        "support",
        "staff",
        "manager",
    }


def admin_api_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_admin_user():
            return _json_error("Authentication required.", 401)
        return fn(*args, **kwargs)

    return wrapper


def _parse_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
        return default


def _safe_count(query) -> int:
    try:
        return int(query.count())
    except Exception:
        return 0


def _iso(value) -> str | None:
    try:
        return value.isoformat() if value is not None else None
    except Exception:
        return None


def _now_utc():
    return datetime.now(timezone.utc)


def _display_name(obj: Any) -> str | None:
    if obj is None:
        return None

    for attr in ("full_name", "name", "username", "email"):
        value = getattr(obj, attr, None)
        if value:
            return value

    first_name = getattr(obj, "first_name", None)
    last_name = getattr(obj, "last_name", None)
    if first_name or last_name:
        full = f"{first_name or ''} {last_name or ''}".strip()
        return full or None

    return None


def _current_user_payload() -> dict[str, Any]:
    return {
        "id": getattr(current_user, "id", None),
        "name": _display_name(current_user),
        "email": getattr(current_user, "email", None),
        "role": getattr(current_user, "role", None),
    }


# =========================================================
# Dashboard counters
# =========================================================

def _count_active_subscriptions() -> int:
    try:
        if hasattr(Subscription, "status"):
            return _safe_count(
                Subscription.query.filter(Subscription.status == "active")
            )
        if hasattr(Subscription, "is_active"):
            return _safe_count(
                Subscription.query.filter(Subscription.is_active.is_(True))
            )
        return _safe_count(Subscription.query)
    except Exception:
        return 0


def _count_expired_subscriptions() -> int:
    try:
        if hasattr(Subscription, "status"):
            return _safe_count(
                Subscription.query.filter(
                    Subscription.status.in_(["expired", "inactive", "suspended"])
                )
            )
        return 0
    except Exception:
        return 0


def _count_open_tickets() -> int:
    try:
        return _safe_count(
            Ticket.query.filter(
                Ticket.status.in_(
                    ["open", "assigned", "in_progress", "waiting_customer"]
                )
            )
        )
    except Exception:
        return 0


def _count_public_leads() -> int:
    try:
        return _safe_count(PublicLead.query)
    except Exception:
        return 0


def _count_unhandled_public_leads() -> int:
    """
    Some deployments may not expose `handled` on PublicLead.
    Fall back to total leads if the field is unavailable.
    """
    try:
        if hasattr(PublicLead, "handled"):
            return _safe_count(
                PublicLead.query.filter(PublicLead.handled.is_(False))
            )
        return _count_public_leads()
    except Exception:
        return _count_public_leads()


# =========================================================
# Serializers
# =========================================================

def _serialize_public_lead(lead: PublicLead) -> dict[str, Any]:
    return {
        "id": getattr(lead, "id", None),
        "kind": getattr(lead, "kind", None),
        "name": getattr(lead, "name", None),
        "phone": getattr(lead, "phone", None),
        "email": getattr(lead, "email", None) if hasattr(lead, "email") else None,
        "estate": getattr(lead, "estate", None),
        "message": getattr(lead, "message", None),
        "source": getattr(lead, "source", None),
        "handled": getattr(lead, "handled", None) if hasattr(lead, "handled") else None,
        "created_at": _iso(getattr(lead, "created_at", None)),
    }


def _serialize_ticket(ticket: Ticket) -> dict[str, Any]:
    customer = getattr(ticket, "customer", None)
    assigned_to = getattr(ticket, "assigned_to", None)

    return {
        "id": getattr(ticket, "id", None),
        "code": getattr(ticket, "code", None),
        "customer_id": getattr(ticket, "customer_id", None),
        "customer_name": _display_name(customer),
        "category": getattr(ticket, "category", None),
        "priority": getattr(ticket, "priority", None),
        "status": getattr(ticket, "status", None),
        "subject": getattr(ticket, "subject", None),
        "description": getattr(ticket, "description", None),
        "assigned_to_admin_id": getattr(ticket, "assigned_to_admin_id", None),
        "assigned_to_name": _display_name(assigned_to),
        "opened_at_utc": _iso(getattr(ticket, "opened_at_utc", None)),
        "created_at": _iso(getattr(ticket, "created_at", None)),
    }


def _serialize_ticket_update(update) -> dict[str, Any]:
    actor = getattr(update, "actor", None)
    assigned_to = getattr(update, "assigned_to", None)
    assigned_from = getattr(update, "assigned_from", None)

    return {
        "id": getattr(update, "id", None),
        "actor_admin_id": getattr(update, "actor_admin_id", None),
        "actor_name": _display_name(actor),
        "message": getattr(update, "message", None),
        "status_from": getattr(update, "status_from", None),
        "status_to": getattr(update, "status_to", None),
        "assigned_from_admin_id": getattr(update, "assigned_from_admin_id", None),
        "assigned_from_name": _display_name(assigned_from),
        "assigned_to_admin_id": getattr(update, "assigned_to_admin_id", None),
        "assigned_to_name": _display_name(assigned_to),
        "created_at": _iso(getattr(update, "created_at", None)),
    }


def _serialize_customer(customer: Customer) -> dict[str, Any]:
    return {
        "id": getattr(customer, "id", None),
        "full_name": _display_name(customer),
        "first_name": getattr(customer, "first_name", None) if hasattr(customer, "first_name") else None,
        "last_name": getattr(customer, "last_name", None) if hasattr(customer, "last_name") else None,
        "email": getattr(customer, "email", None) if hasattr(customer, "email") else None,
        "phone": getattr(customer, "phone", None) if hasattr(customer, "phone") else None,
        "account_number": getattr(customer, "account_number", None) if hasattr(customer, "account_number") else None,
        "customer_number": getattr(customer, "customer_number", None) if hasattr(customer, "customer_number") else None,
        "city": getattr(customer, "city", None) if hasattr(customer, "city") else None,
        "address": getattr(customer, "address", None) if hasattr(customer, "address") else None,
        "is_active": getattr(customer, "is_active", None) if hasattr(customer, "is_active") else None,
        "created_at": _iso(getattr(customer, "created_at", None)),
        "updated_at": _iso(getattr(customer, "updated_at", None)),
    }


def _serialize_customer_location(location) -> dict[str, Any]:
    title = (
        getattr(location, "name", None)
        or getattr(location, "label", None)
        or getattr(location, "estate", None)
    )

    return {
        "id": getattr(location, "id", None),
        "name": title,
        "label": getattr(location, "label", None) if hasattr(location, "label") else None,
        "estate": getattr(location, "estate", None) if hasattr(location, "estate") else None,
        "address": getattr(location, "address", None) if hasattr(location, "address") else None,
        "is_primary": getattr(location, "is_primary", None) if hasattr(location, "is_primary") else None,
        "created_at": _iso(getattr(location, "created_at", None)),
    }


def _serialize_customer_ticket(ticket: Ticket) -> dict[str, Any]:
    return {
        "id": getattr(ticket, "id", None),
        "code": getattr(ticket, "code", None),
        "subject": getattr(ticket, "subject", None),
        "status": getattr(ticket, "status", None),
        "priority": getattr(ticket, "priority", None),
        "category": getattr(ticket, "category", None),
        "opened_at_utc": _iso(getattr(ticket, "opened_at_utc", None)),
    }


def _serialize_subscription(subscription: Subscription) -> dict[str, Any]:
    customer = getattr(subscription, "customer", None)
    package = getattr(subscription, "package", None)
    location = getattr(subscription, "location", None)

    package_name = None
    if package is not None:
        package_name = getattr(package, "name", None) or getattr(package, "code", None)

    # Prefer subscription-linked location first
    location_name = None
    location_id = getattr(subscription, "location_id", None) if hasattr(subscription, "location_id") else None

    if location is not None:
        location_name = (
            getattr(location, "name", None)
            or getattr(location, "label", None)
            or getattr(location, "estate", None)
        )

    # Fallback: derive from customer's primary/first location
    if not location_name and customer is not None:
        customer_locations = None

        if hasattr(customer, "locations"):
            customer_locations = getattr(customer, "locations", None)
        elif hasattr(customer, "customer_locations"):
            customer_locations = getattr(customer, "customer_locations", None)

        if customer_locations:
            chosen_location = None

            for loc in customer_locations:
                if getattr(loc, "is_primary", False):
                    chosen_location = loc
                    break

            if chosen_location is None:
                chosen_location = customer_locations[0]

            if chosen_location is not None:
                if not location_id:
                    location_id = getattr(chosen_location, "id", None)

                location_name = (
                    getattr(chosen_location, "name", None)
                    or getattr(chosen_location, "label", None)
                    or getattr(chosen_location, "estate", None)
                    or getattr(chosen_location, "address", None)
                )

    return {
        "id": getattr(subscription, "id", None),
        "customer_id": getattr(subscription, "customer_id", None),
        "customer_name": _display_name(customer),
        "account_number": getattr(customer, "account_number", None) if customer is not None else None,
        "package_id": getattr(subscription, "package_id", None) if hasattr(subscription, "package_id") else None,
        "package_name": package_name,
        "location_id": location_id,
        "location_name": location_name,
        "status": getattr(subscription, "status", None) if hasattr(subscription, "status") else None,
        "service_type": getattr(subscription, "service_type", None) if hasattr(subscription, "service_type") else None,
        "is_active": getattr(subscription, "is_active", None) if hasattr(subscription, "is_active") else None,
        "starts_at": _iso(getattr(subscription, "starts_at", None)) if hasattr(subscription, "starts_at") else None,
        "ends_at": _iso(getattr(subscription, "ends_at", None)) if hasattr(subscription, "ends_at") else None,
        "started_at": _iso(getattr(subscription, "started_at", None)) if hasattr(subscription, "started_at") else None,
        "expires_at": _iso(getattr(subscription, "expires_at", None)) if hasattr(subscription, "expires_at") else None,
        "next_due_date": _iso(getattr(subscription, "next_due_date", None)) if hasattr(subscription, "next_due_date") else None,
        "created_at": _iso(getattr(subscription, "created_at", None)),
        "updated_at": _iso(getattr(subscription, "updated_at", None)),
    }

def _serialize_transaction(tx: Transaction) -> dict[str, Any]:
    customer = getattr(tx, "customer", None)
    package = getattr(tx, "package", None)

    package_name = None
    if package is not None:
        package_name = getattr(package, "name", None) or getattr(package, "code", None)

    result_code = getattr(tx, "result_code", None)
    tx_type = "manual" if (result_code or "").upper() == "MANUAL" else "mpesa"

    return {
        "id": getattr(tx, "id", None),
        "customer_id": getattr(tx, "customer_id", None),
        "customer_name": _display_name(customer),
        "package_id": getattr(tx, "package_id", None),
        "package_name": package_name,
        "amount": getattr(tx, "amount", None),
        "status": getattr(tx, "status", None),
        "type": tx_type,
        "checkout_request_id": getattr(tx, "checkout_request_id", None),
        "merchant_request_id": getattr(tx, "merchant_request_id", None),
        "mpesa_receipt": getattr(tx, "mpesa_receipt", None),
        "result_code": result_code,
        "result_desc": getattr(tx, "result_desc", None),
        "created_at": _iso(getattr(tx, "created_at", None)),
    }


# =========================================================
# Customer service-state helpers
# =========================================================

def _subscriptions_for_customer_query(customer_id: int):
    query = Subscription.query.filter(Subscription.customer_id == customer_id)

    if hasattr(Subscription, "created_at"):
        return query.order_by(Subscription.created_at.desc())

    return query.order_by(Subscription.id.desc())


def _set_customer_service_state(
    customer: Customer,
    activate: bool,
    reason: str | None = None,
) -> list[Subscription]:
    now = _now_utc()

    if hasattr(customer, "is_active"):
        customer.is_active = activate

    if hasattr(customer, "updated_at"):
        customer.updated_at = now

    subscriptions = _subscriptions_for_customer_query(customer.id).all()

    for sub in subscriptions:
        if hasattr(sub, "is_active"):
            sub.is_active = activate

        if hasattr(sub, "status"):
            current_status = (getattr(sub, "status", None) or "").strip().lower()

            if activate:
                if current_status in {"", "inactive", "suspended", "active"}:
                    sub.status = "active"
            else:
                if current_status not in {"cancelled"}:
                    sub.status = "suspended"

        if hasattr(sub, "updated_at"):
            sub.updated_at = now

        if not activate and hasattr(sub, "suspended_at"):
            sub.suspended_at = now

        if activate and hasattr(sub, "reconnected_at"):
            sub.reconnected_at = now

        if reason:
            if not activate and hasattr(sub, "suspension_reason"):
                sub.suspension_reason = reason
            if activate and hasattr(sub, "reconnection_note"):
                sub.reconnection_note = reason

    return subscriptions


def _sync_customer_to_mikrotik_later(customer: Customer, activate: bool):
    """
    Future integration point.

    Planned later:
    - PPPoE: disable/enable secret
    - Hotspot: disable/enable user
    - Disconnect active sessions immediately on suspend
    """
    pass


def _customer_detail_payload(customer: Customer) -> dict[str, Any]:
    subscriptions = []
    if hasattr(customer, "subscriptions"):
        try:
            subscriptions = [
                _serialize_subscription(item)
                for item in (customer.subscriptions or [])
            ]
        except Exception:
            subscriptions = []

    tickets = []
    if hasattr(customer, "tickets"):
        try:
            tickets = [
                _serialize_customer_ticket(item)
                for item in (customer.tickets or [])
            ]
        except Exception:
            tickets = []

    locations = []
    for rel_name in ("locations", "customer_locations"):
        if hasattr(customer, rel_name):
            try:
                rel_items = getattr(customer, rel_name) or []
                locations = [
                    _serialize_customer_location(item)
                    for item in rel_items
                ]
                break
            except Exception:
                locations = []

    return {
        "customer": _serialize_customer(customer),
        "subscriptions": subscriptions,
        "tickets": tickets,
        "locations": locations,
    }


# =========================================================
# Auth / dashboard
# =========================================================

@api_admin_bp.get("/api/admin/auth/me")
@admin_api_required
def admin_auth_me():
    return jsonify(
        {
            "ok": True,
            "user": _current_user_payload(),
        }
    )


@api_admin_bp.get("/api/admin/dashboard/summary")
@admin_api_required
def admin_dashboard_summary():
    data = {
        "total_customers": _safe_count(Customer.query),
        "total_subscriptions": _safe_count(Subscription.query),
        "active_subscriptions": _count_active_subscriptions(),
        "expired_subscriptions": _count_expired_subscriptions(),
        "open_tickets": _count_open_tickets(),
        "public_leads": _count_public_leads(),
        "new_public_leads": _count_unhandled_public_leads(),
    }

    return jsonify({"ok": True, "data": data})


# =========================================================
# Public leads
# =========================================================

@api_admin_bp.get("/api/admin/public-leads")
@admin_api_required
def admin_public_leads():
    page = max(_parse_int(request.args.get("page"), 1), 1)
    per_page = min(max(_parse_int(request.args.get("per_page"), 20), 1), 100)

    kind = (request.args.get("kind") or "").strip().lower()
    q = (request.args.get("q") or "").strip()

    query = PublicLead.query

    if kind and hasattr(PublicLead, "kind"):
        query = query.filter(PublicLead.kind == kind)

    if q:
        filters = []
        if hasattr(PublicLead, "name"):
            filters.append(PublicLead.name.ilike(f"%{q}%"))
        if hasattr(PublicLead, "phone"):
            filters.append(PublicLead.phone.ilike(f"%{q}%"))
        if hasattr(PublicLead, "estate"):
            filters.append(PublicLead.estate.ilike(f"%{q}%"))
        if hasattr(PublicLead, "message"):
            filters.append(PublicLead.message.ilike(f"%{q}%"))

        if filters:
            query = query.filter(or_(*filters))

    if hasattr(PublicLead, "created_at"):
        query = query.order_by(PublicLead.created_at.desc())
    else:
        query = query.order_by(PublicLead.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "ok": True,
            "data": [_serialize_public_lead(item) for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


# =========================================================
# Tickets
# =========================================================

@api_admin_bp.get("/api/admin/tickets")
@admin_api_required
def admin_tickets():
    page = max(_parse_int(request.args.get("page"), 1), 1)
    per_page = min(max(_parse_int(request.args.get("per_page"), 20), 1), 100)

    status = (request.args.get("status") or "").strip().lower()
    priority = (request.args.get("priority") or "").strip().lower()
    q = (request.args.get("q") or "").strip()

    query = Ticket.query

    if status and hasattr(Ticket, "status"):
        query = query.filter(Ticket.status == status)

    if priority and hasattr(Ticket, "priority"):
        query = query.filter(Ticket.priority == priority)

    if q:
        filters = []
        if hasattr(Ticket, "code"):
            filters.append(Ticket.code.ilike(f"%{q}%"))
        if hasattr(Ticket, "subject"):
            filters.append(Ticket.subject.ilike(f"%{q}%"))
        if hasattr(Ticket, "description"):
            filters.append(Ticket.description.ilike(f"%{q}%"))

        try:
            filters.append(Ticket.customer.has(Customer.full_name.ilike(f"%{q}%")))
        except Exception:
            pass

        if filters:
            query = query.filter(or_(*filters))

    if hasattr(Ticket, "opened_at_utc"):
        query = query.order_by(Ticket.opened_at_utc.desc())
    else:
        query = query.order_by(Ticket.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "ok": True,
            "data": [_serialize_ticket(item) for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@api_admin_bp.get("/api/admin/tickets/<int:ticket_id>")
@admin_api_required
def admin_ticket_detail(ticket_id: int):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return _json_error("Ticket not found.", 404)

    updates = []
    if hasattr(ticket, "updates"):
        try:
            updates = [_serialize_ticket_update(item) for item in (ticket.updates or [])]
        except Exception:
            updates = []

    return jsonify(
        {
            "ok": True,
            "data": {
                "ticket": _serialize_ticket(ticket),
                "updates": updates,
            },
        }
    )


# =========================================================
# Customers
# =========================================================

@api_admin_bp.get("/api/admin/customers")
@admin_api_required
def admin_customers():
    page = max(_parse_int(request.args.get("page"), 1), 1)
    per_page = min(max(_parse_int(request.args.get("per_page"), 20), 1), 100)

    q = (request.args.get("q") or "").strip()
    active = (request.args.get("active") or "").strip().lower()

    query = Customer.query

    if active in {"true", "1", "yes"} and hasattr(Customer, "is_active"):
        query = query.filter(Customer.is_active.is_(True))
    elif active in {"false", "0", "no"} and hasattr(Customer, "is_active"):
        query = query.filter(Customer.is_active.is_(False))

    if q:
        filters = []

        if hasattr(Customer, "full_name"):
            filters.append(Customer.full_name.ilike(f"%{q}%"))
        if hasattr(Customer, "first_name"):
            filters.append(Customer.first_name.ilike(f"%{q}%"))
        if hasattr(Customer, "last_name"):
            filters.append(Customer.last_name.ilike(f"%{q}%"))
        if hasattr(Customer, "phone"):
            filters.append(Customer.phone.ilike(f"%{q}%"))
        if hasattr(Customer, "email"):
            filters.append(Customer.email.ilike(f"%{q}%"))
        if hasattr(Customer, "account_number"):
            filters.append(Customer.account_number.ilike(f"%{q}%"))
        if hasattr(Customer, "customer_number"):
            filters.append(Customer.customer_number.ilike(f"%{q}%"))

        if filters:
            query = query.filter(or_(*filters))

    if hasattr(Customer, "created_at"):
        query = query.order_by(Customer.created_at.desc())
    else:
        query = query.order_by(Customer.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "ok": True,
            "data": [_serialize_customer(item) for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@api_admin_bp.get("/api/admin/customers/<int:customer_id>")
@admin_api_required
def admin_customer_detail(customer_id: int):
    customer = Customer.query.get(customer_id)
    if not customer:
        return _json_error("Customer not found.", 404)

    return jsonify(
        {
            "ok": True,
            "data": _customer_detail_payload(customer),
        }
    )


@api_admin_bp.post("/api/admin/customers/<int:customer_id>/suspend")
@admin_api_required
def admin_customer_suspend(customer_id: int):
    customer = Customer.query.get(customer_id)
    if not customer:
        return _json_error("Customer not found.", 404)

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "Suspended by admin").strip()

    if hasattr(customer, "is_active") and customer.is_active is False:
        return jsonify(
            {
                "ok": True,
                "message": f"{_display_name(customer) or 'Customer'} is already suspended.",
                "data": _customer_detail_payload(customer),
            }
        )

    _set_customer_service_state(customer, activate=False, reason=reason)

    # Future network enforcement hook
    # _sync_customer_to_mikrotik_later(customer, activate=False)

    db.session.commit()

    customer = Customer.query.get(customer_id)

    return jsonify(
        {
            "ok": True,
            "message": f"{_display_name(customer) or 'Customer'} suspended successfully.",
            "data": _customer_detail_payload(customer),
        }
    )


@api_admin_bp.post("/api/admin/customers/<int:customer_id>/reconnect")
@admin_api_required
def admin_customer_reconnect(customer_id: int):
    customer = Customer.query.get(customer_id)
    if not customer:
        return _json_error("Customer not found.", 404)

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "Reconnected by admin").strip()

    if hasattr(customer, "is_active") and customer.is_active is True:
        return jsonify(
            {
                "ok": True,
                "message": f"{_display_name(customer) or 'Customer'} is already active.",
                "data": _customer_detail_payload(customer),
            }
        )

    _set_customer_service_state(customer, activate=True, reason=reason)

    # Future network enforcement hook
    # _sync_customer_to_mikrotik_later(customer, activate=True)

    db.session.commit()

    customer = Customer.query.get(customer_id)

    return jsonify(
        {
            "ok": True,
            "message": f"{_display_name(customer) or 'Customer'} reconnected successfully.",
            "data": _customer_detail_payload(customer),
        }
    )


# =========================================================
# Subscriptions
# =========================================================

@api_admin_bp.get("/api/admin/subscriptions")
@admin_api_required
def admin_subscriptions():
    page = max(_parse_int(request.args.get("page"), 1), 1)
    per_page = min(max(_parse_int(request.args.get("per_page"), 20), 1), 100)

    status = (request.args.get("status") or "").strip().lower()
    service_type = (request.args.get("service_type") or "").strip().lower()
    q = (request.args.get("q") or "").strip()

    query = Subscription.query

    if status and hasattr(Subscription, "status"):
        query = query.filter(Subscription.status == status)

    if service_type and hasattr(Subscription, "service_type"):
        query = query.filter(Subscription.service_type == service_type)

    if q:
        filters = []

        if hasattr(Subscription, "status"):
            filters.append(Subscription.status.ilike(f"%{q}%"))

        try:
            filters.append(Subscription.customer.has(Customer.full_name.ilike(f"%{q}%")))
        except Exception:
            pass

        try:
            filters.append(Subscription.customer.has(Customer.account_number.ilike(f"%{q}%")))
        except Exception:
            pass

        if hasattr(Subscription, "package"):
            try:
                package_model = Subscription.package.property.mapper.class_
                if hasattr(package_model, "name"):
                    filters.append(
                        Subscription.package.has(package_model.name.ilike(f"%{q}%"))
                    )
            except Exception:
                pass

        if filters:
            query = query.filter(or_(*filters))

    if hasattr(Subscription, "created_at"):
        query = query.order_by(Subscription.created_at.desc())
    else:
        query = query.order_by(Subscription.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "ok": True,
            "data": [_serialize_subscription(item) for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


# =========================================================
# Transactions (real billing ledger)
# =========================================================

@api_admin_bp.get("/api/admin/transactions")
@admin_api_required
def admin_transactions():
    page = max(_parse_int(request.args.get("page"), 1), 1)
    per_page = min(max(_parse_int(request.args.get("per_page"), 20), 1), 100)

    status = (request.args.get("status") or "").strip().lower()
    tx_type = (request.args.get("type") or "").strip().lower()
    q = (request.args.get("q") or "").strip()

    query = Transaction.query

    if status:
        query = query.filter(Transaction.status == status)

    if tx_type == "manual":
        query = query.filter(Transaction.result_code == "MANUAL")
    elif tx_type == "mpesa":
        query = query.filter(
            (Transaction.result_code.is_(None)) | (Transaction.result_code != "MANUAL")
        )

    if q:
        filters = [
            Transaction.mpesa_receipt.ilike(f"%{q}%"),
            Transaction.checkout_request_id.ilike(f"%{q}%"),
            Transaction.merchant_request_id.ilike(f"%{q}%"),
            Transaction.result_desc.ilike(f"%{q}%"),
        ]

        try:
            filters.append(Transaction.customer.has(Customer.full_name.ilike(f"%{q}%")))
        except Exception:
            pass

        query = query.filter(or_(*filters))

    query = query.order_by(Transaction.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "ok": True,
            "data": [_serialize_transaction(item) for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@api_admin_bp.get("/api/admin/transactions/<int:tx_id>")
@admin_api_required
def admin_transaction_detail(tx_id: int):
    tx = Transaction.query.get(tx_id)
    if not tx:
        return _json_error("Transaction not found.", 404)

    return jsonify(
        {
            "ok": True,
            "data": {
                "transaction": _serialize_transaction(tx),
            },
        }
    )