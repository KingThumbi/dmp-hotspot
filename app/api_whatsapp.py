from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import RenewalReminder

api_whatsapp_bp = Blueprint("api_whatsapp", __name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Verify Meta webhook signature if WHATSAPP_APP_SECRET is configured.
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if not app_secret or not signature_header:
        return False

    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


def _parse_meta_timestamp(value: Any) -> datetime | None:
    """
    Meta webhook timestamps are usually unix epoch seconds as strings.
    """
    if value in (None, "", 0, "0"):
        return None

    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except Exception:
        return None


def _safe_json_dumps(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return "{}"


def _extract_statuses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract WhatsApp status events from webhook payload.

    Expected shape:
    {
      "entry": [
        {
          "changes": [
            {
              "value": {
                "statuses": [...]
              }
            }
          ]
        }
      ]
    }
    """
    results: list[dict[str, Any]] = []

    entries = payload.get("entry") or []
    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            value = change.get("value") or {}
            statuses = value.get("statuses") or []
            for status in statuses:
                if isinstance(status, dict):
                    results.append(status)

    return results


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract inbound message events, if present.
    """
    results: list[dict[str, Any]] = []

    entries = payload.get("entry") or []
    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            for message in messages:
                if isinstance(message, dict):
                    results.append(message)

    return results


def _extract_contacts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract contacts array from payload for optional logging context.
    """
    results: list[dict[str, Any]] = []

    entries = payload.get("entry") or []
    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            value = change.get("value") or {}
            contacts = value.get("contacts") or []
            for contact in contacts:
                if isinstance(contact, dict):
                    results.append(contact)

    return results


def _map_meta_status_to_reminder_status(meta_status: str | None) -> str | None:
    """
    Map Meta delivery states into RenewalReminder.status.
    Existing model comments indicate:
    pending | sent | failed | skipped

    To stay compatible with your current model, delivered/read are stored as sent.
    """
    normalized = (meta_status or "").strip().lower()

    if normalized in {"sent", "delivered", "read"}:
        return "sent"
    if normalized == "failed":
        return "failed"
    return None


def _build_status_error_message(status_event: dict[str, Any]) -> str | None:
    errors = status_event.get("errors") or []
    if not errors:
        return None

    parts: list[str] = []
    for err in errors:
        if not isinstance(err, dict):
            continue

        title = str(err.get("title") or "").strip()
        message = str(err.get("message") or "").strip()
        code = str(err.get("code") or "").strip()

        segment = " | ".join(x for x in [title, message, f"code={code}" if code else ""] if x)
        if segment:
            parts.append(segment)

    if parts:
        return "; ".join(parts)

    return None


def _update_reminder_from_status(status_event: dict[str, Any]) -> bool:
    """
    Update RenewalReminder row using provider_message_id from Meta status callback.

    Returns True if a matching reminder was found and updated.
    """
    provider_message_id = (status_event.get("id") or "").strip()
    if not provider_message_id:
        return False

    reminder = RenewalReminder.query.filter_by(
        provider_message_id=provider_message_id,
        channel="whatsapp",
    ).order_by(RenewalReminder.id.desc()).first()

    if not reminder:
        current_app.logger.warning(
            "WhatsApp webhook status received for unknown provider_message_id=%s payload=%s",
            provider_message_id,
            _safe_json_dumps(status_event),
        )
        return False

    meta_status = (status_event.get("status") or "").strip().lower()
    mapped_status = _map_meta_status_to_reminder_status(meta_status)
    status_timestamp = _parse_meta_timestamp(status_event.get("timestamp"))
    error_message = _build_status_error_message(status_event)

    if mapped_status:
        reminder.status = mapped_status

    if error_message:
        reminder.error_message = error_message
    elif meta_status in {"sent", "delivered", "read"}:
        reminder.error_message = None

    if meta_status in {"sent", "delivered", "read"}:
        if reminder.sent_at is None:
            reminder.sent_at = status_timestamp or _utcnow()

    provider_name = os.getenv("WHATSAPP_PROVIDER", "meta").strip() or "meta"
    reminder.provider = provider_name

    current_app.logger.info(
        "WhatsApp reminder updated: reminder_id=%s provider_message_id=%s meta_status=%s mapped_status=%s",
        reminder.id,
        provider_message_id,
        meta_status,
        mapped_status,
    )
    return True


@api_whatsapp_bp.get("/api/whatsapp/webhook")
def whatsapp_webhook_verify():
    """
    Meta webhook verification endpoint.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()

    if mode == "subscribe" and token == verify_token:
        current_app.logger.info("WhatsApp webhook verification succeeded.")
        return challenge or "", 200

    current_app.logger.warning(
        "WhatsApp webhook verification failed. mode=%s token_present=%s",
        mode,
        bool(token),
    )
    return "Verification failed", 403


@api_whatsapp_bp.post("/api/whatsapp/webhook")
def whatsapp_webhook_receive():
    """
    Receive WhatsApp webhook callbacks from Meta.

    Handles:
    - delivery status updates for outbound messages
    - inbound customer messages (currently log-only)
    """
    raw_body = request.get_data()
    signature = request.headers.get("X-Hub-Signature-256")

    if os.getenv("WHATSAPP_APP_SECRET", "").strip():
        if not _verify_signature(raw_body, signature):
            current_app.logger.warning("WhatsApp webhook rejected due to invalid signature.")
            return jsonify({"ok": False, "error": "Invalid signature"}), 403

    payload = request.get_json(silent=True) or {}

    statuses = _extract_statuses(payload)
    messages = _extract_messages(payload)
    contacts = _extract_contacts(payload)

    current_app.logger.info(
        "WhatsApp webhook received: statuses=%s inbound_messages=%s contacts=%s payload=%s",
        len(statuses),
        len(messages),
        len(contacts),
        _safe_json_dumps(payload),
    )

    updated = 0

    try:
        for status_event in statuses:
            if _update_reminder_from_status(status_event):
                updated += 1

        # For now inbound messages are only logged.
        # Later this can be extended for support/ticketing workflows.
        for msg in messages:
            msg_id = msg.get("id")
            from_number = msg.get("from")
            msg_type = msg.get("type")
            current_app.logger.info(
                "WhatsApp inbound message received: id=%s from=%s type=%s body=%s",
                msg_id,
                from_number,
                msg_type,
                _safe_json_dumps(msg),
            )

        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed processing WhatsApp webhook payload.")
        return jsonify({"ok": False, "error": "Webhook processing failed"}), 500

    return jsonify(
        {
            "ok": True,
            "updated_reminders": updated,
            "status_events": len(statuses),
            "inbound_messages": len(messages),
        }
    ), 200