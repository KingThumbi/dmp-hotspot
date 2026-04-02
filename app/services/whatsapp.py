from __future__ import annotations

import logging
import os
from typing import Any

import requests

log = logging.getLogger("notifications.whatsapp")


def _strip_plus(phone: str) -> str:
    return phone.lstrip("+")


def send_whatsapp_template_message(
    *,
    phone: str,
    template_name: str,
    components: list[dict[str, Any]] | None = None,
    language_code: str | None = None,
    customer_id: int | None = None,
    subscription_id: int | None = None,
) -> dict[str, Any]:
    """
    Send a WhatsApp template message via Meta Cloud API.

    Returns:
    {
        "ok": bool,
        "provider": "meta",
        "provider_message_id": str | None,
        "error": str | None,
        "response_json": dict | None,
    }
    """
    _ = (customer_id, subscription_id)

    wa_enabled = os.getenv("WHATSAPP_REMINDERS_ENABLED", "false").strip().lower() == "true"
    provider = os.getenv("WHATSAPP_PROVIDER", "meta").strip() or "meta"

    if not wa_enabled:
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": "WhatsApp reminders disabled",
            "response_json": None,
        }

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    api_version = os.getenv("WHATSAPP_API_VERSION", "v23.0").strip() or "v23.0"
    language = (language_code or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")).strip() or "en"

    if not access_token:
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": "Missing WHATSAPP_ACCESS_TOKEN",
            "response_json": None,
        }

    if not phone_number_id:
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": "Missing WHATSAPP_PHONE_NUMBER_ID",
            "response_json": None,
        }

    if not template_name:
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": "Missing WhatsApp template name",
            "response_json": None,
        }

    to_number = _strip_plus(phone)

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
        },
    }

    if components:
        payload["template"]["components"] = components

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        data = resp.json()

        if 200 <= resp.status_code < 300:
            message_id = None
            messages = data.get("messages") or []
            if messages:
                message_id = messages[0].get("id")

            return {
                "ok": True,
                "provider": provider,
                "provider_message_id": message_id,
                "error": None,
                "response_json": data,
            }

        error_obj = data.get("error") or {}
        error_message = error_obj.get("message") or f"WhatsApp API error ({resp.status_code})"

        log.warning(
            "WhatsApp API error phone=%s template=%s status=%s error=%s",
            phone,
            template_name,
            resp.status_code,
            error_message,
        )

        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": error_message,
            "response_json": data,
        }

    except Exception as exc:
        log.exception("WhatsApp send failed for phone=%s template=%s", phone, template_name)
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": str(exc),
            "response_json": None,
        }