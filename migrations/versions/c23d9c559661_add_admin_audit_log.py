"""Add admin audit log

Revision ID: c23d9c559661
Revises: 9fc22be0664d
Create Date: 2026-01-29 19:41:09.735006
"""
from alembic import op
import sqlalchemy as sa

revision = "c23d9c559661"
down_revision = "9fc22be0664d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),      # removed index=True
        sa.Column("action", sa.String(length=60), nullable=False),     # removed index=True
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("meta_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),        # removed index=True
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"]),
    )

    # Explicit index names (stable + clear)
    op.create_index("ix_admin_audit_logs_admin_user_id", "admin_audit_logs", ["admin_user_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_user_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
