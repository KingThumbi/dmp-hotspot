from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import RouterAction, Subscription

log = logging.getLogger(__name__)

_enqueue_metrics: dict[str, Any] = {
    "attempts": 0,
    "created": 0,
    "duplicate_action_key_hits": 0,
    "failures": 0,
    "failures_by_action_type": {},
}


def _increment_metric(name: str, *, action_type: str | None = None) -> None:
    try:
        _enqueue_metrics[name] = int(_enqueue_metrics.get(name, 0)) + 1
        if name == "failures" and action_type:
            by_action = _enqueue_metrics.setdefault("failures_by_action_type", {})
            by_action[action_type] = int(by_action.get(action_type, 0)) + 1
    except Exception:
        pass


def get_enqueue_metrics() -> dict[str, Any]:
    by_action = dict(_enqueue_metrics.get("failures_by_action_type", {}))
    return {
        "attempts": int(_enqueue_metrics.get("attempts", 0)),
        "created": int(_enqueue_metrics.get("created", 0)),
        "duplicate_action_key_hits": int(_enqueue_metrics.get("duplicate_action_key_hits", 0)),
        "failures": int(_enqueue_metrics.get("failures", 0)),
        "failures_by_action_type": by_action,
    }


def _iso(value: Any) -> str | None:
    try:
        return value.isoformat() if value is not None else None
    except Exception:
        return None


def _subscription_identity(sub: Subscription | None) -> str | None:
    if sub is None:
        return None
    service_type = (getattr(sub, "service_type", "") or "").strip().lower()
    if service_type == "pppoe":
        return (getattr(sub, "pppoe_username", None) or "").strip() or None
    return (getattr(sub, "hotspot_username", None) or "").strip() or None


def build_action_key(
    *,
    action_type: str,
    subscription_id: int | None = None,
    identity: str | None = None,
    reason: str | None = None,
    correlation_id: str | None = None,
) -> str:
    """
    Stable idempotency key for observe-only queue rows.

    Callers should pass a domain correlation_id for payment/manual/scheduler events.
    The hash keeps the DB index compact even when correlation text grows.
    """
    parts = [
        (action_type or "").strip().lower(),
        str(subscription_id or ""),
        (identity or "").strip().lower(),
        (reason or "").strip().lower(),
        (correlation_id or "").strip().lower(),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    prefix = (action_type or "router_action").strip().lower().replace(".", "_")[:40]
    return f"{prefix}:{digest}"


def _payload_for_subscription(
    *,
    subscription: Subscription | None,
    action_type: str,
    reason: str | None,
    extra_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action_type": action_type,
        "reason": reason,
        "observe_only": True,
        "direct_execution_preserved": True,
        "worker_enabled": False,
    }

    if subscription is not None:
        package = getattr(subscription, "package", None)
        payload.update(
            {
                "subscription_id": getattr(subscription, "id", None),
                "customer_id": getattr(subscription, "customer_id", None),
                "package_id": getattr(subscription, "package_id", None),
                "service_type": getattr(subscription, "service_type", None),
                "identity": _subscription_identity(subscription),
                "profile_name": getattr(package, "mikrotik_profile", None),
                "status": getattr(subscription, "status", None),
                "starts_at": _iso(getattr(subscription, "starts_at", None)),
                "expires_at": _iso(getattr(subscription, "expires_at", None)),
            }
        )

    if extra_payload:
        payload.update(extra_payload)

    return payload


def enqueue_router_action(
    *,
    action_type: str,
    subscription: Subscription | None = None,
    subscription_id: int | None = None,
    customer_id: int | None = None,
    package_id: int | None = None,
    service_type: str | None = None,
    identity: str | None = None,
    profile_name: str | None = None,
    reason: str | None = None,
    created_by: str | None = None,
    created_by_admin_id: int | None = None,
    correlation_id: str | None = None,
    payload: dict[str, Any] | None = None,
    priority: int = 100,
    max_attempts: int = 5,
    next_run_at: datetime | None = None,
    commit: bool = True,
) -> tuple[RouterAction | None, bool]:
    """
    Enqueue an observe-only router action.

    Returns (row, created). Queue failures are intentionally not swallowed here so
    tests can assert behavior; production callers should use safe_enqueue_router_action.
    """
    _increment_metric("attempts")

    if subscription is not None:
        subscription_id = subscription_id or getattr(subscription, "id", None)
        customer_id = customer_id or getattr(subscription, "customer_id", None)
        package_id = package_id or getattr(subscription, "package_id", None)
        service_type = service_type or getattr(subscription, "service_type", None)
        identity = identity or _subscription_identity(subscription)
        package = getattr(subscription, "package", None)
        profile_name = profile_name or getattr(package, "mikrotik_profile", None)

    action_key = build_action_key(
        action_type=action_type,
        subscription_id=subscription_id,
        identity=identity,
        reason=reason,
        correlation_id=correlation_id,
    )

    existing = RouterAction.query.filter_by(action_key=action_key).first()
    if existing:
        _increment_metric("duplicate_action_key_hits")
        log.info(
            "router_action_enqueue_duplicate action_key=%s action_type=%s status=%s sub_id=%s customer_id=%s identity=%s created_by=%s correlation_id=%s",
            action_key,
            action_type,
            existing.status,
            subscription_id,
            customer_id,
            identity,
            created_by,
            correlation_id,
        )
        return existing, False

    row = RouterAction(
        action_key=action_key,
        status="queued",
        action_type=action_type,
        service_type=(service_type or None),
        subscription_id=subscription_id,
        customer_id=customer_id,
        package_id=package_id,
        identity=(identity or None),
        profile_name=(profile_name or None),
        priority=int(priority),
        payload_json=json.dumps(
            _payload_for_subscription(
                subscription=subscription,
                action_type=action_type,
                reason=reason,
                extra_payload=payload,
            ),
            sort_keys=True,
            default=str,
        ),
        attempt_count=0,
        max_attempts=int(max_attempts),
        next_run_at=next_run_at,
        created_by=created_by,
        created_by_admin_id=created_by_admin_id,
        correlation_id=correlation_id,
    )

    db.session.add(row)

    if not commit:
        log.info(
            "router_action_enqueue_staged action_key=%s action_type=%s sub_id=%s customer_id=%s service_type=%s identity=%s created_by=%s correlation_id=%s observe_only=true",
            action_key,
            action_type,
            subscription_id,
            customer_id,
            service_type,
            identity,
            created_by,
            correlation_id,
        )
        return row, True

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = RouterAction.query.filter_by(action_key=action_key).first()
        if existing:
            _increment_metric("duplicate_action_key_hits")
            return existing, False
        raise

    _increment_metric("created")
    log.info(
        "router_action_enqueue_created action_key=%s action_type=%s sub_id=%s customer_id=%s package_id=%s service_type=%s identity=%s created_by=%s correlation_id=%s priority=%s observe_only=true",
        action_key,
        action_type,
        subscription_id,
        customer_id,
        package_id,
        service_type,
        identity,
        created_by,
        correlation_id,
        priority,
    )
    return row, True


def safe_enqueue_router_action(**kwargs: Any) -> RouterAction | None:
    """
    Best-effort enqueue wrapper for production lifecycle hooks.

    Observe-only queue writes must never interrupt the current authoritative DB
    state update or the existing direct router command.
    """
    # TODO(router-queue-worker): In a later phase, a worker will execute queued
    # actions after direct router calls have been retired behind a feature flag.
    try:
        row, _created = enqueue_router_action(**kwargs)
        return row
    except Exception:
        _increment_metric("failures", action_type=kwargs.get("action_type"))
        try:
            db.session.rollback()
        except Exception:
            pass
        log.exception(
            "router_action_enqueue_failed action_type=%s subscription_id=%s customer_id=%s identity=%s created_by=%s correlation_id=%s observe_only=true",
            kwargs.get("action_type"),
            kwargs.get("subscription_id") or getattr(kwargs.get("subscription"), "id", None),
            kwargs.get("customer_id") or getattr(kwargs.get("subscription"), "customer_id", None),
            kwargs.get("identity"),
            kwargs.get("created_by"),
            kwargs.get("correlation_id"),
        )
        return None
