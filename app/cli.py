# app/cli.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

import click
from flask import current_app
from flask.cli import with_appcontext

from app.models import Subscription
from app.services.router_actions import disconnect_subscription, reconnect_subscription


# ======================================================
# Basic CLI sanity
# ======================================================
@click.command("ping-cli")
def ping_cli():
    """Verify custom CLI commands are registered."""
    click.echo("CLI OK: commands are registered.")


@click.command("sub-disconnect-last")
@with_appcontext
def sub_disconnect_last():
    """DRY-RUN disconnect the most recent subscription."""
    sub = Subscription.query.order_by(Subscription.id.desc()).first()
    if not sub:
        click.echo("No subscriptions found.")
        return
    result = disconnect_subscription(sub, dry_run=True)
    click.echo(str(result))


@click.command("sub-reconnect-last")
@with_appcontext
def sub_reconnect_last():
    """DRY-RUN reconnect the most recent subscription."""
    sub = Subscription.query.order_by(Subscription.id.desc()).first()
    if not sub:
        click.echo("No subscriptions found.")
        return
    result = reconnect_subscription(sub, dry_run=True)
    click.echo(str(result))


# ======================================================
# Router tools
# ======================================================
@click.group()
def router():
    """Router tools (audit/resync)."""


def _active_pppoe_subs():
    """DB-side: active + unexpired PPPoE subs with username."""
    now = datetime.utcnow()  # DB stores UTC naive in this project
    return (
        Subscription.query.filter(
            Subscription.service_type == "pppoe",
            Subscription.status == "active",
            Subscription.expires_at.isnot(None),
            Subscription.expires_at > now,
            Subscription.pppoe_username.isnot(None),
        )
        .order_by(Subscription.id.asc())
        .all()
    )


@router.command("audit-pppoe")
@click.option("--active", "only_active", is_flag=True, help="Audit only active, unexpired PPPoE subs from DB.")
@with_appcontext
def audit_pppoe(only_active: bool):
    """
    Read-only audit: checks if PPPoE secrets exist on MikroTik and whether they are disabled.
    Does NOT modify the router.
    """
    from app.router_agent import _pppoe_pool, pppoe_secret_get  # reuse existing helpers

    subs = _active_pppoe_subs() if only_active else (
        Subscription.query.filter(Subscription.service_type == "pppoe")
        .order_by(Subscription.id.asc())
        .all()
    )

    if not subs:
        click.echo("No PPPoE subscriptions matched.")
        return

    try:
        pool = _pppoe_pool(current_app)
        api = pool.get_api()
    except Exception as e:
        raise click.ClickException(f"Router connection failed: {e}")

    click.echo(f"Auditing {len(subs)} PPPoE subscriptions on router...\n")

    ok = missing = disabled = 0
    for s in subs:
        username = (s.pppoe_username or "").strip()
        if not username:
            click.echo(f"[SKIP] sub_id={s.id} missing pppoe_username")
            continue

        row = pppoe_secret_get(api, username)
        if not row:
            click.echo(f"[MISSING] sub_id={s.id} user={username} expires_at={s.expires_at}")
            missing += 1
            continue

        is_disabled = str(row.get("disabled", "")).lower() in {"yes", "true", "1"}
        if is_disabled:
            click.echo(f"[DISABLED] sub_id={s.id} user={username} expires_at={s.expires_at}")
            disabled += 1
        else:
            click.echo(f"[OK] sub_id={s.id} user={username} expires_at={s.expires_at}")
            ok += 1

    click.echo(f"\nSummary: OK={ok} DISABLED={disabled} MISSING={missing}")


@router.command("resync-pppoe")
@click.option("--active", "only_active", is_flag=True, help="Resync only active, unexpired PPPoE subs from DB.")
@click.option("--limit", type=int, default=25, show_default=True, help="Max number of subs to process.")
@click.option("--apply", "apply_changes", is_flag=True, help="Actually modify router. Default is DRY-RUN.")
@with_appcontext
def resync_pppoe(only_active: bool, limit: int, apply_changes: bool):
    """
    Resync PPPoE router state to match DB for active subs:
      - If secret missing: ensure/create it with correct profile/comment
      - Ensure secret is enabled (disabled=no)
    """
    from app.router_agent import pppoe_secret_ensure, pppoe_set_disabled

    subs = _active_pppoe_subs() if only_active else (
        Subscription.query.filter(Subscription.service_type == "pppoe")
        .order_by(Subscription.id.asc())
        .all()
    )

    subs = subs[: max(limit, 0)]
    if not subs:
        click.echo("No PPPoE subscriptions matched.")
        return

    router_enabled = bool(current_app.config.get("ROUTER_AGENT_ENABLED", False))
    if apply_changes and not router_enabled:
        raise click.ClickException("Refusing to apply: ROUTER_AGENT_ENABLED=false. Turn it on explicitly first.")

    click.echo(
        f"Resync PPPoE: count={len(subs)} mode={'APPLY' if apply_changes else 'DRY-RUN'} router_enabled={router_enabled}\n"
    )

    changed = skipped = failed = 0

    for s in subs:
        username = (s.pppoe_username or "").strip()
        if not username:
            click.echo(f"[SKIP] sub_id={s.id} missing pppoe_username")
            skipped += 1
            continue

        profile = getattr(s.package, "mikrotik_profile", None) if getattr(s, "package", None) else None
        if not profile:
            click.echo(f"[SKIP] sub_id={s.id} user={username} missing package.mikrotik_profile")
            skipped += 1
            continue

        # Keep comment simple and useful
        comment = f"db_sub_id={s.id} exp={s.expires_at.isoformat() if s.expires_at else '-'}"

        if not apply_changes:
            click.echo(f"[DRY] would ensure+enable secret user={username} profile={profile} comment='{comment}'")
            continue

        try:
            r1 = pppoe_secret_ensure(current_app, username=username, password=None, profile=profile, comment=comment)
            r2 = pppoe_set_disabled(current_app, username=username, disabled=False)
            okish = bool(getattr(r1, "ok", False) or (isinstance(r1, dict) and r1.get("ok")))
            okish = okish and bool(getattr(r2, "ok", False) or (isinstance(r2, dict) and r2.get("ok")))
            if okish:
                click.echo(f"[OK] ensured+enabled user={username} (sub_id={s.id})")
                changed += 1
            else:
                click.echo(f"[FAIL] user={username} sub_id={s.id} r1={r1} r2={r2}")
                failed += 1
        except Exception as e:
            click.echo(f"[EXC] user={username} sub_id={s.id} err={e}")
            failed += 1

    click.echo(f"\nDone. changed={changed} skipped={skipped} failed={failed}")


# ======================================================
# Init hook
# ======================================================
def init_app(app):
    # base
    app.cli.add_command(ping_cli)
    app.cli.add_command(sub_disconnect_last)
    app.cli.add_command(sub_reconnect_last)

    # router group
    app.cli.add_command(router)
