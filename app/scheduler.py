# app/scheduler.py
from __future__ import annotations

import logging
from datetime import datetime

from .extensions import db
from .models import Subscription
from .router_agent import pppoe_kick_active_sessions, pppoe_set_disabled
from .services.mikrotik_hotspot import disable_hotspot_user, kick_hotspot_active

pppoe_log = logging.getLogger("pppoe.scheduler")
hotspot_log = logging.getLogger("hotspot.scheduler")
all_log = logging.getLogger("expiry.scheduler")


def _utcnow_naive() -> datetime:
    """
    DB uses UTC-naive datetimes (as per current PPPoE logic).
    Keep enforcement comparisons consistent with that.
    """
    return datetime.utcnow()


def _okish(res) -> bool:
    """
    Normalize "ok" status from different return shapes.

    Supported:
    - object with .ok attribute (router_agent style)
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
    PPPoE expiry enforcement (Phase C).

    Targets ONLY:
      - service_type='pppoe'
      - status='active'
      - expires_at IS NOT NULL
      - expires_at <= now (UTC-naive)
      - pppoe_username IS NOT NULL

    dry_run=True  -> logs only (safe default)
    dry_run=False -> disable PPPoE + kick sessions (if ROUTER_AGENT_ENABLED), then mark DB expired
    """
    with app.app_context():
        now = _utcnow_naive()  # ✅ UTC-naive to match DB

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

        for sub in expired:
            user = (sub.pppoe_username or "").strip()

            pppoe_log.warning(
                "PPPoE expiry detected | sub_id=%s user=%s expires_at=%s dry_run=%s router_enabled=%s",
                sub.id,
                user or "-",
                sub.expires_at,
                dry_run,
                router_enabled,
            )

            # No username: can only mark expired in DB (no router action possible)
            if not user:
                if not dry_run:
                    sub.status = "expired"
                    db.session.add(sub)
                continue

            if dry_run:
                continue

            # Live enforcement
            if router_enabled:
                try:
                    res1 = pppoe_set_disabled(app, user, disabled=True)
                    res2 = pppoe_kick_active_sessions(app, user)

                    ok1 = getattr(res1, "ok", True)
                    ok2 = getattr(res2, "ok", True)

                    if not ok1 or not ok2:
                        pppoe_log.error("Router enforcement non-ok | user=%s res1=%s res2=%s", user, res1, res2)
                        # ✅ Do not expire DB if router enforcement didn't succeed
                        continue
                except Exception:
                    pppoe_log.exception(
                        "Router enforcement exception; leaving DB active | user=%s sub_id=%s",
                        user,
                        sub.id,
                    )
                    continue

            # If router enforcement succeeded OR router automation is OFF,
            # we still expire in DB (DB is source of truth).
            sub.status = "expired"
            db.session.add(sub)

        if not dry_run:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                pppoe_log.exception("DB commit failed while expiring PPPoE subscriptions")


def enforce_hotspot_expiry(app, dry_run: bool = True) -> None:
    """
    Hotspot expiry enforcement (Phase D).

    Targets ONLY:
      - service_type='hotspot'
      - status='active'
      - expires_at IS NOT NULL
      - expires_at <= now (UTC-naive)
      - hotspot_username IS NOT NULL

    dry_run=True  -> logs only
    dry_run=False -> disable Hotspot user + kick session (if ROUTER_AGENT_ENABLED), then mark DB expired

    Safety rule (mirrors PPPoE):
    - If router automation is enabled AND router enforcement fails/throws,
      we DO NOT mark the DB expired (to avoid mismatched truth/actions).
    - If router automation is OFF, we still expire in DB (DB is source of truth).
    """
    with app.app_context():
        now = _utcnow_naive()  # ✅ UTC-naive to match DB

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

        for sub in expired:
            user = (sub.hotspot_username or "").strip()

            hotspot_log.warning(
                "Hotspot expiry detected | sub_id=%s user=%s expires_at=%s dry_run=%s router_enabled=%s",
                sub.id,
                user or "-",
                sub.expires_at,
                dry_run,
                router_enabled,
            )

            # No username: can only mark expired in DB (no router action possible)
            if not user:
                if not dry_run:
                    sub.status = "expired"
                    db.session.add(sub)
                continue

            if dry_run:
                continue

            # Live enforcement
            if router_enabled:
                try:
                    res1 = disable_hotspot_user(app, user)
                    res2 = kick_hotspot_active(app, user)

                    ok1 = _okish(res1)
                    ok2 = _okish(res2)

                    if not ok1 or not ok2:
                        hotspot_log.error("Router enforcement non-ok | user=%s res1=%s res2=%s", user, res1, res2)
                        # ✅ Do not expire DB if router enforcement didn't succeed
                        continue
                except Exception:
                    hotspot_log.exception(
                        "Router enforcement exception; leaving DB active | user=%s sub_id=%s",
                        user,
                        sub.id,
                    )
                    continue

            # If router enforcement succeeded OR router automation is OFF,
            # we still expire in DB (DB is source of truth).
            sub.status = "expired"
            db.session.add(sub)

        if not dry_run:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                hotspot_log.exception("DB commit failed while expiring Hotspot subscriptions")


def enforce_all_expiry(app, dry_run: bool = True) -> None:
    """
    Run both PPPoE + Hotspot enforcement in one call.
    Recommended: schedule a single job calling this.
    """
    all_log.info("Running enforce_all_expiry(dry_run=%s)", dry_run)
    enforce_pppoe_expiry(app, dry_run=dry_run)
    enforce_hotspot_expiry(app, dry_run=dry_run)
