"""public_leads created_at server default

Revision ID: d51fc055ced0
Revises: 21a382072aa5
Create Date: 2026-02-19 14:06:40.256428

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd51fc055ced0'
down_revision = '21a382072aa5'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "public_leads",
        "created_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

def downgrade():
    op.alter_column(
        "public_leads",
        "created_at",
        server_default=None,
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )