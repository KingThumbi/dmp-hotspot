"""public_leads handled workflow

Revision ID: 70a52c1dac9c
Revises: d51fc055ced0
Create Date: 2026-02-19 18:03:59.851970

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '70a52c1dac9c'
down_revision = 'd51fc055ced0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "public_leads",
        sa.Column("handled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "public_leads",
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "public_leads",
        sa.Column("handled_by", sa.String(length=120), nullable=True),
    )

    # Indexes (safe even if already exists)
    op.execute("CREATE INDEX IF NOT EXISTS ix_public_leads_handled ON public_leads (handled)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_public_leads_created_at ON public_leads (created_at)")

def downgrade():
    # Safe drops
    op.execute("DROP INDEX IF EXISTS ix_public_leads_created_at")
    op.execute("DROP INDEX IF EXISTS ix_public_leads_handled")

    op.drop_column("public_leads", "handled_by")
    op.drop_column("public_leads", "handled_at")
    op.drop_column("public_leads", "handled")