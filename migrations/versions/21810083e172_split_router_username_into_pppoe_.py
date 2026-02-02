"""split router_username into pppoe_username and hotspot_username

Revision ID: 21810083e172
Revises: 25d9e08fc0ef
Create Date: 2026-02-01 20:46:18.154496
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "21810083e172"
down_revision = "25d9e08fc0ef"
branch_labels = None
depends_on = None


def upgrade():
    # ---------------------------------------------------------
    # 1) Add new columns for clean separation
    # ---------------------------------------------------------
    op.add_column("subscriptions", sa.Column("pppoe_username", sa.String(length=64), nullable=True))
    op.add_column("subscriptions", sa.Column("hotspot_username", sa.String(length=64), nullable=True))

    # ---------------------------------------------------------
    # 2) Add indexes (non-unique; uniqueness is enforced via partial indexes below)
    # ---------------------------------------------------------
    op.create_index("ix_subscriptions_pppoe_username", "subscriptions", ["pppoe_username"], unique=False)
    op.create_index("ix_subscriptions_hotspot_username", "subscriptions", ["hotspot_username"], unique=False)

    # ---------------------------------------------------------
    # 3) Backfill from existing router_username using service_type
    # - PPPoE: router_username -> pppoe_username
    # - Hotspot: router_username -> hotspot_username
    # ---------------------------------------------------------
    op.execute(
        """
        UPDATE subscriptions
        SET pppoe_username = router_username
        WHERE service_type = 'pppoe'
          AND router_username IS NOT NULL
          AND pppoe_username IS NULL;
        """
    )

    op.execute(
        """
        UPDATE subscriptions
        SET hotspot_username = router_username
        WHERE service_type = 'hotspot'
          AND router_username IS NOT NULL
          AND hotspot_username IS NULL;
        """
    )

    # ---------------------------------------------------------
    # 4) Make router_username nullable (deprecate the overloaded field)
    #    Keep the column for now to avoid breaking older code paths,
    #    but new code should stop writing to it.
    # ---------------------------------------------------------
    op.alter_column(
        "subscriptions",
        "router_username",
        existing_type=sa.VARCHAR(length=64),  # your current / intended type
        nullable=True,
    )

    # ---------------------------------------------------------
    # 5) Industry-grade duplicate prevention
    #    Prevent duplicate ACTIVE accounts per username by service type.
    #    (Allows history: expired/pending rows are fine.)
    # ---------------------------------------------------------
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_pppoe_username
        ON subscriptions (pppoe_username)
        WHERE service_type = 'pppoe'
          AND status = 'active'
          AND pppoe_username IS NOT NULL;
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_hotspot_username
        ON subscriptions (hotspot_username)
        WHERE service_type = 'hotspot'
          AND status = 'active'
          AND hotspot_username IS NOT NULL;
        """
    )


def downgrade():
    # ---------------------------------------------------------
    # Reverse the upgrade cleanly
    # ---------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS uq_active_hotspot_username;")
    op.execute("DROP INDEX IF EXISTS uq_active_pppoe_username;")

    op.drop_index("ix_subscriptions_hotspot_username", table_name="subscriptions")
    op.drop_index("ix_subscriptions_pppoe_username", table_name="subscriptions")

    # revert router_username nullable change (back to NOT NULL)
    op.alter_column(
        "subscriptions",
        "router_username",
        existing_type=sa.VARCHAR(length=64),
        nullable=False,
    )

    op.drop_column("subscriptions", "hotspot_username")
    op.drop_column("subscriptions", "pppoe_username")
