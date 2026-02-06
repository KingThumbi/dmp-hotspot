"""add pending_package_id to subscriptions

Revision ID: c7cdfc77cfd2
Revises: f6e7d73af2c9
Create Date: 2026-02-06 01:00:20.249886

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7cdfc77cfd2'
down_revision = 'f6e7d73af2c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "subscriptions",
        sa.Column("pending_package_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_subscriptions_pending_package_id",
        "subscriptions",
        ["pending_package_id"],
    )
    op.create_foreign_key(
        "fk_subscriptions_pending_package_id_packages",
        "subscriptions",
        "packages",
        ["pending_package_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_subscriptions_pending_package_id_packages", "subscriptions", type_="foreignkey")
    op.drop_index("ix_subscriptions_pending_package_id", table_name="subscriptions")
    op.drop_column("subscriptions", "pending_package_id")
