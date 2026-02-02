"""packages.created_at server default

Revision ID: ec18915494f7
Revises: ccb022ccf02c
Create Date: 2026-02-02 11:49:02.318271

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ec18915494f7"
down_revision = "ccb022ccf02c"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Backfill any existing NULLs (safety; should be none if NOT NULL held)
    op.execute("UPDATE packages SET created_at = timezone('utc', now()) WHERE created_at IS NULL")

    # 2) Add a Postgres server default so raw SQL inserts don't fail
    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            existing_nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        )


def downgrade():
    # Remove server default (back to app-side default only)
    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            existing_nullable=False,
            server_default=None,
        )
