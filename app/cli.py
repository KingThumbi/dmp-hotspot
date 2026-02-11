import click
from app.services.router_actions import (
    disconnect_subscription,
    reconnect_subscription,
)
from app.models import Subscription


@click.command("ping-cli")
def ping_cli():
    """Verify custom CLI commands are registered."""
    click.echo("CLI OK: commands are registered.")


@click.command("sub-disconnect-last")
def sub_disconnect_last():
    """DRY-RUN disconnect the most recent subscription."""
    sub = Subscription.query.order_by(Subscription.id.desc()).first()
    if not sub:
        click.echo("No subscriptions found.")
        return
    result = disconnect_subscription(sub, dry_run=True)
    click.echo(result)


@click.command("sub-reconnect-last")
def sub_reconnect_last():
    """DRY-RUN reconnect the most recent subscription."""
    sub = Subscription.query.order_by(Subscription.id.desc()).first()
    if not sub:
        click.echo("No subscriptions found.")
        return
    result = reconnect_subscription(sub, dry_run=True)
    click.echo(result)
