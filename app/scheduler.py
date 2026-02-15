# app/scheduler.py
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from .extensions import db
from .models import MpesaPayment, Subscription
from .router_agent import pppoe_kick_active_sessions, pppoe_set_disabled
from .services.mikrotik_hotspot import disable_hotspot_user, kick_hotspot_active
from .services.mpesa_daraja import load_mpesa_config as load_mpesa_cfg_daraja, stk_query as daraja_stk_query

pppoe_log = logging.getLogger("pppoe.scheduler")
hotspot_log = logging.getLogger("hotspot.scheduler")
all_log = logging.getLogger("expiry.scheduler")
recon_log = logging.getLogger("mpesa.reconcile")


def _utcnow_naive() -> datetime:
    """DB uses UTC-naive datetimes for subscriptions."""
    return datetime.utcnow()


def _now_utc_aware() -> datetime:
    """mpesa_payments uses timestamptz, so use aware UTC."""
    return datetime.now(timezone.utc)


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


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


# -------------------------------------------------------------------
# Expiry enforcement (existing behavior preserved)
# -------------------------------------------------------------------
def enforce_pppoe_expiry(app, dry_run: bool = True) -> None:
    """
    PPPoE expiry enforcement (DB is source of truth).
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


# -------------------------------------------------------------------
# M-Pesa reconciliation layer (NEW)
# -------------------------------------------------------------------
def reconcile_pending_mpesa(app, dry_run: bool = True) -> None:
    """
    Reconcile STK Push payments stuck in 'pending' using STK Query.

    Env toggles:
      - RECONCILE_ENABLED (default false)
      - RECONCILE_PENDING_AFTER_SECONDS (default 180)
      - RECONCILE_TIMEOUT_SECONDS (default 1800)
      - RECONCILE_MAX_ATTEMPTS (default 10)
    """
    if not _bool_env("RECONCILE_ENABLED", False):
        return

    with app.app_context():
        if dry_run:
            recon_log.info("[reconcile] DRY_RUN=true; skipping")
            return

        pending_after = int(os.getenv("RECONCILE_PENDING_AFTER_SECONDS", "180"))
        timeout_after = int(os.getenv("RECONCILE_TIMEOUT_SECONDS", "1800"))
        max_attempts = int(os.getenv("RECONCILE_MAX_ATTEMPTS", "10"))

        now = _now_utc_aware()
        pending_cutoff = now - timedelta(seconds=pending_after)
        timeout_cutoff = now - timedelta(seconds=timeout_after)

        rows = (
            MpesaPayment.query
            .filter(MpesaPayment.status == "pending")
            .filter(MpesaPayment.created_at <= pending_cutoff)
            .filter(MpesaPayment.checkout_request_id.isnot(None))
            .filter(MpesaPayment.reconcile_attempts < max_attempts)
            .order_by(MpesaPayment.created_at.asc())
            .limit(50)
            .all()
        )

        if not rows:
            return

        cfg = load_mpesa_cfg_daraja()

        from app.mpesa import finalize_success_and_activate, mark_payment_failed

        for p in rows:
            try:
                # timeout guard (single write path)
                if p.created_at <= timeout_cutoff:
                    mark_payment_failed(
                        p,
                        status="timeout",
                        result_code=None,
                        result_desc="Timed out waiting for STK completion.",
                        raw={"source": "reconcile", "note": "timeout"},
                        now=now,
                        bump_reconcile=True,
                    )
                    continue

                resp = daraja_stk_query(checkout_request_id=p.checkout_request_id, cfg=cfg)

                rc = resp.get("ResultCode")
                rd = resp.get("ResultDesc") or ""

                # update reconcile tracking (single increment)
                p.reconcile_attempts = int(p.reconcile_attempts or 0) + 1
                p.last_reconcile_at = now
                p.external_updated_at = now
                p.updated_at = now

                try:
                    p.result_code = int(rc) if rc is not None else None
                except Exception:
                    p.result_code = None

                p.result_desc = rd

                # Persist tracking updates once
                db.session.add(p)
                db.session.commit()

                if str(rc) == "0":
                    # Success: STK query usually doesn't provide receipt, but we can still activate.
                    finalize_success_and_activate(
                        p,
                        mpesa_receipt=None,
                        paid_at=now,
                        raw={"source": "stk_query", "resp": resp},
                    )

                    # Optional label after recovering:
                    p.status = "reconciled"
                    p.updated_at = now
                    db.session.add(p)
                    db.session.commit()

                elif str(rc) == "1032":
                    mark_payment_failed(
                        p,
                        status="cancelled",
                        result_code=p.result_code,
                        result_desc=rd or "Cancelled by user.",
                        raw={"source": "stk_query", "resp": resp},
                    )
                else:
                    mark_payment_failed(
                        p,
                        status="failed",
                        result_code=p.result_code,
                        result_desc=rd or "STK query indicates failure.",
                        raw={"source": "stk_query", "resp": resp},
                        now=now,
                        bump_reconcile=True,
                    )

            except Exception:
                recon_log.exception("[reconcile] error payment_id=%s checkout=%s", p.id, p.checkout_request_id)


def retry_activation_failed(app, dry_run: bool = True) -> None:
    """
    Retry activation/router hooks for payments stuck in activation_failed.

    Env toggles:
      - RECONCILE_ENABLED (default false)
      - ACTIVATION_RETRY_MAX (default 5)
    """
    if not _bool_env("RECONCILE_ENABLED", False):
        return

    with app.app_context():
        if dry_run:
            recon_log.info("[activation-retry] DRY_RUN=true; skipping")
            return

        max_retry = int(os.getenv("ACTIVATION_RETRY_MAX", "5"))
        now = _now_utc_aware()

        rows = (
            MpesaPayment.query
            .filter(MpesaPayment.status.in_(["activation_failed", "success"]))
            .filter(MpesaPayment.subscription_id.isnot(None))
            .filter(MpesaPayment.activation_attempts < max_retry)
            .order_by(MpesaPayment.updated_at.asc())
            .limit(50)
            .all()
        )

        if not rows:
            return

        from app.mpesa import _activate_subscription_and_router

        for p in rows:
            try:
                p.activation_attempts += 1
                p.last_activation_at = now
                p.updated_at = now
                db.session.add(p)
                db.session.commit()

                _activate_subscription_and_router(p)

                p.status = "reconciled"
                p.activation_error = None
                p.updated_at = now
                db.session.add(p)
                db.session.commit()

            except Exception as e:
                p.status = "activation_failed"
                p.activation_error = str(e)
                p.updated_at = now
                db.session.add(p)
                db.session.commit()
                recon_log.exception("[activation-retry] failed payment_id=%s", p.id)
