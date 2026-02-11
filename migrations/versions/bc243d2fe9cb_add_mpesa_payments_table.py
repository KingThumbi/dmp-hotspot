"""add mpesa_payments table

Revision ID: bc243d2fe9cb
Revises: c7cdfc77cfd2
Create Date: 2026-02-09 23:13:50.276176
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bc243d2fe9cb"
down_revision = "c7cdfc77cfd2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Idempotent guard (helps if table already exists in some env)
    if "mpesa_payments" in insp.get_table_names(schema="public"):
        return

    op.create_table(
        "mpesa_payments",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),

        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),

        sa.Column("checkout_request_id", sa.String(length=64), nullable=True),
        sa.Column("merchant_request_id", sa.String(length=64), nullable=True),
        sa.Column("mpesa_receipt", sa.String(length=40), nullable=True, unique=True),

        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("raw_callback", sa.JSON(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Explicit index (reliable across environments)
    op.create_index(
        "ix_mpesa_payments_checkout_request_id",
        "mpesa_payments",
        ["checkout_request_id"],
    )

    # Add FKs only if referenced tables exist (prevents deploy-time failure)
    public_tables = set(insp.get_table_names(schema="public"))
    if "customers" in public_tables:
        op.create_foreign_key(
            "fk_mpesa_payments_customer",
            "mpesa_payments",
            "customers",
            ["customer_id"],
            ["id"],
        )
    if "subscriptions" in public_tables:
        op.create_foreign_key(
            "fk_mpesa_payments_subscription",
            "mpesa_payments",
            "subscriptions",
            ["subscription_id"],
            ["id"],
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "mpesa_payments" not in insp.get_table_names(schema="public"):
        return

    # Drop index first, then table (safe ordering)
    op.drop_index("ix_mpesa_payments_checkout_request_id", table_name="mpesa_payments")
    op.drop_table("mpesa_payments")
