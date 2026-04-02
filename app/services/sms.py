from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("notifications.sms")


def send_sms_message(
    *,
    phone: str,
    message: str,
    customer_id: int | None = None,
    subscription_id: int | None = None,
) -> dict[str, Any]:
    """
    SMS transport service.

    Returns:
    {
        "ok": bool,
        "provider": str,
        "provider_message_id": str | None,
        "error": str | None,
    }

    Replace the mock section with your real SMS provider integration.
    """
    _ = (customer_id, subscription_id)

    sms_enabled = os.getenv("SMS_REMINDERS_ENABLED", "false").strip().lower() == "true"
    provider = os.getenv("SMS_PROVIDER", "mock").strip() or "mock"

    if not sms_enabled:
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": "SMS reminders disabled",
        }

    try:
        if provider == "mock":
            log.info("Mock SMS send to %s: %s", phone, message)
            return {
                "ok": True,
                "provider": provider,
                "provider_message_id": "mock-sms-id",
                "error": None,
            }

        # ------------------------------------------------------
        # Plug your real SMS provider here
        # Example shape only:
        #
        # api_key = os.getenv("SMS_API_KEY", "").strip()
        # sender_id = os.getenv("SMS_SENDER_ID", "").strip()
        # ...
        # requests.post(...)
        # ------------------------------------------------------

        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": f"Unsupported SMS provider: {provider}",
        }

    except Exception as exc:
        log.exception("SMS send failed for phone=%s", phone)
        return {
            "ok": False,
            "provider": provider,
            "provider_message_id": None,
            "error": str(exc),
        }