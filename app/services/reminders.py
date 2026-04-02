from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models import Customer, RenewalReminder, Subscription
from app.services.sms import send_sms_message
from app.services.whatsapp import send_whatsapp_template_message

log = logging.getLogger("renewal.reminders")

VALID_PHONE_RE = re.compile(r"^\+?\d{10,15}$")

REMINDER_TYPE_MAP = {
    2: "days_before_2",
    1: "days_before_1",
    0: "on_disconnect",
}

WHATSAPP_TEMPLATE_BY_REMINDER_TYPE = {
    "days_before_2": "renewal_reminder_2_days",
    "days_before_1": "renewal_reminder_1_day",
    "on_disconnect": "service_suspended_notice",
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
    name = (
        getattr(customer, "name", None)
        or getattr(customer, "full_name", None)
        or getattr(customer, "customer_name", None)
        or "Customer"
    )
    return str(name).strip() or "Customer"


def get_customer_phone(customer: Customer) -> str | None:
    return normalize_phone_kenya(getattr(customer, "phone", None))


def get_account_number(customer: Customer) -> str:
    value = getattr(customer, "account_number", None)
    return str(value).strip() if value else "N/A"


def reminder_type_for_days(days_left: int) -> str:
    return REMINDER_TYPE_MAP.get(days_left, "on_disconnect")


def build_renewal_message(
    customer: Customer,
    subscription: Subscription,
    days_left: int,
) -> str:
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


def get_whatsapp_template_name(reminder_type: str) -> str:
    return WHATSAPP_TEMPLATE_BY_REMINDER_TYPE.get(
        reminder_type,
        "renewal_reminder_2_days",
    )


def build_whatsapp_template_components(
    *,
    customer: Customer,
    subscription: Subscription,
    reminder_type: str,
) -> list[dict[str, Any]]:
    """
    Assumes your approved template body placeholders follow this general pattern:
    1. customer name
    2. package/subscription name
    3. expiry date or status text
    4. account number

    Adjust to exactly match your approved Meta templates.
    """
    recipient_name = get_customer_display_name(customer)
    package_name = getattr(getattr(subscription, "package", None), "name", None) or "Package"
    expiry_text = (
        subscription.expires_at.strftime("%d %b %Y")
        if getattr(subscription, "expires_at", None)
        else "soon"
    )
    account_number = get_account_number(customer)

    if reminder_type == "on_disconnect":
        expiry_text = "expired"

    return [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": recipient_name},
                {"type": "text", "text": package_name},
                {"type": "text", "text": expiry_text},
                {"type": "text", "text": account_number},
            ],
        }
    ]


def was_reminder_already_logged(
    subscription_id: int,
    channel: str,
    reminder_type: str,
) -> bool:
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
    is_manual_resend: bool = False,
) -> RenewalReminder:
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
        is_manual_resend=is_manual_resend,
    )
    db.session.add(row)
    return row


def _record_invalid_phone_logs(
    *,
    customer: Customer,
    subscription: Subscription,
    reminder_type: str,
    recipient_name: str,
    message: str,
    include_whatsapp: bool,
) -> None:
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


def _send_sms_and_log(
    *,
    customer: Customer,
    subscription: Subscription,
    reminder_type: str,
    phone: str,
    recipient_name: str,
    message: str,
    is_manual_resend: bool = False,
) -> str:
    if not is_manual_resend and was_reminder_already_logged(subscription.id, "sms", reminder_type):
        return "already_logged"

    result = send_sms_message(
        phone=phone,
        message=message,
        customer_id=customer.id,
        subscription_id=subscription.id,
    )

    create_log(
        customer_id=customer.id,
        subscription_id=subscription.id,
        channel="sms",
        reminder_type=reminder_type,
        phone=phone,
        recipient_name=recipient_name,
        message_body=message,
        status="sent" if result["ok"] else "failed",
        provider=result.get("provider"),
        provider_message_id=result.get("provider_message_id"),
        error_message=result.get("error"),
        sent_at=datetime.now(timezone.utc) if result["ok"] else None,
        is_manual_resend=is_manual_resend,
    )

    return "sent" if result["ok"] else "failed"


def _send_whatsapp_and_log(
    *,
    customer: Customer,
    subscription: Subscription,
    reminder_type: str,
    phone: str,
    recipient_name: str,
    message: str,
    is_manual_resend: bool = False,
) -> str:
    if not is_manual_resend and was_reminder_already_logged(subscription.id, "whatsapp", reminder_type):
        return "already_logged"

    template_name = get_whatsapp_template_name(reminder_type)
    components = build_whatsapp_template_components(
        customer=customer,
        subscription=subscription,
        reminder_type=reminder_type,
    )

    result = send_whatsapp_template_message(
        phone=phone,
        template_name=template_name,
        components=components,
        customer_id=customer.id,
        subscription_id=subscription.id,
    )

    create_log(
        customer_id=customer.id,
        subscription_id=subscription.id,
        channel="whatsapp",
        reminder_type=reminder_type,
        phone=phone,
        recipient_name=recipient_name,
        message_body=message,
        status="sent" if result["ok"] else "failed",
        provider=result.get("provider"),
        provider_message_id=result.get("provider_message_id"),
        error_message=result.get("error"),
        sent_at=datetime.now(timezone.utc) if result["ok"] else None,
        is_manual_resend=is_manual_resend,
    )

    return "sent" if result["ok"] else "failed"


def send_subscription_reminder(
    subscription: Subscription,
    customer: Customer,
    days_left: int,
    *,
    include_whatsapp: bool = True,
    include_sms: bool = True,
    is_manual_resend: bool = False,
) -> dict[str, Any]:
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
            result["sms"] = "skipped" if include_sms else "not_requested"
            result["whatsapp"] = "skipped" if include_whatsapp else "not_requested"
            return result

        if include_sms:
            result["sms"] = _send_sms_and_log(
                customer=customer,
                subscription=subscription,
                reminder_type=reminder_type,
                phone=phone,
                recipient_name=recipient_name,
                message=message,
                is_manual_resend=is_manual_resend,
            )
        else:
            result["sms"] = "not_requested"

        if include_whatsapp:
            result["whatsapp"] = _send_whatsapp_and_log(
                customer=customer,
                subscription=subscription,
                reminder_type=reminder_type,
                phone=phone,
                recipient_name=recipient_name,
                message=message,
                is_manual_resend=is_manual_resend,
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
                include_sms=True,
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
    return send_subscription_reminder(
        subscription=subscription,
        customer=customer,
        days_left=0,
        include_whatsapp=True,
        include_sms=True,
    )


def manual_resend_reminder(
    subscription: Subscription,
    customer: Customer,
    *,
    days_left: int,
    include_sms: bool = True,
    include_whatsapp: bool = True,
) -> dict[str, Any]:
    """
    Manual resend bypasses the unique-cycle dedupe by logging a new row with
    is_manual_resend=True.
    """
    return send_subscription_reminder(
        subscription=subscription,
        customer=customer,
        days_left=days_left,
        include_sms=include_sms,
        include_whatsapp=include_whatsapp,
        is_manual_resend=True,
    )