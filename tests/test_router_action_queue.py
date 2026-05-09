from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def queue_app(monkeypatch, tmp_path):
    db_path = tmp_path / "router_action_queue.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("ROUTER_AGENT_ENABLED", "false")
    monkeypatch.setenv("ROUTER_AUTOMATION_ENABLED", "false")

    from app import create_app
    from app.extensions import db
    from app.models import (
        AdminUser,
        Customer,
        MpesaPayment,
        Package,
        RouterAction,
        Subscription,
        Transaction,
    )

    app = create_app()
    app.config.update(
        TESTING=True,
        ROUTER_AGENT_ENABLED=True,
        ROUTER_AUTOMATION_DRY_RUN=True,
    )

    tables = [
        AdminUser.__table__,
        Customer.__table__,
        Package.__table__,
        Transaction.__table__,
        Subscription.__table__,
        MpesaPayment.__table__,
        RouterAction.__table__,
    ]

    with app.app_context():
        db.metadata.create_all(db.engine, tables=tables)
        yield app
        db.session.remove()
        db.metadata.drop_all(db.engine, tables=list(reversed(tables)))


def _create_subscription(
    *,
    service_type: str = "pppoe",
    status: str = "active",
    expires_at: datetime | None = None,
):
    from app.extensions import db
    from app.models import Customer, Package, Subscription

    customer = Customer(phone="254700000001", account_number="DMP001")
    package = Package(
        code=f"{service_type}_basic",
        name=f"{service_type.upper()} Basic",
        duration_minutes=60,
        price_kes=50,
        mikrotik_profile=f"{service_type}-profile",
    )
    sub = Subscription(
        customer=customer,
        package=package,
        service_type=service_type,
        status=status,
        starts_at=datetime.utcnow() - timedelta(minutes=5),
        expires_at=expires_at or datetime.utcnow() + timedelta(hours=1),
        pppoe_username="D001" if service_type == "pppoe" else None,
        hotspot_username="254700000001" if service_type == "hotspot" else None,
    )

    db.session.add_all([customer, package, sub])
    db.session.commit()
    return customer, package, sub


def test_idempotent_enqueue_creates_one_action(queue_app):
    from app.models import RouterAction
    from app.services.router_action_queue import enqueue_router_action

    with queue_app.app_context():
        _customer, _package, sub = _create_subscription()

        first, first_created = enqueue_router_action(
            action_type="subscription.reconnect",
            subscription=sub,
            reason="payment_received",
            correlation_id="payment:1",
        )
        second, second_created = enqueue_router_action(
            action_type="subscription.reconnect",
            subscription=sub,
            reason="payment_received",
            correlation_id="payment:1",
        )

        assert first_created is True
        assert second_created is False
        assert second is not None
        assert first is not None
        assert second.id == first.id
        assert RouterAction.query.count() == 1


def test_duplicate_action_key_returns_existing_action(queue_app):
    from app.extensions import db
    from app.models import RouterAction
    from app.services.router_action_queue import build_action_key, enqueue_router_action

    with queue_app.app_context():
        _customer, _package, sub = _create_subscription(service_type="hotspot")
        action_key = build_action_key(
            action_type="subscription.disconnect",
            subscription_id=sub.id,
            identity=sub.hotspot_username,
            reason="expired",
            correlation_id="expiry:1",
        )
        existing = RouterAction(
            action_key=action_key,
            status="queued",
            action_type="subscription.disconnect",
            service_type="hotspot",
            subscription_id=sub.id,
            customer_id=sub.customer_id,
            package_id=sub.package_id,
            identity=sub.hotspot_username,
        )
        db.session.add(existing)
        db.session.commit()

        row, created = enqueue_router_action(
            action_type="subscription.disconnect",
            subscription=sub,
            reason="expired",
            correlation_id="expiry:1",
        )

        assert created is False
        assert row is not None
        assert row.id == existing.id
        assert RouterAction.query.count() == 1


def test_safe_enqueue_never_breaks_caller_flow(monkeypatch, queue_app):
    from app.services import router_action_queue

    def explode(**_kwargs):
        raise RuntimeError("database unavailable")

    with queue_app.app_context():
        monkeypatch.setattr(router_action_queue, "enqueue_router_action", explode)

        marker = "caller still completes"
        row = router_action_queue.safe_enqueue_router_action(
            action_type="subscription.reconnect",
            subscription_id=123,
            identity="D123",
            reason="payment_received",
        )

        assert row is None
        assert marker == "caller still completes"


def test_payload_result_and_error_fields_serialize_correctly(queue_app):
    from app.extensions import db
    from app.models import RouterAction
    from app.services.router_action_queue import enqueue_router_action

    with queue_app.app_context():
        _customer, _package, sub = _create_subscription()

        row, created = enqueue_router_action(
            action_type="subscription.reconnect",
            subscription=sub,
            reason="payment_received",
            correlation_id="payment:serialize",
            payload={"payment_id": 9, "nested": {"ok": True}},
        )

        assert created is True
        assert row is not None

        row.result_json = json.dumps({"ok": True, "router": "observe-only"})
        row.error_message = "last error sample"
        db.session.commit()

        saved = db.session.get(RouterAction, row.id)
        assert saved is not None
        payload = json.loads(saved.payload_json or "{}")
        result = json.loads(saved.result_json or "{}")

        assert payload["observe_only"] is True
        assert payload["direct_execution_preserved"] is True
        assert payload["payment_id"] == 9
        assert payload["nested"] == {"ok": True}
        assert result == {"ok": True, "router": "observe-only"}
        assert saved.error_message == "last error sample"


def test_lifecycle_payment_path_enqueues_reconnect_without_live_router(monkeypatch, queue_app):
    from app.extensions import db
    from app.models import MpesaPayment, RouterAction
    from app.mpesa import _activate_subscription_and_router
    from app.services import router_actions

    with queue_app.app_context():
        _customer, _package, sub = _create_subscription(status="pending")
        payment = MpesaPayment(
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            phone="254700000001",
            amount=50,
            checkout_request_id="checkout-1",
            mpesa_receipt="RCP001",
            status="success",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        router_calls: list[dict] = []

        def fake_reconnect(subscription, reason, dry_run):
            router_calls.append(
                {"subscription_id": subscription.id, "reason": reason, "dry_run": dry_run}
            )
            return {"ok": True, "observe_only_test": True}

        monkeypatch.setattr(router_actions, "reconnect_subscription", fake_reconnect)

        _activate_subscription_and_router(payment)

        action = RouterAction.query.filter_by(
            action_type="subscription.reconnect",
            created_by="mpesa_payment",
        ).one()
        payload = json.loads(action.payload_json or "{}")

        assert action.subscription_id == sub.id
        assert action.status == "queued"
        assert action.correlation_id == f"mpesa_payment:{payment.id}"
        assert payload["payment_id"] == payment.id
        assert payload["mpesa_receipt"] == "RCP001"
        assert router_calls == [
            {"subscription_id": sub.id, "reason": "payment_received", "dry_run": True}
        ]
        assert db.session.get(MpesaPayment, payment.id).status == "success"


def test_admin_enable_path_enqueues_reconnect_without_live_router(monkeypatch, queue_app):
    from app import admin as admin_module
    from app.models import RouterAction

    class CurrentUserStub:
        id = 77
        is_authenticated = True
        is_active = True

        def has_role(self, *_roles):
            return True

    with queue_app.app_context():
        _customer, _package, sub = _create_subscription(
            service_type="pppoe",
            status="active",
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )

        agent_calls: list[dict] = []

        def fake_agent_enable(app, username, profile, minutes, comment):
            agent_calls.append(
                {
                    "username": username,
                    "profile": profile,
                    "minutes": minutes,
                    "comment": comment,
                }
            )

        monkeypatch.setattr(admin_module, "current_user", CurrentUserStub())
        monkeypatch.setattr(admin_module, "agent_enable", fake_agent_enable)
        monkeypatch.setattr(admin_module, "audit", lambda *_args, **_kwargs: None)

        fn = admin_module.subscription_enable
        while hasattr(fn, "__wrapped__"):
            fn = fn.__wrapped__

        with queue_app.test_request_context(f"/admin/subscriptions/{sub.id}/enable", method="POST"):
            fn(sub.id)

        action = RouterAction.query.filter_by(
            action_type="subscription.reconnect",
            created_by="admin_enable",
        ).one()
        payload = json.loads(action.payload_json or "{}")

        assert action.subscription_id == sub.id
        assert action.created_by_admin_id == 77
        assert action.identity == "D001"
        assert payload["username"] == "D001"
        assert agent_calls == [
            {
                "username": "D001",
                "profile": "pppoe-profile",
                "minutes": 0,
                "comment": "Enabled by admin",
            }
        ]
