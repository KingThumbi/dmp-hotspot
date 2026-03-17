"""add subscription_change_logs table

Revision ID: b3e4fa2478b6
Revises: 776e153b6aeb
Create Date: 2026-03-18 00:15:00.944572
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3e4fa2478b6"
down_revision = "776e153b6aeb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscription_change_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("old_package_id", sa.Integer(), nullable=True),
        sa.Column("new_package_id", sa.Integer(), nullable=True),
        sa.Column("old_pending_package_id", sa.Integer(), nullable=True),
        sa.Column("new_pending_package_id", sa.Integer(), nullable=True),
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("old_starts_at", sa.DateTime(), nullable=True),
        sa.Column("new_starts_at", sa.DateTime(), nullable=True),
        sa.Column("old_expires_at", sa.DateTime(), nullable=True),
        sa.Column("new_expires_at", sa.DateTime(), nullable=True),
        sa.Column("old_identity", sa.String(length=64), nullable=True),
        sa.Column("new_identity", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["changed_by_admin_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_subscription_change_logs_subscription_id"),
        "subscription_change_logs",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_change_logs_customer_id"),
        "subscription_change_logs",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_change_logs_changed_by_admin_id"),
        "subscription_change_logs",
        ["changed_by_admin_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_change_logs_created_at"),
        "subscription_change_logs",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_subscription_change_logs_created_at"), table_name="subscription_change_logs")
    op.drop_index(op.f("ix_subscription_change_logs_changed_by_admin_id"), table_name="subscription_change_logs")
    op.drop_index(op.f("ix_subscription_change_logs_customer_id"), table_name="subscription_change_logs")
    op.drop_index(op.f("ix_subscription_change_logs_subscription_id"), table_name="subscription_change_logs")
    op.drop_table("subscription_change_logs")