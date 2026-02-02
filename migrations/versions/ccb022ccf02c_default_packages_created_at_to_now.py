"""default packages.created_at to now

Revision ID: ccb022ccf02c
Revises: 21810083e172
Create Date: 2026-02-02 09:27:19.707372

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ccb022ccf02c"
down_revision = "21810083e172"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    ONLY: give packages.created_at a DB-side default.

    Why:
    - packages.created_at is NOT NULL
    - inserts should not be forced to always supply created_at
    - DB becomes source-of-truth for timestamps (industry grade)

    IMPORTANT:
    - Do NOT alter customers/subscriptions constraints here
    - Do NOT drop partial unique indexes (uq_active_*), they prevent duplicate active users
    """
    op.alter_column(
        "packages",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Remove the DB-side default (revert to requiring explicit created_at on insert)."""
    op.alter_column(
        "packages",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
