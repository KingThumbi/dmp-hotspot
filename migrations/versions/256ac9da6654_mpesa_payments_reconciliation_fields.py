"""mpesa payments reconciliation fields

Revision ID: 256ac9da6654
Revises: 014c32f037f2
Create Date: 2026-02-14 16:51:14.972695

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '256ac9da6654'
down_revision = '014c32f037f2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mpesa_payments", sa.Column("result_code", sa.Integer(), nullable=True))
    op.add_column("mpesa_payments", sa.Column("result_desc", sa.Text(), nullable=True))
    op.add_column("mpesa_payments", sa.Column("external_updated_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("mpesa_payments", sa.Column("reconcile_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("mpesa_payments", sa.Column("last_reconcile_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("mpesa_payments", sa.Column("activation_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("mpesa_payments", sa.Column("last_activation_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("mpesa_payments", sa.Column("activation_error", sa.Text(), nullable=True))

    # Helpful indexes
    op.create_index("ix_mpesa_payments_status", "mpesa_payments", ["status"])
    op.create_index("ix_mpesa_payments_status_created_at", "mpesa_payments", ["status", "created_at"])
    op.create_index("ix_mpesa_payments_subscription_id", "mpesa_payments", ["subscription_id"])
    op.create_index("ix_mpesa_payments_paid_at", "mpesa_payments", ["paid_at"])

def downgrade():
    op.drop_index("ix_mpesa_payments_paid_at", table_name="mpesa_payments")
    op.drop_index("ix_mpesa_payments_subscription_id", table_name="mpesa_payments")
    op.drop_index("ix_mpesa_payments_status_created_at", table_name="mpesa_payments")
    op.drop_index("ix_mpesa_payments_status", table_name="mpesa_payments")

    op.drop_column("mpesa_payments", "activation_error")
    op.drop_column("mpesa_payments", "last_activation_at")
    op.drop_column("mpesa_payments", "activation_attempts")

    op.drop_column("mpesa_payments", "last_reconcile_at")
    op.drop_column("mpesa_payments", "reconcile_attempts")

    op.drop_column("mpesa_payments", "external_updated_at")
    op.drop_column("mpesa_payments", "result_desc")
    op.drop_column("mpesa_payments", "result_code")