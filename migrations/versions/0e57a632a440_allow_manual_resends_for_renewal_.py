"""allow manual resends for renewal reminders

Revision ID: 0e57a632a440
Revises: c2b56e71af2f
Create Date: 2026-03-31 21:06:20.816605

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0e57a632a440"
down_revision = "c2b56e71af2f"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add flag to distinguish automatic reminder logs from manual resend logs.
    with op.batch_alter_table("renewal_reminders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_manual_resend",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.create_index(
            "ix_renewal_reminders_is_manual_resend",
            ["is_manual_resend"],
            unique=False,
        )

    # 2) Drop the old unique index if it exists.
    op.execute(
        """
        DROP INDEX IF EXISTS uq_renewal_reminders_subscription_channel_type
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS ix_renewal_reminders_unique_cycle
        """
    )

    # 3) Create a partial unique index that applies only to automatic logs.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_renewal_reminders_auto_cycle
        ON renewal_reminders (subscription_id, channel, reminder_type)
        WHERE is_manual_resend = false
        """
    )

    # 4) Remove server default after existing rows have been backfilled safely.
    with op.batch_alter_table("renewal_reminders", schema=None) as batch_op:
        batch_op.alter_column("is_manual_resend", server_default=None)


def downgrade():
    # 1) Drop the partial unique index.
    op.execute(
        """
        DROP INDEX IF EXISTS uq_renewal_reminders_auto_cycle
        """
    )

    # 2) Restore the old unique index style.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_renewal_reminders_subscription_channel_type
        ON renewal_reminders (subscription_id, channel, reminder_type)
        """
    )

    # 3) Drop resend support column.
    with op.batch_alter_table("renewal_reminders", schema=None) as batch_op:
        batch_op.drop_index("ix_renewal_reminders_is_manual_resend")
        batch_op.drop_column("is_manual_resend")