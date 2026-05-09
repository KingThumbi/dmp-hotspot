from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any


log = logging.getLogger("subscription.lifecycle")


PPPOE_DEFAULT_DURATION_MINUTES = 30 * 24 * 60


def utcnow_naive() -> datetime:
    """Project convention: subscription timestamps are UTC-naive."""
    return datetime.utcnow()


def _log_action(action: str, *, subscription: Any = None, customer: Any = None, **extra: Any) -> None:
    """
    Structured lifecycle logging.

    Keep this helper defensive so logging never breaks customer access changes.
    """
    try:
        payload = {
            "action": action,
            "subscription_id": getattr(subscription, "id", None) if subscription is not None else None,
            "customer_id": (
                getattr(subscription, "customer_id", None)
                if subscription is not None
                else getattr(customer, "id", None)
            ),
            "service_type": getattr(subscription, "service_type", None) if subscription is not None else None,
            "status": getattr(subscription, "status", None) if subscription is not None else None,
            "identity": subscription.identity() if subscription is not None and hasattr(subscription, "identity") else None,
            **extra,
        }
        log.info("subscription lifecycle action", extra={"lifecycle": payload})
    except Exception:
        log.info("subscription lifecycle action=%s", action)


def _duration_minutes(package: Any, *, fallback_minutes: int) -> int:
    minutes = int(getattr(package, "duration_minutes", 0) or 0)
    return minutes if minutes > 0 else int(fallback_minutes)


def activate_or_extend_hotspot_subscription(
    subscription: Any,
    package: Any,
    transaction: Any,
    *,
    now: datetime | None = None,
) -> None:
    """
    Current hotspot billing rule:
    - active/unexpired subscriptions extend from current expiry
    - otherwise activate from now

    The caller owns db.session.add/commit to preserve existing behavior.
    """
    now = now or utcnow_naive()
    minutes = _duration_minutes(package, fallback_minutes=60)

    try:
        if (getattr(subscription, "service_type", "") or "").lower() == "hotspot":
            if not getattr(subscription, "hotspot_username", None):
                customer = getattr(subscription, "customer", None)
                if customer is not None and getattr(customer, "phone", None):
                    subscription.hotspot_username = customer.phone

        if getattr(subscription, "status", None) == "active" and getattr(subscription, "expires_at", None):
            base = subscription.expires_at if subscription.expires_at > now else now
            subscription.expires_at = base + timedelta(minutes=minutes)
            if not getattr(subscription, "starts_at", None):
                subscription.starts_at = now
        else:
            subscription.status = "active"
            subscription.starts_at = now
            subscription.expires_at = now + timedelta(minutes=minutes)

        subscription.last_tx_id = getattr(transaction, "id", None)

        _log_action(
            "activate_or_extend_hotspot",
            subscription=subscription,
            package_id=getattr(package, "id", None),
            package_code=getattr(package, "code", None),
            transaction_id=getattr(transaction, "id", None),
            expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        )
        # TODO(router-queue): enqueue hotspot enable/update instead of direct router calls.
    except Exception:
        log.exception(
            "Hotspot lifecycle activation failed sub_id=%s tx_id=%s",
            getattr(subscription, "id", None),
            getattr(transaction, "id", None),
        )
        raise


def activate_or_extend_pppoe_subscription(
    subscription: Any,
    package: Any,
    transaction: Any,
    *,
    now: datetime | None = None,
) -> None:
    """
    Current PPPoE renewal rule:
    - early renewal extends from current expiry
    - expired/missing expiry starts from now

    The caller owns db.session.add/commit to preserve existing behavior.
    """
    now = now or utcnow_naive()
    minutes = _duration_minutes(package, fallback_minutes=PPPOE_DEFAULT_DURATION_MINUTES)

    try:
        if getattr(subscription, "expires_at", None) and subscription.expires_at > now:
            subscription.expires_at = subscription.expires_at + timedelta(minutes=minutes)
            subscription.status = "active"
            if not getattr(subscription, "starts_at", None):
                subscription.starts_at = now
        else:
            subscription.status = "active"
            subscription.starts_at = now
            subscription.expires_at = now + timedelta(minutes=minutes)

        subscription.last_tx_id = getattr(transaction, "id", None)

        _log_action(
            "activate_or_extend_pppoe",
            subscription=subscription,
            package_id=getattr(package, "id", None),
            package_code=getattr(package, "code", None),
            transaction_id=getattr(transaction, "id", None),
            expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        )
        # TODO(router-queue): enqueue PPPoE enable/profile-sync instead of direct router calls.
    except Exception:
        log.exception(
            "PPPoE lifecycle activation failed sub_id=%s tx_id=%s",
            getattr(subscription, "id", None),
            getattr(transaction, "id", None),
        )
        raise


def activate_or_extend_current_subscription(
    subscription: Any,
    *,
    now: datetime | None = None,
) -> None:
    """
    Generic activation helper for existing callers that already have
    subscription.package loaded and do not use the legacy Transaction.last_tx_id.
    """
    now = now or utcnow_naive()

    try:
        package = getattr(subscription, "package", None)
        minutes = int(getattr(package, "duration_minutes", 0) or 0)
        if minutes <= 0:
            raise RuntimeError("Package duration_minutes is missing/invalid")

        base = (
            subscription.expires_at
            if getattr(subscription, "expires_at", None) and subscription.expires_at > now
            else now
        )
        subscription.status = "active"
        if not getattr(subscription, "starts_at", None):
            subscription.starts_at = now
        subscription.expires_at = base + timedelta(minutes=minutes)

        _log_action(
            "activate_or_extend_current",
            subscription=subscription,
            package_id=getattr(package, "id", None),
            package_code=getattr(package, "code", None),
            expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        )
        # TODO(router-queue): enqueue service reconnect/profile-sync after commit.
    except Exception:
        log.exception("Generic lifecycle activation failed sub_id=%s", getattr(subscription, "id", None))
        raise


def apply_pppoe_prorated_upgrade(
    subscription: Any,
    package: Any,
    transaction: Any,
    *,
    now: datetime | None = None,
) -> None:
    """
    Current PPPoE upgrade behavior:
    - change package immediately
    - keep existing expiry
    - mark active
    """
    now = now or utcnow_naive()

    try:
        subscription.package_id = getattr(package, "id", None)
        subscription.status = "active"
        subscription.last_tx_id = getattr(transaction, "id", None)
        if not getattr(subscription, "starts_at", None):
            subscription.starts_at = now

        _log_action(
            "apply_pppoe_prorated_upgrade",
            subscription=subscription,
            package_id=getattr(package, "id", None),
            package_code=getattr(package, "code", None),
            transaction_id=getattr(transaction, "id", None),
        )
        # TODO(router-queue): enqueue PPPoE profile update instead of direct router calls.
    except Exception:
        log.exception(
            "PPPoE prorated upgrade failed sub_id=%s tx_id=%s",
            getattr(subscription, "id", None),
            getattr(transaction, "id", None),
        )
        raise


def apply_manual_payment_activation(
    subscription: Any,
    *,
    paid_at: datetime,
    expires_override: datetime | None = None,
) -> None:
    """
    Current manual-payment activation behavior from Flask admin.

    The caller creates the Transaction and assigns last_tx_id after flush.
    """
    try:
        package = getattr(subscription, "package", None)
        minutes = _duration_minutes(package, fallback_minutes=PPPOE_DEFAULT_DURATION_MINUTES)
        base = (
            subscription.expires_at
            if getattr(subscription, "expires_at", None) and subscription.expires_at > paid_at
            else paid_at
        )
        computed_expires = base + timedelta(minutes=minutes)

        subscription.status = "active"
        if not getattr(subscription, "starts_at", None):
            subscription.starts_at = paid_at
        subscription.expires_at = expires_override or computed_expires

        if hasattr(subscription, "updated_at"):
            subscription.updated_at = utcnow_naive()

        _log_action(
            "manual_payment_activation",
            subscription=subscription,
            package_id=getattr(package, "id", None),
            package_code=getattr(package, "code", None),
            paid_at=paid_at.isoformat() if paid_at else None,
            expires_override=expires_override.isoformat() if expires_override else None,
            expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        )
        # TODO(router-queue): enqueue reconnect after the manual payment commit succeeds.
    except Exception:
        log.exception("Manual payment activation failed sub_id=%s", getattr(subscription, "id", None))
        raise


def mark_subscription_expired(
    subscription: Any,
    *,
    reason: str = "expired",
    now: datetime | None = None,
) -> None:
    """Mark a subscription expired without committing; caller preserves commit behavior."""
    now = now or utcnow_naive()
    try:
        subscription.status = "expired"
        _log_action(
            "mark_expired",
            subscription=subscription,
            reason=reason,
            now_utc=now.isoformat(),
            expires_at=(
                subscription.expires_at.isoformat()
                if getattr(subscription, "expires_at", None)
                else None
            ),
        )
        # TODO(router-queue): enqueue disconnect after this DB transition is committed.
    except Exception:
        log.exception("Subscription expiry transition failed sub_id=%s", getattr(subscription, "id", None))
        raise


def set_customer_service_state(
    customer: Any,
    subscriptions: list[Any],
    *,
    activate: bool,
    reason: str | None = None,
    now: datetime | None = None,
) -> list[Any]:
    """
    Current admin customer suspend/reconnect behavior.

    This intentionally mirrors the existing API behavior:
    - suspend sets subscription.status = suspended except cancelled
    - reconnect sets blank/inactive/suspended/active statuses to active
    - optional legacy columns are updated when present
    - caller owns commit and router integration remains a future step
    """
    now = now or datetime.now(timezone.utc)
    action = "customer_reconnect" if activate else "customer_suspend"

    try:
        if hasattr(customer, "is_active"):
            customer.is_active = activate

        if hasattr(customer, "updated_at"):
            customer.updated_at = now

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

            _log_action(action, subscription=sub, reason=reason)

        # TODO(router-queue): enqueue one router action per affected subscription.
        return subscriptions
    except Exception:
        log.exception(
            "Customer lifecycle state change failed customer_id=%s activate=%s",
            getattr(customer, "id", None),
            activate,
        )
        raise
