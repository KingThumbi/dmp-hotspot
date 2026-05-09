from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.subscription_lifecycle import (
    activate_or_extend_hotspot_subscription,
    activate_or_extend_pppoe_subscription,
    apply_manual_payment_activation,
    apply_pppoe_prorated_upgrade,
    mark_subscription_expired,
    set_customer_service_state,
)


class Stub:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def identity(self) -> str:
        if getattr(self, "service_type", "") == "pppoe":
            return getattr(self, "pppoe_username", "") or ""
        return getattr(self, "hotspot_username", "") or ""


def package(minutes: int, *, package_id: int = 10, code: str = "pkg") -> Stub:
    return Stub(id=package_id, code=code, duration_minutes=minutes)


def tx(tx_id: int = 99) -> Stub:
    return Stub(id=tx_id)


def test_hotspot_activation_sets_status_dates_identity_and_transaction():
    now = datetime(2026, 5, 9, 10, 0, 0)
    customer = Stub(id=1, phone="254712345678")
    sub = Stub(
        id=2,
        customer_id=1,
        customer=customer,
        service_type="hotspot",
        status="pending",
        starts_at=None,
        expires_at=None,
        hotspot_username=None,
        last_tx_id=None,
    )

    activate_or_extend_hotspot_subscription(sub, package(120), tx(7), now=now)

    assert sub.status == "active"
    assert sub.starts_at == now
    assert sub.expires_at == now + timedelta(minutes=120)
    assert sub.hotspot_username == "254712345678"
    assert sub.last_tx_id == 7


def test_hotspot_extension_extends_from_future_expiry_and_keeps_start():
    now = datetime(2026, 5, 9, 10, 0, 0)
    started = now - timedelta(hours=2)
    current_expiry = now + timedelta(minutes=30)
    sub = Stub(
        id=3,
        customer_id=1,
        service_type="hotspot",
        status="active",
        starts_at=started,
        expires_at=current_expiry,
        hotspot_username="254712345678",
        last_tx_id=None,
    )

    activate_or_extend_hotspot_subscription(sub, package(60), tx(8), now=now)

    assert sub.status == "active"
    assert sub.starts_at == started
    assert sub.expires_at == current_expiry + timedelta(minutes=60)
    assert sub.last_tx_id == 8


def test_pppoe_activation_sets_status_dates_and_transaction():
    now = datetime(2026, 5, 9, 10, 0, 0)
    sub = Stub(
        id=4,
        customer_id=2,
        service_type="pppoe",
        status="pending",
        starts_at=None,
        expires_at=None,
        pppoe_username="D001",
        last_tx_id=None,
    )

    activate_or_extend_pppoe_subscription(sub, package(43200, code="pppoe_5m"), tx(9), now=now)

    assert sub.status == "active"
    assert sub.starts_at == now
    assert sub.expires_at == now + timedelta(minutes=43200)
    assert sub.last_tx_id == 9


def test_pppoe_extension_extends_from_future_expiry_and_keeps_start():
    now = datetime(2026, 5, 9, 10, 0, 0)
    started = now - timedelta(days=10)
    current_expiry = now + timedelta(days=5)
    sub = Stub(
        id=5,
        customer_id=2,
        service_type="pppoe",
        status="active",
        starts_at=started,
        expires_at=current_expiry,
        pppoe_username="D002",
        last_tx_id=None,
    )

    activate_or_extend_pppoe_subscription(sub, package(43200, code="pppoe_10m"), tx(10), now=now)

    assert sub.status == "active"
    assert sub.starts_at == started
    assert sub.expires_at == current_expiry + timedelta(minutes=43200)
    assert sub.last_tx_id == 10


def test_expiry_marking_only_changes_subscription_status():
    now = datetime(2026, 5, 9, 10, 0, 0)
    expires_at = now - timedelta(minutes=1)
    sub = Stub(
        id=6,
        customer_id=3,
        service_type="hotspot",
        status="active",
        starts_at=now - timedelta(hours=1),
        expires_at=expires_at,
        hotspot_username="254700000001",
    )

    mark_subscription_expired(sub, now=now)

    assert sub.status == "expired"
    assert sub.expires_at == expires_at


def test_suspend_transition_updates_customer_and_non_cancelled_subscriptions():
    now = datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc)
    customer = Stub(id=7, is_active=True, updated_at=None)
    active = Stub(
        id=8,
        customer_id=7,
        service_type="pppoe",
        status="active",
        is_active=True,
        updated_at=None,
        suspended_at=None,
        suspension_reason=None,
    )
    cancelled = Stub(id=9, customer_id=7, service_type="hotspot", status="cancelled")

    result = set_customer_service_state(
        customer,
        [active, cancelled],
        activate=False,
        reason="nonpayment",
        now=now,
    )

    assert result == [active, cancelled]
    assert customer.is_active is False
    assert customer.updated_at == now
    assert active.status == "suspended"
    assert active.is_active is False
    assert active.updated_at == now
    assert active.suspended_at == now
    assert active.suspension_reason == "nonpayment"
    assert cancelled.status == "cancelled"


def test_reconnect_transition_reactivates_allowed_statuses_and_preserves_cancelled():
    now = datetime(2026, 5, 9, 11, 0, 0, tzinfo=timezone.utc)
    customer = Stub(id=10, is_active=False, updated_at=None)
    suspended = Stub(
        id=11,
        customer_id=10,
        service_type="pppoe",
        status="suspended",
        is_active=False,
        updated_at=None,
        reconnected_at=None,
        reconnection_note=None,
    )
    cancelled = Stub(id=12, customer_id=10, service_type="hotspot", status="cancelled")

    set_customer_service_state(
        customer,
        [suspended, cancelled],
        activate=True,
        reason="paid",
        now=now,
    )

    assert customer.is_active is True
    assert customer.updated_at == now
    assert suspended.status == "active"
    assert suspended.is_active is True
    assert suspended.updated_at == now
    assert suspended.reconnected_at == now
    assert suspended.reconnection_note == "paid"
    assert cancelled.status == "cancelled"


def test_prorated_upgrade_changes_package_and_keeps_existing_expiry():
    now = datetime(2026, 5, 9, 10, 0, 0)
    existing_expiry = now + timedelta(days=12)
    sub = Stub(
        id=13,
        customer_id=11,
        service_type="pppoe",
        status="active",
        starts_at=None,
        expires_at=existing_expiry,
        package_id=20,
        pppoe_username="D003",
        last_tx_id=None,
    )
    new_package = package(43200, package_id=21, code="pppoe_20m")

    apply_pppoe_prorated_upgrade(sub, new_package, tx(14), now=now)

    assert sub.package_id == 21
    assert sub.status == "active"
    assert sub.starts_at == now
    assert sub.expires_at == existing_expiry
    assert sub.last_tx_id == 14


def test_manual_payment_activation_preserves_existing_start_and_extends_from_future_expiry():
    paid_at = datetime(2026, 5, 9, 10, 0, 0)
    started = paid_at - timedelta(days=20)
    current_expiry = paid_at + timedelta(days=3)
    sub = Stub(
        id=14,
        customer_id=12,
        service_type="pppoe",
        status="active",
        starts_at=started,
        expires_at=current_expiry,
        package=package(43200, code="pppoe_5m"),
        updated_at=None,
    )

    apply_manual_payment_activation(sub, paid_at=paid_at)

    assert sub.status == "active"
    assert sub.starts_at == started
    assert sub.expires_at == current_expiry + timedelta(minutes=43200)
    assert sub.updated_at is not None


def test_manual_payment_activation_uses_expiry_override_when_provided():
    paid_at = datetime(2026, 5, 9, 10, 0, 0)
    override = paid_at + timedelta(days=45)
    sub = Stub(
        id=15,
        customer_id=13,
        service_type="hotspot",
        status="pending",
        starts_at=None,
        expires_at=None,
        package=package(60, code="daily"),
    )

    apply_manual_payment_activation(sub, paid_at=paid_at, expires_override=override)

    assert sub.status == "active"
    assert sub.starts_at == paid_at
    assert sub.expires_at == override
