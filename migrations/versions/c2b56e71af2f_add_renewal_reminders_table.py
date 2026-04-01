"""add renewal_reminders table safely

Revision ID: c2b56e71af2f
Revises: b3e4fa2478b6
Create Date: 2026-03-31 18:05:27.228847

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c2b56e71af2f"
down_revision = "b3e4fa2478b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "renewal_reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("reminder_type", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("recipient_name", sa.String(length=255), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_renewal_reminders_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            name="fk_renewal_reminders_subscription_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("renewal_reminders", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_renewal_reminders_customer_id"),
            ["customer_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_renewal_reminders_subscription_id"),
            ["subscription_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_renewal_reminders_channel"),
            ["channel"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_renewal_reminders_reminder_type"),
            ["reminder_type"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_renewal_reminders_status"),
            ["status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_renewal_reminders_sent_at",
            ["sent_at"],
            unique=False,
        )
        batch_op.create_index(
            "uq_renewal_reminders_subscription_channel_type",
            ["subscription_id", "channel", "reminder_type"],
            unique=True,
        )


def downgrade():
    with op.batch_alter_table("renewal_reminders", schema=None) as batch_op:
        batch_op.drop_index("uq_renewal_reminders_subscription_channel_type")
        batch_op.drop_index("ix_renewal_reminders_sent_at")
        batch_op.drop_index(batch_op.f("ix_renewal_reminders_status"))
        batch_op.drop_index(batch_op.f("ix_renewal_reminders_reminder_type"))
        batch_op.drop_index(batch_op.f("ix_renewal_reminders_channel"))
        batch_op.drop_index(batch_op.f("ix_renewal_reminders_subscription_id"))
        batch_op.drop_index(batch_op.f("ix_renewal_reminders_customer_id"))

    op.drop_table("renewal_reminders")