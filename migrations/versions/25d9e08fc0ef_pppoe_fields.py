"""pppoe fields (safe)

Revision ID: 25d9e08fc0ef
Revises: c23d9c559661
Create Date: 2026-01-31 21:53:15.887654
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "25d9e08fc0ef"
down_revision = "c23d9c559661"
branch_labels = None
depends_on = None


def _has_column(table: str, col: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table)]
    return col in cols


def _has_unique(table: str, name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    uqs = insp.get_unique_constraints(table)
    return any(uq.get("name") == name for uq in uqs)


def upgrade():
    # ---- customers: PPPoE creds ----
    if not _has_column("customers", "pppoe_username"):
        op.add_column("customers", sa.Column("pppoe_username", sa.String(length=64), nullable=True))
        op.create_index("ix_customers_pppoe_username", "customers", ["pppoe_username"])

    if not _has_column("customers", "pppoe_password"):
        op.add_column("customers", sa.Column("pppoe_password", sa.String(length=128), nullable=True))

    if not _has_unique("customers", "uq_customers_pppoe_username"):
        # only create unique if column exists
        if _has_column("customers", "pppoe_username"):
            op.create_unique_constraint("uq_customers_pppoe_username", "customers", ["pppoe_username"])

    # ---- subscriptions: service_type ----
    if not _has_column("subscriptions", "service_type"):
        op.add_column(
            "subscriptions",
            sa.Column("service_type", sa.String(length=20), nullable=False, server_default="hotspot"),
        )
        op.create_index("ix_subscriptions_service_type", "subscriptions", ["service_type"])
        op.alter_column("subscriptions", "service_type", server_default=None)

    # NOTE:
    # starts_at and status already exist in your DB -> DO NOT add them here
    # expires_at already exists too -> use it as the PPPoE end time


def downgrade():
    # reverse carefully (only if they exist)
    if _has_column("subscriptions", "service_type"):
        op.drop_index("ix_subscriptions_service_type", table_name="subscriptions")
        op.drop_column("subscriptions", "service_type")

    if _has_unique("customers", "uq_customers_pppoe_username"):
        op.drop_constraint("uq_customers_pppoe_username", "customers", type_="unique")

    if _has_column("customers", "pppoe_password"):
        op.drop_column("customers", "pppoe_password")

    if _has_column("customers", "pppoe_username"):
        op.drop_index("ix_customers_pppoe_username", table_name="customers")
        op.drop_column("customers", "pppoe_username")
