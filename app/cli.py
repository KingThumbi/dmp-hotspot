# app/cli.py
from __future__ import annotations

from datetime import datetime
from typing import Any

import click
from flask import current_app
from flask.cli import with_appcontext

from app.models import Subscription
from app.services.pppoe_expiry import sweep_expired_accounts
from app.services.pppoe_reconcile import reconcile_subscription_router_state
from app.services.router_actions import disconnect_subscription, reconnect_subscription


# ======================================================
# Internal helpers
# ======================================================
def _utcnow_naive() -> datetime:
    """Project convention: DB stores UTC-naive datetimes."""
    return datetime.utcnow()


def _echo_result(result: dict[str, Any]) -> None:
    """Pretty-print a generic result dict."""
    click.echo(
        click.style("Result:", fg="cyan", bold=True)
        + f" ok={result.get('ok')} "
        + f"dry_run={result.get('dry_run', '-')}"
    )
    for k, v in result.items():
        if k in {"ok", "dry_run"}:
            continue
        click.echo(f"  - {k}: {v}")


def _pppoe_query(*, only_active: bool) -> list[Subscription]:
    """
    Return PPPoE subscriptions.
    If only_active=True, return only active + unexpired + username-present rows.
    """
    if only_active:
        now = _utcnow_naive()
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

    return (
        Subscription.query.filter(Subscription.service_type == "pppoe")
        .order_by(Subscription.id.asc())
        .all()
    )


def _limit_rows(rows: list[Subscription], limit: int | None) -> list[Subscription]:
    if limit is None:
        return rows
    return rows[: max(limit, 0)]


def _sub_identity(sub: Subscription) -> str:
    svc = (getattr(sub, "service_type", "") or "").strip().lower()
    if svc == "pppoe":
        return (getattr(sub, "pppoe_username", None) or "").strip()
    if svc == "hotspot":
        return (getattr(sub, "hotspot_username", None) or "").strip()
    return ""


# ======================================================
# Basic CLI sanity
# ======================================================
@click.command("ping-cli")
def ping_cli() -> None:
    """Verify custom CLI commands are registered."""
    click.echo("CLI OK: commands are registered.")


@click.command("sub-disconnect-last")
@with_appcontext
def sub_disconnect_last() -> None:
    """DRY-RUN disconnect the most recent subscription."""
    sub = Subscription.query.order_by(Subscription.id.desc()).first()
    if not sub:
        click.echo("No subscriptions found.")
        return

    result = disconnect_subscription(sub, dry_run=True)
    _echo_result(result)


@click.command("sub-reconnect-last")
@with_appcontext
def sub_reconnect_last() -> None:
    """DRY-RUN reconnect the most recent subscription."""
    sub = Subscription.query.order_by(Subscription.id.desc()).first()
    if not sub:
        click.echo("No subscriptions found.")
        return

    result = reconnect_subscription(sub, dry_run=True)
    _echo_result(result)


@click.command("sweep-expired-pppoe")
@with_appcontext
def sweep_expired_pppoe_command() -> None:
    """
    Find expired active PPPoE-linked accounts in DB, mark them expired,
    and disable/disconnect them through the configured enforcement path.
    """
    result = sweep_expired_accounts()
    _echo_result(result if isinstance(result, dict) else {"ok": True, "result": result})

@click.command("reconcile-router-state")
@click.option("--apply", "apply_changes", is_flag=True, help="Apply changes. Default is dry-run.")
@click.option("--limit", default=100, show_default=True, type=int, help="Max subscriptions to check.")
@with_appcontext
def reconcile_router_state_cmd(apply_changes: bool, limit: int) -> None:
    """
    Self-heal router state from DB truth:
    - active + unexpired => reconnect/enable
    - expired/inactive => disconnect/disable
    """
    result = reconcile_subscription_router_state(
        dry_run=not apply_changes,
        limit=limit,
    )

    click.echo(
        f"ok={result['ok']} dry_run={result['dry_run']} checked={result['checked']} "
        f"planned={result['planned']} applied={result['applied']} "
        f"skipped={result['skipped']} failures={result['failures']}"
    )

    for item in result.get("details", []):
        click.echo(
            f"[{item.get('result')}] "
            f"sub_id={item.get('sub_id')} "
            f"svc={item.get('svc')} "
            f"user={item.get('identity', '-')} "
            f"should_be_active={item.get('should_be_active')} "
            f"msg={item.get('message', '-')}"
        )
        
# ======================================================
# Router tools
# ======================================================
@click.group()
def router() -> None:
    """Router tools (audit/resync)."""


@router.command("audit-pppoe")
@click.option("--active", "only_active", is_flag=True, help="Audit only active, unexpired PPPoE subs from DB.")
@with_appcontext
def audit_pppoe(only_active: bool) -> None:
    """
    Read-only audit:
    checks whether PPPoE secrets exist on MikroTik and whether they are disabled.
    Does NOT modify the router.
    """
    from app.router_agent import _pppoe_pool, pppoe_secret_get

    subs = _pppoe_query(only_active=only_active)

    if not subs:
        click.echo("No PPPoE subscriptions matched.")
        return

    try:
        pool = _pppoe_pool(current_app)
        api = pool.get_api()
    except Exception as e:
        raise click.ClickException(f"Router connection failed: {e}") from e

    click.echo(f"Auditing {len(subs)} PPPoE subscriptions on router...\n")

    ok = 0
    missing = 0
    disabled = 0
    skipped = 0

    for sub in subs:
        username = (sub.pppoe_username or "").strip()
        if not username:
            click.echo(f"[SKIP] sub_id={sub.id} missing pppoe_username")
            skipped += 1
            continue

        row = pppoe_secret_get(api, username)
        if not row:
            click.echo(f"[MISSING] sub_id={sub.id} user={username} expires_at={sub.expires_at}")
            missing += 1
            continue

        is_disabled = str(row.get("disabled", "")).strip().lower() in {"yes", "true", "1"}
        if is_disabled:
            click.echo(f"[DISABLED] sub_id={sub.id} user={username} expires_at={sub.expires_at}")
            disabled += 1
        else:
            click.echo(f"[OK] sub_id={sub.id} user={username} expires_at={sub.expires_at}")
            ok += 1

    click.echo(
        f"\nSummary: OK={ok} DISABLED={disabled} MISSING={missing} SKIPPED={skipped}"
    )


@router.command("resync-pppoe")
@click.option("--active", "only_active", is_flag=True, help="Resync only active, unexpired PPPoE subs from DB.")
@click.option("--limit", type=int, default=25, show_default=True, help="Max number of subs to process.")
@click.option("--apply", "apply_changes", is_flag=True, help="Actually modify router. Default is DRY-RUN.")
@with_appcontext
def resync_pppoe(only_active: bool, limit: int, apply_changes: bool) -> None:
    """
    Resync PPPoE router state to match DB for selected subscriptions:
    - If secret missing: ensure/create it with correct profile/comment
    - Ensure secret is enabled (disabled=no)
    """
    from app.router_agent import pppoe_secret_ensure, pppoe_set_disabled

    subs = _limit_rows(_pppoe_query(only_active=only_active), limit)

    if not subs:
        click.echo("No PPPoE subscriptions matched.")
        return

    router_enabled = bool(current_app.config.get("ROUTER_AGENT_ENABLED", False))
    if apply_changes and not router_enabled:
        raise click.ClickException(
            "Refusing to apply: ROUTER_AGENT_ENABLED=false. Turn it on explicitly first."
        )

    mode = "APPLY" if apply_changes else "DRY-RUN"
    click.echo(
        f"Resync PPPoE: count={len(subs)} mode={mode} router_enabled={router_enabled}\n"
    )

    changed = 0
    skipped = 0
    failed = 0

    for sub in subs:
        username = (sub.pppoe_username or "").strip()
        if not username:
            click.echo(f"[SKIP] sub_id={sub.id} missing pppoe_username")
            skipped += 1
            continue

        profile = getattr(sub.package, "mikrotik_profile", None) if getattr(sub, "package", None) else None
        if not profile:
            click.echo(f"[SKIP] sub_id={sub.id} user={username} missing package.mikrotik_profile")
            skipped += 1
            continue

        comment = f"db_sub_id={sub.id} exp={sub.expires_at.isoformat() if sub.expires_at else '-'}"

        if not apply_changes:
            click.echo(
                f"[DRY] would ensure+enable secret "
                f"user={username} profile={profile} comment='{comment}'"
            )
            continue

        try:
            res_ensure = pppoe_secret_ensure(
                current_app,
                username=username,
                password=None,
                profile=profile,
                comment=comment,
            )
            res_enable = pppoe_set_disabled(current_app, username=username, disabled=False)

            ok_ensure = bool(getattr(res_ensure, "ok", False) or (isinstance(res_ensure, dict) and res_ensure.get("ok")))
            ok_enable = bool(getattr(res_enable, "ok", False) or (isinstance(res_enable, dict) and res_enable.get("ok")))

            if ok_ensure and ok_enable:
                click.echo(f"[OK] ensured+enabled user={username} (sub_id={sub.id})")
                changed += 1
            else:
                click.echo(f"[FAIL] user={username} sub_id={sub.id} ensure={res_ensure} enable={res_enable}")
                failed += 1

        except Exception as e:
            click.echo(f"[EXC] user={username} sub_id={sub.id} err={e}")
            failed += 1

    click.echo(f"\nDone. changed={changed} skipped={skipped} failed={failed}")


# ======================================================
# App integration
# ======================================================
def init_app(app) -> None:
    """Register CLI commands with the Flask app."""
    app.cli.add_command(ping_cli)
    app.cli.add_command(sub_disconnect_last)
    app.cli.add_command(sub_reconnect_last)
    app.cli.add_command(sweep_expired_pppoe_command)
    app.cli.add_command(reconcile_router_state_cmd)
    app.cli.add_command(router)