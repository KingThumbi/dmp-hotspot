# app/scheduler.py
from __future__ import annotations

import logging
from datetime import datetime

from .extensions import db
from .models import Subscription
from .router_agent import pppoe_kick_active_sessions, pppoe_set_disabled

log = logging.getLogger("pppoe.scheduler")


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
        now = datetime.utcnow()  # ✅ UTC-naive to match DB

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
            log.info("PPPoE expiry check: none expired (now_utc=%s, dry_run=%s)", now.isoformat(), dry_run)
            return

        router_enabled = bool(app.config.get("ROUTER_AGENT_ENABLED", False))

        for sub in expired:
            user = (sub.pppoe_username or "").strip()

            log.warning(
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
                        log.error("Router enforcement non-ok | user=%s res1=%s res2=%s", user, res1, res2)
                        # ✅ Do not expire DB if router enforcement didn't succeed
                        continue
                except Exception:
                    log.exception("Router enforcement exception; leaving DB active | user=%s sub_id=%s", user, sub.id)
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
                log.exception("DB commit failed while expiring subscriptions")
