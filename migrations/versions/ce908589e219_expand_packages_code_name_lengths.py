"""expand packages code/name lengths

Revision ID: ce908589e219
Revises: ec18915494f7
Create Date: 2026-02-02 12:03:04.685816
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "ce908589e219"
down_revision = "ec18915494f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Only expand:
      - packages.code: varchar(20) -> varchar(30)
      - packages.name: varchar(60) -> varchar(80)

    Keep this migration surgical. No unrelated schema edits.
    """
    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.alter_column(
            "code",
            existing_type=sa.VARCHAR(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "name",
            existing_type=sa.VARCHAR(length=60),
            type_=sa.String(length=80),
            existing_nullable=False,
        )


def downgrade() -> None:
    """
    Revert expansions:
      - packages.code: varchar(30) -> varchar(20)
      - packages.name: varchar(80) -> varchar(60)
    """
    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=80),
            type_=sa.VARCHAR(length=60),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "code",
            existing_type=sa.String(length=30),
            type_=sa.VARCHAR(length=20),
            existing_nullable=False,
        )
