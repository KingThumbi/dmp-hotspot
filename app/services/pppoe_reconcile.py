# app/services/pppoe_reconcile.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app

from app.models import Subscription
from app.services.router_actions import disconnect_subscription, reconnect_subscription


def _utcnow_naive() -> datetime:
    """Project convention: DB stores UTC-naive datetimes."""
    return datetime.utcnow()


def _log(msg: str) -> None:
    try:
        current_app.logger.info(msg)
    except Exception:
        print(f"[pppoe_reconcile] {datetime.utcnow().isoformat()}Z {msg}")


def _service_type(sub: Subscription) -> str:
    return (getattr(sub, "service_type", "") or "").strip().lower()


def _identity(sub: Subscription) -> str:
    svc = _service_type(sub)
    if svc == "pppoe":
        return (getattr(sub, "pppoe_username", None) or "").strip()
    if svc == "hotspot":
        return (getattr(sub, "hotspot_username", None) or "").strip()
    return ""


def _should_be_active(sub: Subscription, now: datetime) -> bool:
    status = (getattr(sub, "status", "") or "").strip().lower()
    expires_at = getattr(sub, "expires_at", None)

    return (
        status == "active"
        and expires_at is not None
        and expires_at > now
    )


def _normalize_action_result(
    *,
    sub: Subscription,
    identity: str,
    should_be_active: bool,
    dry_run: bool,
    result: dict[str, Any],
) -> dict[str, Any]:
    ok = bool(result.get("ok", False))
    message = result.get("message")
    meta = result.get("meta")
    skipped = bool(result.get("skipped", False))

    if skipped:
        status = "skipped"
    elif ok:
        if dry_run:
            status = "planned_enable" if should_be_active else "planned_disable"
        else:
            status = "applied_enable" if should_be_active else "applied_disable"
    else:
        status = "failed"

    return {
        "sub_id": getattr(sub, "id", None),
        "customer_id": getattr(sub, "customer_id", None),
        "svc": _service_type(sub),
        "identity": identity,
        "db_status": (getattr(sub, "status", None) or ""),
        "expires_at": getattr(sub, "expires_at", None).isoformat() if getattr(sub, "expires_at", None) else None,
        "should_be_active": should_be_active,
        "result": status,
        "ok": ok,
        "message": message,
        "meta": meta,
    }


def reconcile_subscription_router_state(
    *,
    dry_run: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Self-heal router state from DB truth.

    Rules:
    - active + unexpired subscriptions should be reconnected/enabled
    - expired/inactive subscriptions should be disconnected/disabled

    Enforcement path:
    - PPPoE -> relay-backed router_actions
    - Hotspot -> hotspot router_actions

    Notes:
    - This function is DB-truth driven.
    - In dry-run mode, actions are reported as planned_*.
    - In apply mode, actions are reported as applied_*.
    """
    now = _utcnow_naive()
    limit = max(int(limit or 0), 0)

    rows = (
        Subscription.query
        .filter(Subscription.service_type.in_(["pppoe", "hotspot"]))
        .order_by(Subscription.id.asc())
        .limit(limit)
        .all()
    )

    checked = 0
    planned = 0
    applied = 0
    skipped = 0
    failed = 0
    details: list[dict[str, Any]] = []

    for sub in rows:
        checked += 1

        svc = _service_type(sub)
        identity = _identity(sub)

        if not identity:
            item = {
                "sub_id": getattr(sub, "id", None),
                "customer_id": getattr(sub, "customer_id", None),
                "svc": svc,
                "identity": "",
                "db_status": (getattr(sub, "status", None) or ""),
                "expires_at": getattr(sub, "expires_at", None).isoformat() if getattr(sub, "expires_at", None) else None,
                "should_be_active": False,
                "result": "skipped",
                "ok": False,
                "message": "Missing service identity",
                "meta": None,
            }
            details.append(item)
            skipped += 1

            _log(
                f"reconcile skipped sub_id={getattr(sub, 'id', None)} "
                f"svc={svc} reason=missing_identity"
            )
            continue

        should_be_active = _should_be_active(sub, now)

        try:
            if should_be_active:
                raw_result = reconnect_subscription(
                    sub,
                    reason="router_reconcile_active",
                    dry_run=dry_run,
                )
            else:
                raw_result = disconnect_subscription(
                    sub,
                    reason="router_reconcile_expired",
                    dry_run=dry_run,
                )

            item = _normalize_action_result(
                sub=sub,
                identity=identity,
                should_be_active=should_be_active,
                dry_run=dry_run,
                result=raw_result if isinstance(raw_result, dict) else {
                    "ok": False,
                    "message": f"Unexpected result type: {type(raw_result).__name__}",
                    "meta": {"raw_result": str(raw_result)},
                },
            )
            details.append(item)

            result_code = item["result"]
            if result_code == "skipped":
                skipped += 1
            elif result_code.startswith("planned_"):
                planned += 1
            elif result_code.startswith("applied_"):
                applied += 1
            else:
                failed += 1

            _log(
                f"reconcile sub_id={item['sub_id']} svc={svc} identity={identity} "
                f"should_be_active={should_be_active} dry_run={dry_run} "
                f"result={result_code} ok={item['ok']}"
            )

        except Exception as e:
            failed += 1
            item = {
                "sub_id": getattr(sub, "id", None),
                "customer_id": getattr(sub, "customer_id", None),
                "svc": svc,
                "identity": identity,
                "db_status": (getattr(sub, "status", None) or ""),
                "expires_at": getattr(sub, "expires_at", None).isoformat() if getattr(sub, "expires_at", None) else None,
                "should_be_active": should_be_active,
                "result": "failed",
                "ok": False,
                "message": str(e),
                "meta": None,
            }
            details.append(item)

            current_app.logger.exception(
                "Router reconcile failed sub_id=%s svc=%s identity=%s",
                getattr(sub, "id", None),
                svc,
                identity,
            )

    return {
        "ok": failed == 0,
        "dry_run": dry_run,
        "checked": checked,
        "planned": planned,
        "applied": applied,
        "skipped": skipped,
        "failures": failed,
        "details": details,
    }