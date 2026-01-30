"""Add admin users

Revision ID: 870303940b31
Revises: ac88cef78057
Create Date: 2026-01-27 00:01:35.814117
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "870303940b31"
down_revision = "ac88cef78057"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)

    # remove server defaults after backfilling existing rows (safety / cleanliness)
    op.alter_column("admin_users", "is_active", server_default=None)
    op.alter_column("admin_users", "created_at", server_default=None)


def downgrade():
    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_table("admin_users")
