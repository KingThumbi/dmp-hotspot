# app/scheduler.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Tuple

from .extensions import db
from .models import Subscription
from .router_agent import pppoe_kick_active_sessions, pppoe_set_disabled
from .services.mikrotik_hotspot import disable_hotspot_user, kick_hotspot_active

pppoe_log = logging.getLogger("pppoe.scheduler")
hotspot_log = logging.getLogger("hotspot.scheduler")
all_log = logging.getLogger("expiry.scheduler")


def _utcnow_naive() -> datetime:
    """DB uses UTC-naive datetimes."""
    return datetime.utcnow()


def _okish(res) -> bool:
    """
    Normalize "ok" status from different return shapes.

    Supported:
    - object with .ok attribute
    - dict with {"ok": ...}
    - None/unknown -> assume OK unless explicitly false
    """
    if res is None:
        return True
    if isinstance(res, dict):
        return bool(res.get("ok", True))
    return bool(getattr(res, "ok", True))


def enforce_pppoe_expiry(app, dry_run: bool = True) -> None:
    """
    PPPoE expiry enforcement (DB is source of truth).

    Flow:
      1) Find expired active PPPoE subs
      2) Mark DB expired (commit)
      3) Best-effort router enforcement (disable + kick)
         - If router fails, we LOG and rely on next run to retry.
    """
    with app.app_context():
        now = _utcnow_naive()

        expired = (
            Subscription.query
            .filter(
                Subscription.service_type == "pppoe",
                Subscription.status == "active",
                Subscription.expires_at.isnot(None),
                Subscription.expires_at <= now,
                Subscription.pppoe_username.isnot(None),
            )
            .all()
        )

        if not expired:
            pppoe_log.info("PPPoE expiry check: none expired (now_utc=%s, dry_run=%s)", now.isoformat(), dry_run)
            return

        router_enabled = bool(app.config.get("ROUTER_AGENT_ENABLED", False))

        # --- Step 1: DB-first (authoritative) ---
        to_enforce: List[Tuple[int, str]] = []
        for sub in expired:
            user = (sub.pppoe_username or "").strip()
            pppoe_log.warning(
                "PPPoE expiry detected | sub_id=%s user=%s expires_at=%s dry_run=%s router_enabled=%s",
                sub.id, user or "-", sub.expires_at, dry_run, router_enabled
            )

            if dry_run:
                continue

            sub.status = "expired"
            db.session.add(sub)

            if user:
                to_enforce.append((sub.id, user))

        if not dry_run:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                pppoe_log.exception("DB commit failed while expiring PPPoE subscriptions")
                return

        # --- Step 2: Router follows DB (best-effort) ---
        if dry_run or not router_enabled:
            return

        for sub_id, user in to_enforce:
            try:
                res1 = pppoe_set_disabled(app, user, disabled=True)
                res2 = pppoe_kick_active_sessions(app, user)

                if not _okish(res1) or not _okish(res2):
                    pppoe_log.error("PPPoE router enforcement non-ok | sub_id=%s user=%s res1=%s res2=%s",
                                    sub_id, user, res1, res2)
            except Exception:
                pppoe_log.exception("PPPoE router enforcement exception | sub_id=%s user=%s", sub_id, user)


def enforce_hotspot_expiry(app, dry_run: bool = True) -> None:
    """
    Hotspot expiry enforcement (DB is source of truth).

    Flow:
      1) Find expired active hotspot subs
      2) Mark DB expired (commit)
      3) Best-effort router enforcement (disable + kick)
         - If router fails, we LOG and rely on next run to retry.
    """
    with app.app_context():
        now = _utcnow_naive()

        expired = (
            Subscription.query
            .filter(
                Subscription.service_type == "hotspot",
                Subscription.status == "active",
                Subscription.expires_at.isnot(None),
                Subscription.expires_at <= now,
                Subscription.hotspot_username.isnot(None),
            )
            .all()
        )

        if not expired:
            hotspot_log.info("Hotspot expiry check: none expired (now_utc=%s, dry_run=%s)", now.isoformat(), dry_run)
            return

        router_enabled = bool(app.config.get("ROUTER_AGENT_ENABLED", False))

        # --- Step 1: DB-first (authoritative) ---
        to_enforce: List[Tuple[int, str]] = []
        for sub in expired:
            user = (sub.hotspot_username or "").strip()
            hotspot_log.warning(
                "Hotspot expiry detected | sub_id=%s user=%s expires_at=%s dry_run=%s router_enabled=%s",
                sub.id, user or "-", sub.expires_at, dry_run, router_enabled
            )

            if dry_run:
                continue

            sub.status = "expired"
            db.session.add(sub)

            if user:
                to_enforce.append((sub.id, user))

        if not dry_run:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                hotspot_log.exception("DB commit failed while expiring Hotspot subscriptions")
                return

        # --- Step 2: Router follows DB (best-effort) ---
        if dry_run or not router_enabled:
            return

        for sub_id, user in to_enforce:
            try:
                res1 = disable_hotspot_user(app, user)
                res2 = kick_hotspot_active(app, user)

                if not _okish(res1) or not _okish(res2):
                    hotspot_log.error("Hotspot router enforcement non-ok | sub_id=%s user=%s res1=%s res2=%s",
                                      sub_id, user, res1, res2)
            except Exception:
                hotspot_log.exception("Hotspot router enforcement exception | sub_id=%s user=%s", sub_id, user)


def enforce_all_expiry(app, dry_run: bool = True) -> None:
    """Run both PPPoE + Hotspot enforcement in one call."""
    all_log.info("Running enforce_all_expiry(dry_run=%s)", dry_run)
    enforce_pppoe_expiry(app, dry_run=dry_run)
    enforce_hotspot_expiry(app, dry_run=dry_run)
