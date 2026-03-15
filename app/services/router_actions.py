from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from flask import current_app

from app.router_agent import agent_enable
from app.services.mikrotik_hotspot import (
    disable_hotspot_user,
    ensure_hotspot_user,
    kick_hotspot_active,
)
from app.services.mikrotik_relay import (
    RelayError,
    disable_pppoe,
    enable_pppoe,
    disconnect_pppoe,
)


def _log(msg: str) -> None:
    try:
        current_app.logger.info(msg)
    except Exception:
        print(f"[router_actions] {datetime.utcnow().isoformat()}Z {msg}")


def disconnect_subscription(subscription, reason: str = "unpaid", dry_run: bool = True) -> Dict[str, Any]:
    svc = (getattr(subscription, "service_type", "") or "").strip().lower()
    sub_id = getattr(subscription, "id", None)
    customer_id = getattr(subscription, "customer_id", None)

    _log(
        f"DISCONNECT sub_id={sub_id} customer_id={customer_id} "
        f"svc={svc} reason={reason} dry_run={dry_run}"
    )

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    if svc == "pppoe":
        user = (getattr(subscription, "pppoe_username", "") or "").strip()
        if not user:
            return {"ok": False, "message": "Missing pppoe_username"}

        try:
            relay_result = disable_pppoe(user, disconnect=True)
            return {
                "ok": True,
                "message": "PPPoE disabled via relay",
                "meta": {"relay": relay_result},
            }
        except RelayError as e:
            current_app.logger.exception(
                "PPPoE relay disable failed sub_id=%s username=%s", sub_id, user
            )
            return {
                "ok": False,
                "message": f"PPPoE relay disable failed: {e}",
            }

    if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
        return {
            "ok": False,
            "skipped": True,
            "message": "Router agent disabled (ROUTER_AGENT_ENABLED=false)",
        }

    if svc == "hotspot":
        user = (getattr(subscription, "hotspot_username", "") or "").strip()
        if not user:
            return {"ok": False, "message": "Missing hotspot_username"}

        try:
            disable_hotspot_user(current_app, user)
            removed = kick_hotspot_active(current_app, user)
            return {
                "ok": True,
                "message": "Hotspot disabled + kicked",
                "meta": {"removed": removed},
            }
        except Exception as e:
            current_app.logger.exception(
                "Hotspot disconnect failed sub_id=%s username=%s", sub_id, user
            )
            return {"ok": False, "message": f"Hotspot disconnect failed: {e}"}

    return {"ok": False, "message": f"Unknown service_type: {svc}"}


def reconnect_subscription(subscription, reason: str = "payment_received", dry_run: bool = True) -> Dict[str, Any]:
    svc = (getattr(subscription, "service_type", "") or "").strip().lower()
    sub_id = getattr(subscription, "id", None)
    customer_id = getattr(subscription, "customer_id", None)

    _log(
        f"RECONNECT sub_id={sub_id} customer_id={customer_id} "
        f"svc={svc} reason={reason} dry_run={dry_run}"
    )

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    if svc == "pppoe":
        user = (getattr(subscription, "pppoe_username", "") or "").strip()
        if not user:
            return {"ok": False, "message": "Missing pppoe_username"}

        try:
            relay_result = enable_pppoe(user, disconnect=False)
            return {
                "ok": True,
                "message": "PPPoE enabled via relay",
                "meta": {"relay": relay_result},
            }
        except RelayError as e:
            current_app.logger.exception(
                "PPPoE relay enable failed sub_id=%s username=%s", sub_id, user
            )
            return {
                "ok": False,
                "message": f"PPPoE relay enable failed: {e}",
            }

    if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
        return {
            "ok": False,
            "skipped": True,
            "message": "Router agent disabled (ROUTER_AGENT_ENABLED=false)",
        }

    if svc == "hotspot":
        user = (getattr(subscription, "hotspot_username", "") or "").strip()
        if not user:
            return {"ok": False, "message": "Missing hotspot_username"}

        try:
            profile = subscription.package.mikrotik_profile
            exp = subscription.expires_at
            max_devices = subscription.package.max_devices

            ensure_hotspot_user(
                current_app,
                username=user,
                profile=profile,
                expires_at=exp,
                comment_extra=f"max_devices={max_devices} reason={reason}",
            )
            removed = kick_hotspot_active(current_app, user)

            return {
                "ok": True,
                "message": "Hotspot enabled + kicked",
                "meta": {"removed": removed},
            }
        except Exception as e:
            current_app.logger.exception(
                "Hotspot reconnect failed sub_id=%s username=%s", sub_id, user
            )
            return {"ok": False, "message": f"Hotspot reconnect failed: {e}"}

    return {"ok": False, "message": f"Unknown service_type: {svc}"}


def disconnect_pppoe_only(username: str, dry_run: bool = True) -> Dict[str, Any]:
    username = (username or "").strip()
    if not username:
        return {"ok": False, "message": "Missing username"}

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    try:
        relay_result = disable_pppoe(username, disconnect=True)
        return {"ok": True, "message": "PPPoE disabled via relay", "meta": {"relay": relay_result}}
    except RelayError as e:
        current_app.logger.exception("disconnect_pppoe_only failed username=%s", username)
        return {"ok": False, "message": str(e)}


def reconnect_pppoe_only(username: str, dry_run: bool = True) -> Dict[str, Any]:
    username = (username or "").strip()
    if not username:
        return {"ok": False, "message": "Missing username"}

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    try:
        relay_result = enable_pppoe(username, disconnect=False)
        return {"ok": True, "message": "PPPoE enabled via relay", "meta": {"relay": relay_result}}
    except RelayError as e:
        current_app.logger.exception("reconnect_pppoe_only failed username=%s", username)
        return {"ok": False, "message": str(e)}
