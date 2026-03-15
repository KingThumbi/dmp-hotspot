# app/cli/pppoe_jobs.py
import click
from flask.cli import with_appcontext

from app.services.pppoe_expiry import sweep_expired_accounts


@click.command("sweep-expired-pppoe")
@with_appcontext
def sweep_expired_pppoe_command():
    result = sweep_expired_accounts()
    click.echo(result)
