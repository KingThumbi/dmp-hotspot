"""add admin_user

Revision ID: 9fc22be0664d
Revises: 870303940b31
Create Date: 2026-01-27 01:13:19.148733
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9fc22be0664d"
down_revision = "870303940b31"
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================
    # 1) packages.created_at (SAFE ADD: nullable -> backfill -> not null)
    # =========================================================
    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))

    # Backfill existing rows (prevents NOT NULL violation)
    op.execute("UPDATE packages SET created_at = NOW() WHERE created_at IS NULL")

    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            nullable=False,
        )

    # =========================================================
    # 2) Add helpful indexes (NON-DESTRUCTIVE)
    #    - We do NOT drop unique constraints. Your existing uniques remain intact.
    # =========================================================

    # Subscriptions indexes
    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_subscriptions_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_expires_at"), ["expires_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_last_tx_id"), ["last_tx_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_mac_address"), ["mac_address"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_package_id"), ["package_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_router_username"), ["router_username"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_starts_at"), ["starts_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscriptions_status"), ["status"], unique=False)

    # Transactions indexes (keep unique constraints as-is; add non-unique ones)
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_transactions_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_transactions_customer_id"), ["customer_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_transactions_merchant_request_id"), ["merchant_request_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_transactions_package_id"), ["package_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_transactions_status"), ["status"], unique=False)


def downgrade():
    # Reverse indexes we added
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_status"))
        batch_op.drop_index(batch_op.f("ix_transactions_package_id"))
        batch_op.drop_index(batch_op.f("ix_transactions_merchant_request_id"))
        batch_op.drop_index(batch_op.f("ix_transactions_customer_id"))
        batch_op.drop_index(batch_op.f("ix_transactions_created_at"))

    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_subscriptions_status"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_starts_at"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_router_username"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_package_id"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_mac_address"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_last_tx_id"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_expires_at"))
        batch_op.drop_index(batch_op.f("ix_subscriptions_customer_id"))

    # Remove created_at (safe because it was introduced here)
    with op.batch_alter_table("packages", schema=None) as batch_op:
        batch_op.drop_column("created_at")
