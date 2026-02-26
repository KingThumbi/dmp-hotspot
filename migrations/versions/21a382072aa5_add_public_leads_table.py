"""Add public_leads table

Revision ID: 21a382072aa5
Revises: 256ac9da6654
Create Date: 2026-02-19 13:47:05.688166
"""
from alembic import op
import sqlalchemy as sa

revision = "21a382072aa5"
down_revision = "256ac9da6654"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "public_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("estate", sa.String(length=120), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_leads_kind", "public_leads", ["kind"], unique=False)
    op.create_index("ix_public_leads_phone", "public_leads", ["phone"], unique=False)
    op.create_index("ix_public_leads_created_at", "public_leads", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_public_leads_created_at", table_name="public_leads")
    op.drop_index("ix_public_leads_phone", table_name="public_leads")
    op.drop_index("ix_public_leads_kind", table_name="public_leads")
    op.drop_table("public_leads")
