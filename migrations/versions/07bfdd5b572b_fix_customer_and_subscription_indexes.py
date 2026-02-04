"""phase d: assets and expenses

Revision ID: 07bfdd5b572b
Revises: b24bec32fb4a
Create Date: 2026-02-03 09:21:16.224986
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "07bfdd5b572b"
down_revision = "b24bec32fb4a"
branch_labels = None
depends_on = None


def upgrade():
    # NOTE:
    # This migration was originally auto-generated using batch_op.* calls.
    # On Render/production we discovered schema drift (some indexes already exist),
    # so we make the operations defensive / idempotent.

    # ---------------------------------------------------------
    # customers: move from old UNIQUE constraint to a unique index
    # ---------------------------------------------------------

    # Drop the old unique constraint if it exists (may not exist in prod)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_customers_pppoe_username'
            ) THEN
                ALTER TABLE customers DROP CONSTRAINT uq_customers_pppoe_username;
            END IF;
        END $$;
        """
    )

    # Create the unique index if it does not exist
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_pppoe_username
        ON customers (pppoe_username);
        """
    )

    # ---------------------------------------------------------
    # subscriptions: drop partial unique indexes if they exist,
    # then add helpful lookup indexes
    # ---------------------------------------------------------

    # Drop partial indexes defensively (names matter; use exact names)
    op.execute("DROP INDEX IF EXISTS uq_active_hotspot_username;")
    op.execute("DROP INDEX IF EXISTS uq_active_pppoe_username;")

    # Create normal indexes if missing
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_subscriptions_created_at
        ON subscriptions (created_at);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_subscriptions_service_type
        ON subscriptions (service_type);
        """
    )


def downgrade():
    # Reverse defensively.

    # Drop non-unique indexes if they exist
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_service_type;")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_created_at;")

    # Re-create the partial unique indexes if missing
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_pppoe_username
        ON subscriptions (pppoe_username)
        WHERE (service_type::text = 'pppoe'::text)
          AND (status::text = 'active'::text)
          AND (pppoe_username IS NOT NULL);
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_hotspot_username
        ON subscriptions (hotspot_username)
        WHERE (service_type::text = 'hotspot'::text)
          AND (status::text = 'active'::text)
          AND (hotspot_username IS NOT NULL);
        """
    )

    # Drop the unique index on customers if it exists
    op.execute("DROP INDEX IF EXISTS ix_customers_pppoe_username;")

    # Re-create the old unique constraint if missing
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_customers_pppoe_username'
            ) THEN
                ALTER TABLE customers
                ADD CONSTRAINT uq_customers_pppoe_username
                UNIQUE (pppoe_username);
            END IF;
        END $$;
        """
    )