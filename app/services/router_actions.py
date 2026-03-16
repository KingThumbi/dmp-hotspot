from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from flask import current_app

from app.services.mikrotik_hotspot import (
    disable_hotspot_user,
    ensure_hotspot_user,
    kick_hotspot_active,
)
from app.services.mikrotik_relay import (
    RelayError,
    disable_pppoe,
    enable_pppoe,
)


def _log(message: str) -> None:
    try:
        current_app.logger.info(message)
    except Exception:
        print(f"[router_actions] {datetime.now(timezone.utc).isoformat()} {message}")


def _subscription_meta(subscription) -> tuple[str, Any, Any]:
    svc = (getattr(subscription, "service_type", "") or "").strip().lower()
    sub_id = getattr(subscription, "id", None)
    customer_id = getattr(subscription, "customer_id", None)
    return svc, sub_id, customer_id


def _pppoe_username(subscription) -> str:
    return (getattr(subscription, "pppoe_username", "") or "").strip()


def _hotspot_username(subscription) -> str:
    return (getattr(subscription, "hotspot_username", "") or "").strip()


def disconnect_subscription(
    subscription,
    reason: str = "unpaid",
    dry_run: bool = True,
) -> Dict[str, Any]:
    svc, sub_id, customer_id = _subscription_meta(subscription)

    _log(
        f"DISCONNECT sub_id={sub_id} customer_id={customer_id} "
        f"svc={svc} reason={reason} dry_run={dry_run}"
    )

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    if svc == "pppoe":
        username = _pppoe_username(subscription)
        if not username:
            return {"ok": False, "message": "Missing pppoe_username"}

        try:
            relay_result = disable_pppoe(username, disconnect=True)
            result = {
                "ok": True,
                "message": "PPPoE disabled via relay",
                "meta": {"relay": relay_result},
            }
            _log(
                f"DISCONNECT OK sub_id={sub_id} customer_id={customer_id} "
                f"svc={svc} username={username} result={result}"
            )
            return result
        except RelayError as exc:
            current_app.logger.exception(
                "PPPoE relay disable failed sub_id=%s username=%s",
                sub_id,
                username,
            )
            return {"ok": False, "message": f"PPPoE relay disable failed: {exc}"}

    if svc == "hotspot":
        if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
            return {
                "ok": False,
                "skipped": True,
                "message": "Router agent disabled (ROUTER_AGENT_ENABLED=false)",
            }

        username = _hotspot_username(subscription)
        if not username:
            return {"ok": False, "message": "Missing hotspot_username"}

        try:
            disable_hotspot_user(current_app, username)
            removed = kick_hotspot_active(current_app, username)
            result = {
                "ok": True,
                "message": "Hotspot disabled + kicked",
                "meta": {"removed": removed},
            }
            _log(
                f"DISCONNECT OK sub_id={sub_id} customer_id={customer_id} "
                f"svc={svc} username={username} result={result}"
            )
            return result
        except Exception as exc:
            current_app.logger.exception(
                "Hotspot disconnect failed sub_id=%s username=%s",
                sub_id,
                username,
            )
            return {"ok": False, "message": f"Hotspot disconnect failed: {exc}"}

    return {"ok": False, "message": f"Unknown service_type: {svc}"}


def reconnect_subscription(
    subscription,
    reason: str = "payment_received",
    dry_run: bool = True,
) -> Dict[str, Any]:
    svc, sub_id, customer_id = _subscription_meta(subscription)

    _log(
        f"RECONNECT sub_id={sub_id} customer_id={customer_id} "
        f"svc={svc} reason={reason} dry_run={dry_run}"
    )

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    if svc == "pppoe":
        username = _pppoe_username(subscription)
        if not username:
            return {"ok": False, "message": "Missing pppoe_username"}

        try:
            relay_result = enable_pppoe(username, disconnect=True)
            result = {
                "ok": True,
                "message": "PPPoE enabled via relay",
                "meta": {"relay": relay_result},
            }
            _log(
                f"RECONNECT OK sub_id={sub_id} customer_id={customer_id} "
                f"svc={svc} username={username} result={result}"
            )
            return result
        except RelayError as exc:
            current_app.logger.exception(
                "PPPoE relay enable failed sub_id=%s username=%s",
                sub_id,
                username,
            )
            return {"ok": False, "message": f"PPPoE relay enable failed: {exc}"}

    if svc == "hotspot":
        if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
            return {
                "ok": False,
                "skipped": True,
                "message": "Router agent disabled (ROUTER_AGENT_ENABLED=false)",
            }

        username = _hotspot_username(subscription)
        if not username:
            return {"ok": False, "message": "Missing hotspot_username"}

        try:
            profile = subscription.package.mikrotik_profile
            expires_at = subscription.expires_at
            max_devices = subscription.package.max_devices

            ensure_hotspot_user(
                current_app,
                username=username,
                profile=profile,
                expires_at=expires_at,
                comment_extra=f"max_devices={max_devices} reason={reason}",
            )
            removed = kick_hotspot_active(current_app, username)

            result = {
                "ok": True,
                "message": "Hotspot enabled + kicked",
                "meta": {"removed": removed},
            }
            _log(
                f"RECONNECT OK sub_id={sub_id} customer_id={customer_id} "
                f"svc={svc} username={username} result={result}"
            )
            return result
        except Exception as exc:
            current_app.logger.exception(
                "Hotspot reconnect failed sub_id=%s username=%s",
                sub_id,
                username,
            )
            return {"ok": False, "message": f"Hotspot reconnect failed: {exc}"}

    return {"ok": False, "message": f"Unknown service_type: {svc}"}


def disconnect_pppoe_only(username: str, dry_run: bool = True) -> Dict[str, Any]:
    username = (username or "").strip()
    if not username:
        return {"ok": False, "message": "Missing username"}

    _log(f"DISCONNECT_PPPOE_ONLY username={username} dry_run={dry_run}")

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    try:
        relay_result = disable_pppoe(username, disconnect=True)
        result = {
            "ok": True,
            "message": "PPPoE disabled via relay",
            "meta": {"relay": relay_result},
        }
        _log(f"DISCONNECT_PPPOE_ONLY OK username={username} result={result}")
        return result
    except RelayError as exc:
        current_app.logger.exception(
            "disconnect_pppoe_only failed username=%s",
            username,
        )
        return {"ok": False, "message": str(exc)}


def reconnect_pppoe_only(username: str, dry_run: bool = True) -> Dict[str, Any]:
    username = (username or "").strip()
    if not username:
        return {"ok": False, "message": "Missing username"}

    _log(f"RECONNECT_PPPOE_ONLY username={username} dry_run={dry_run}")

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    try:
        relay_result = enable_pppoe(username, disconnect=True)
        result = {
            "ok": True,
            "message": "PPPoE enabled via relay",
            "meta": {"relay": relay_result},
        }
        _log(f"RECONNECT_PPPOE_ONLY OK username={username} result={result}")
        return result
    except RelayError as exc:
        current_app.logger.exception(
            "reconnect_pppoe_only failed username=%s",
            username,
        )
        return {"ok": False, "message": str(exc)}