"""add max_devices to packages

Revision ID: 014c32f037f2
Revises: bc243d2fe9cb
Create Date: 2026-02-10 13:14:51.622572

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014c32f037f2'
down_revision = 'bc243d2fe9cb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "packages",
        sa.Column("max_devices", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )

    # Optional: remove server_default after backfill (keeps schema tidy)
    op.alter_column("packages", "max_devices", server_default=None)


def downgrade():
    op.drop_column("packages", "max_devices")
