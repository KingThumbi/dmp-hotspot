from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from .extensions import db
from .models import PublicLead
from .services.notify import notify_admin_new_lead

api_public_bp = Blueprint("api_public", __name__)


@api_public_bp.post("/api/public/leads/coverage")
def public_lead_coverage():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    estate = (data.get("estate") or "").strip()
    message = (data.get("message") or "").strip()
    source = (data.get("source") or "website").strip()

    if not name or not phone:
        return jsonify({"ok": False, "error": "Name and phone are required."}), 400

    created_at = datetime.now(timezone.utc)

    lead = PublicLead(
        kind="coverage",
        name=name,
        phone=phone,
        estate=estate or None,
        message=message or None,
        source=source,
        created_at=created_at,
        handled=False,
    )

    db.session.add(lead)
    db.session.commit()

    try:
        notify_admin_new_lead(
            {
                "kind": lead.kind,
                "name": lead.name,
                "phone": lead.phone,
                "estate": lead.estate,
                "message": lead.message,
                "source": lead.source,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            }
        )
    except Exception:
        # best-effort only
        pass

    return jsonify({"ok": True, "message": "Coverage request received."}), 201


@api_public_bp.post("/api/public/contact")
def public_contact():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()
    source = (data.get("source") or "website").strip()

    if not name or not phone or not message:
        return jsonify({"ok": False, "error": "Name, phone, and message are required."}), 400

    created_at = datetime.now(timezone.utc)

    lead = PublicLead(
        kind="contact",
        name=name,
        phone=phone,
        email=email or None,
        estate=subject or None,
        message=message,
        source=source,
        created_at=created_at,
        handled=False,
    )

    db.session.add(lead)
    db.session.commit()

    try:
        notify_admin_new_lead(
            {
                "kind": lead.kind,
                "name": lead.name,
                "phone": lead.phone,
                "email": lead.email,
                "subject": subject or None,
                "message": lead.message,
                "source": lead.source,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            }
        )
    except Exception:
        pass

    return jsonify({"ok": True, "message": "Message received."}), 201