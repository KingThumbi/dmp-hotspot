"""add account_number to customers

Revision ID: 776e153b6aeb
Revises: 70a52c1dac9c
Create Date: 2026-03-17 20:57:25.914143
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "776e153b6aeb"
down_revision = "70a52c1dac9c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("account_number", sa.String(length=32), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_customers_account_number"),
            ["account_number"],
            unique=True,
        )


def downgrade():
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_customers_account_number"))
        batch_op.drop_column("account_number")