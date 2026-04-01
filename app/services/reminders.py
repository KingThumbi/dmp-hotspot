from __future__ import annotations

import logging
import os
import re
import requests
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models import Customer, RenewalReminder, Subscription

log = logging.getLogger("renewal.reminders")

VALID_PHONE_RE = re.compile(r"^\+?\d{10,15}$")

REMINDER_TYPE_MAP = {
    2: "days_before_2",
    1: "days_before_1",
    0: "on_disconnect",
}


def normalize_phone_kenya(phone: str | None) -> str | None:
    """
    Normalize common Kenyan phone formats into E.164 (+254XXXXXXXXX).

    Supported examples:
    - 0712345678 -> +254712345678
    - 0112345678 -> +254112345678
    - 254712345678 -> +254712345678
    - +254712345678 -> +254712345678
    """
    if not phone:
        return None

    raw = re.sub(r"\s+", "", phone.strip())

    if raw.startswith("07") and len(raw) == 10:
        return f"+254{raw[1:]}"
    if raw.startswith("01") and len(raw) == 10:
        return f"+254{raw[1:]}"
    if raw.startswith("254") and len(raw) == 12:
        return f"+{raw}"
    if raw.startswith("+254") and len(raw) == 13:
        return raw

    if VALID_PHONE_RE.fullmatch(raw):
        return raw

    return None


def get_customer_display_name(customer: Customer) -> str:
    """Return the best available customer display name."""
    name = (
        getattr(customer, "name", None)
        or getattr(customer, "full_name", None)
        or getattr(customer, "customer_name", None)
        or "Customer"
    )
    return str(name).strip() or "Customer"


def get_customer_phone(customer: Customer) -> str | None:
    """Return the customer's normalized phone number."""
    return normalize_phone_kenya(getattr(customer, "phone", None))


def get_account_number(customer: Customer) -> str:
    """Return a safe display account number."""
    value = getattr(customer, "account_number", None)
    return str(value).strip() if value else "N/A"


def reminder_type_for_days(days_left: int) -> str:
    """Map days-left to the canonical reminder type."""
    return REMINDER_TYPE_MAP.get(days_left, "on_disconnect")


def build_renewal_message(
    customer: Customer,
    subscription: Subscription,
    days_left: int,
) -> str:
    """Build the reminder message body."""
    name = get_customer_display_name(customer)
    account_number = get_account_number(customer)
    expiry = (
        subscription.expires_at.strftime("%d %b %Y")
        if getattr(subscription, "expires_at", None)
        else "soon"
    )

    if days_left == 2:
        tail = (
            f"will expire in 2 days ({expiry}). Kindly renew early to avoid "
            "service interruption."
        )
    elif days_left == 1:
        tail = (
            f"will expire tomorrow ({expiry}). Kindly renew to avoid "
            "disconnection."
        )
    else:
        tail = (
            "has expired and your service has been disconnected. Kindly renew "
            "to restore your connection."
        )

    return (
        f"Hello {name}, your Dmpolin Connect internet subscription for account "
        f"{account_number} {tail} Thank you."
    )


def was_reminder_already_logged(
    subscription_id: int,
    channel: str,
    reminder_type: str,
) -> bool:
    """Return True if this reminder cycle has already been logged."""
    return (
        RenewalReminder.query.filter_by(
            subscription_id=subscription_id,
            channel=channel,
            reminder_type=reminder_type,
        ).first()
        is not None
    )


def create_log(
    *,
    customer_id: int,
    subscription_id: int,
    channel: str,
    reminder_type: str,
    phone: str | None,
    recipient_name: str | None,
    message_body: str,
    status: str,
    provider: str | None = None,
    provider_message_id: str | None = None,
    error_message: str | None = None,
    sent_at: datetime | None = None,
) -> RenewalReminder:
    """Create a reminder log row without committing."""
    row = RenewalReminder(
        customer_id=customer_id,
        subscription_id=subscription_id,
        channel=channel,
        reminder_type=reminder_type,
        phone=phone,
        recipient_name=recipient_name,
        message_body=message_body,
        status=status,
        provider=provider,
        provider_message_id=provider_message_id,
        error_message=error_message,
        sent_at=sent_at,
    )
    db.session.add(row)
    return row


def send_sms(phone: str, message: str) -> tuple[bool, str | None, str | None]:
    """
    Send SMS using the configured provider.

    Returns:
        (success, provider_message_id, error_message)
    """
    sms_enabled = os.getenv("SMS_REMINDERS_ENABLED", "false").lower() == "true"
    if not sms_enabled:
        return False, None, "SMS reminders disabled"

    # TODO: replace with real provider integration
    _ = (phone, message)
    return True, "mock-sms-id", None


def send_whatsapp(phone: str, message: str) -> tuple[bool, str | None, str | None]:
    """
    Send WhatsApp via Meta WhatsApp Cloud API.

    Returns:
        (success, provider_message_id, error_message)
    """
    wa_enabled = os.getenv("WHATSAPP_REMINDERS_ENABLED", "false").lower() == "true"
    if not wa_enabled:
        return False, None, "WhatsApp reminders disabled"

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    template_name = os.getenv("WHATSAPP_TEMPLATE_NAME", "").strip()
    language_code = os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en").strip()

    if not access_token:
        return False, None, "Missing WHATSAPP_ACCESS_TOKEN"
    if not phone_number_id:
        return False, None, "Missing WHATSAPP_PHONE_NUMBER_ID"
    if not template_name:
        return False, None, "Missing WHATSAPP_TEMPLATE_NAME"

    # Cloud API expects recipient phone without the leading plus.
    to_number = phone.lstrip("+")

    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # For proactive reminders, send a template message.
    # Start simple: one body parameter containing the rendered reminder text.
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": message[:1024],
                        }
                    ],
                }
            ],
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        data = resp.json()

        if 200 <= resp.status_code < 300:
            message_id = None
            messages = data.get("messages") or []
            if messages:
                message_id = messages[0].get("id")
            return True, message_id, None

        error_obj = data.get("error") or {}
        error_message = (
            error_obj.get("message")
            or f"WhatsApp API error ({resp.status_code})"
        )
        return False, None, error_message

    except Exception as exc:
        return False, None, str(exc)

def _record_invalid_phone_logs(
    *,
    customer: Customer,
    subscription: Subscription,
    reminder_type: str,
    recipient_name: str,
    message: str,
    include_whatsapp: bool,
) -> None:
    """Log skipped reminder attempts when the phone number is missing or invalid."""
    error = "Missing or invalid phone number"

    if not was_reminder_already_logged(subscription.id, "sms", reminder_type):
        create_log(
            customer_id=customer.id,
            subscription_id=subscription.id,
            channel="sms",
            reminder_type=reminder_type,
            phone=None,
            recipient_name=recipient_name,
            message_body=message,
            status="skipped",
            error_message=error,
        )

    if include_whatsapp and not was_reminder_already_logged(
        subscription.id,
        "whatsapp",
        reminder_type,
    ):
        create_log(
            customer_id=customer.id,
            subscription_id=subscription.id,
            channel="whatsapp",
            reminder_type=reminder_type,
            phone=None,
            recipient_name=recipient_name,
            message_body=message,
            status="skipped",
            error_message=error,
        )


def _send_and_log_channel(
    *,
    customer: Customer,
    subscription: Subscription,
    channel: str,
    reminder_type: str,
    phone: str,
    recipient_name: str,
    message: str,
) -> str:
    """
    Send on a single channel and create the corresponding log row.

    Returns one of:
    - sent
    - failed
    - already_logged
    """
    if was_reminder_already_logged(subscription.id, channel, reminder_type):
        return "already_logged"

    provider_env = "SMS_PROVIDER" if channel == "sms" else "WHATSAPP_PROVIDER"
    provider_name = os.getenv(provider_env, "none")

    if channel == "sms":
        ok, provider_message_id, error = send_sms(phone, message)
    else:
        ok, provider_message_id, error = send_whatsapp(phone, message)

    create_log(
        customer_id=customer.id,
        subscription_id=subscription.id,
        channel=channel,
        reminder_type=reminder_type,
        phone=phone,
        recipient_name=recipient_name,
        message_body=message,
        status="sent" if ok else "failed",
        provider=provider_name,
        provider_message_id=provider_message_id,
        error_message=error,
        sent_at=datetime.now(timezone.utc) if ok else None,
    )

    return "sent" if ok else "failed"


def send_subscription_reminder(
    subscription: Subscription,
    customer: Customer,
    days_left: int,
    *,
    include_whatsapp: bool = True,
) -> dict[str, Any]:
    """
    Send and log a reminder for a single subscription/customer pair.
    """
    reminder_type = reminder_type_for_days(days_left)
    phone = get_customer_phone(customer)
    recipient_name = get_customer_display_name(customer)
    message = build_renewal_message(customer, subscription, days_left)

    result: dict[str, Any] = {
        "subscription_id": subscription.id,
        "customer_id": customer.id,
        "days_left": days_left,
        "reminder_type": reminder_type,
        "phone": phone,
        "sms": None,
        "whatsapp": None,
    }

    try:
        if not phone:
            _record_invalid_phone_logs(
                customer=customer,
                subscription=subscription,
                reminder_type=reminder_type,
                recipient_name=recipient_name,
                message=message,
                include_whatsapp=include_whatsapp,
            )
            db.session.commit()
            result["sms"] = "skipped"
            result["whatsapp"] = "skipped" if include_whatsapp else "not_requested"
            return result

        result["sms"] = _send_and_log_channel(
            customer=customer,
            subscription=subscription,
            channel="sms",
            reminder_type=reminder_type,
            phone=phone,
            recipient_name=recipient_name,
            message=message,
        )

        if include_whatsapp:
            result["whatsapp"] = _send_and_log_channel(
                customer=customer,
                subscription=subscription,
                channel="whatsapp",
                reminder_type=reminder_type,
                phone=phone,
                recipient_name=recipient_name,
                message=message,
            )
        else:
            result["whatsapp"] = "not_requested"

        db.session.commit()
        return result

    except Exception:
        db.session.rollback()
        log.exception(
            "Failed sending renewal reminder for subscription_id=%s customer_id=%s",
            getattr(subscription, "id", None),
            getattr(customer, "id", None),
        )
        raise


def get_subscriptions_due_for_reminder(
    days_left: int,
) -> list[tuple[Subscription, Customer]]:
    """
    Return subscriptions due for scheduled pre-expiry reminders.

    Supported days_left values:
    - 2
    - 1
    """
    now = datetime.now(timezone.utc)
    target_date = (now + timedelta(days=days_left)).date()

    return (
        db.session.query(Subscription, Customer)
        .join(Customer, Customer.id == Subscription.customer_id)
        .filter(Subscription.expires_at.isnot(None))
        .filter(func.date(Subscription.expires_at) == target_date)
        .filter(Subscription.status.in_(["active", "pending_disconnect"]))
        .all()
    )


def send_due_renewal_reminders(days_left: int = 2) -> dict[str, int]:
    """
    Scheduled pre-expiry reminder runner.

    Only supports:
    - 2 days before
    - 1 day before
    """
    if days_left not in (1, 2):
        raise ValueError(
            "send_due_renewal_reminders only supports days_left of 1 or 2"
        )

    rows = get_subscriptions_due_for_reminder(days_left=days_left)

    sent = 0
    failed = 0
    skipped = 0

    for subscription, customer in rows:
        try:
            result = send_subscription_reminder(
                subscription=subscription,
                customer=customer,
                days_left=days_left,
                include_whatsapp=True,
            )

            for channel in ("sms", "whatsapp"):
                state = result.get(channel)
                if state == "sent":
                    sent += 1
                elif state == "failed":
                    failed += 1
                elif state in {"skipped", "already_logged", "not_requested"}:
                    skipped += 1

        except Exception as exc:
            failed += 1
            log.exception(
                "Renewal reminder failed for subscription_id=%s customer_id=%s: %s",
                getattr(subscription, "id", None),
                getattr(customer, "id", None),
                exc,
            )

    summary = {
        "days_left": days_left,
        "subscriptions_total": len(rows),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
    }

    log.info(
        "Renewal reminders run complete: days_left=%s total=%s sent=%s failed=%s skipped=%s",
        summary["days_left"],
        summary["subscriptions_total"],
        summary["sent"],
        summary["failed"],
        summary["skipped"],
    )

    return summary


def send_disconnect_reminder(
    subscription: Subscription,
    customer: Customer,
) -> dict[str, Any]:
    """
    Event-driven reminder sent after actual expiry/disconnection.
    """
    return send_subscription_reminder(
        subscription=subscription,
        customer=customer,
        days_left=0,
        include_whatsapp=True,
    )