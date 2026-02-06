"""subscriptions add pending_package_id

Revision ID: f6e7d73af2c9
Revises: 94f093d8a103
Create Date: 2026-02-05 20:35:19.162638

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6e7d73af2c9'
down_revision = '94f093d8a103'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subscriptions", sa.Column("pending_package_id", sa.Integer(), nullable=True))
    op.create_index("ix_subscriptions_pending_package_id", "subscriptions", ["pending_package_id"], unique=False)
    op.create_foreign_key(
        "fk_subscriptions_pending_package_id_packages",
        "subscriptions",
        "packages",
        ["pending_package_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_subscriptions_pending_package_id_packages", "subscriptions", type_="foreignkey")
    op.drop_index("ix_subscriptions_pending_package_id", table_name="subscriptions")
    op.drop_column("subscriptions", "pending_package_id")