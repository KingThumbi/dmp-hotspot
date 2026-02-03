"""utc defaults for phase d created_at

Revision ID: 4177cf17ade1
Revises: 8fcb7fc1cc37
Create Date: 2026-02-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4177cf17ade1"
down_revision = "8fcb7fc1cc37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "assets",
        "created_at",
        server_default=sa.text("timezone('utc', now())"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "asset_events",
        "created_at",
        server_default=sa.text("timezone('utc', now())"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "expenses",
        "created_at",
        server_default=sa.text("timezone('utc', now())"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "assets",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "asset_events",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "expenses",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
