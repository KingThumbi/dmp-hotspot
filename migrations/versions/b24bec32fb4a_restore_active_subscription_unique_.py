"""restore active subscription unique indexes

Revision ID: b24bec32fb4a
Revises: ce908589e219
Create Date: 2026-02-02 12:08:50

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b24bec32fb4a"
down_revision = "ce908589e219"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Restore the two partial unique indexes that enforce:
      - only one ACTIVE hotspot entitlement per hotspot_username
      - only one ACTIVE PPPoE entitlement per pppoe_username
    """

    # Hotspot: one ACTIVE per hotspot_username (phone)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_hotspot_username
        ON subscriptions (hotspot_username)
        WHERE service_type = 'hotspot'
          AND status = 'active'
          AND hotspot_username IS NOT NULL;
        """
    )

    # PPPoE: one ACTIVE per pppoe_username (D###/DA####)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_pppoe_username
        ON subscriptions (pppoe_username)
        WHERE service_type = 'pppoe'
          AND status = 'active'
          AND pppoe_username IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_active_pppoe_username;")
    op.execute("DROP INDEX IF EXISTS uq_active_hotspot_username;")
