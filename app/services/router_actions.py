from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from flask import current_app

from app.router_agent import (
    agent_enable,
    pppoe_kick_active_sessions,
    pppoe_set_disabled,
)

from app.services.mikrotik_hotspot import (
    disable_hotspot_user,
    ensure_hotspot_user,
    kick_hotspot_active,
)


def _log(msg: str) -> None:
    try:
        current_app.logger.info(msg)
    except Exception:
        print(f"[router_actions] {datetime.utcnow().isoformat()}Z {msg}")


def disconnect_subscription(subscription, reason: str = "unpaid", dry_run: bool = True) -> Dict[str, Any]:
    svc = (getattr(subscription, "service_type", "") or "").strip().lower()
    _log(
        f"DISCONNECT sub_id={getattr(subscription,'id',None)} "
        f"customer_id={getattr(subscription,'customer_id',None)} svc={svc} reason={reason} dry_run={dry_run}"
    )

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
        return {"ok": False, "skipped": True, "message": "Router agent disabled (ROUTER_AGENT_ENABLED=false)"}

    if svc == "pppoe":
        user = (subscription.pppoe_username or "").strip()
        if not user:
            return {"ok": False, "message": "Missing pppoe_username"}
        res1 = pppoe_set_disabled(current_app, username=user, disabled=True)
        res2 = pppoe_kick_active_sessions(current_app, username=user)
        return {"ok": True, "message": "PPPoE disabled + kicked", "meta": {"disable": res1.meta, "kick": res2.meta}}

    if svc == "hotspot":
        user = (subscription.hotspot_username or "").strip()
        if not user:
            return {"ok": False, "message": "Missing hotspot_username"}
        disable_hotspot_user(current_app, user)
        removed = kick_hotspot_active(current_app, user)
        return {"ok": True, "message": "Hotspot disabled + kicked", "meta": {"removed": removed}}

    return {"ok": False, "message": f"Unknown service_type: {svc}"}


def reconnect_subscription(subscription, reason: str = "payment_received", dry_run: bool = True) -> Dict[str, Any]:
    svc = (getattr(subscription, "service_type", "") or "").strip().lower()
    _log(
        f"RECONNECT sub_id={getattr(subscription,'id',None)} "
        f"customer_id={getattr(subscription,'customer_id',None)} svc={svc} reason={reason} dry_run={dry_run}"
    )

    if dry_run:
        return {"ok": True, "dry_run": True, "message": "DRY RUN"}

    if not current_app.config.get("ROUTER_AGENT_ENABLED", False):
        return {"ok": False, "skipped": True, "message": "Router agent disabled (ROUTER_AGENT_ENABLED=false)"}

    if svc == "pppoe":
        user = (subscription.pppoe_username or "").strip()
        if not user:
            return {"ok": False, "message": "Missing pppoe_username"}
        profile = subscription.package.mikrotik_profile
        agent_enable(current_app, username=user, profile=profile, minutes=0, comment=reason)
        res2 = pppoe_kick_active_sessions(current_app, username=user)
        return {"ok": True, "message": "PPPoE enabled + kicked", "meta": {"kick": res2.meta}}

    if svc == "hotspot":
        user = (subscription.hotspot_username or "").strip()
        if not user:
            return {"ok": False, "message": "Missing hotspot_username"}

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

        return {"ok": True, "message": "Hotspot enabled + kicked", "meta": {"removed": removed}}

    return {"ok": False, "message": f"Unknown service_type: {svc}"}
