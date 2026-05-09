"""add router actions observe queue

Revision ID: 4f9a2c7b8d10
Revises: 0e57a632a440
Create Date: 2026-05-09 21:35:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f9a2c7b8d10"
down_revision = "0e57a632a440"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "router_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action_key", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("service_type", sa.String(length=20), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("package_id", sa.Integer(), nullable=True),
        sa.Column("router_id", sa.Integer(), nullable=True),
        sa.Column("identity", sa.String(length=80), nullable=True),
        sa.Column("profile_name", sa.String(length=80), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("locked_by", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=60), nullable=True),
        sa.Column("created_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_router_actions_action_key", "router_actions", ["action_key"], unique=True)
    op.create_index("ix_router_actions_action_type", "router_actions", ["action_type"], unique=False)
    op.create_index("ix_router_actions_correlation_id", "router_actions", ["correlation_id"], unique=False)
    op.create_index("ix_router_actions_created_at", "router_actions", ["created_at"], unique=False)
    op.create_index("ix_router_actions_created_by", "router_actions", ["created_by"], unique=False)
    op.create_index("ix_router_actions_created_by_admin_id", "router_actions", ["created_by_admin_id"], unique=False)
    op.create_index("ix_router_actions_customer_id", "router_actions", ["customer_id"], unique=False)
    op.create_index("ix_router_actions_identity", "router_actions", ["identity"], unique=False)
    op.create_index("ix_router_actions_next_run_at", "router_actions", ["next_run_at"], unique=False)
    op.create_index("ix_router_actions_package_id", "router_actions", ["package_id"], unique=False)
    op.create_index("ix_router_actions_priority", "router_actions", ["priority"], unique=False)
    op.create_index("ix_router_actions_router_id", "router_actions", ["router_id"], unique=False)
    op.create_index("ix_router_actions_service_type", "router_actions", ["service_type"], unique=False)
    op.create_index("ix_router_actions_status", "router_actions", ["status"], unique=False)
    op.create_index(
        "ix_router_actions_status_next_run_at_priority",
        "router_actions",
        ["status", "next_run_at", "priority"],
        unique=False,
    )
    op.create_index("ix_router_actions_subscription_id", "router_actions", ["subscription_id"], unique=False)
    op.create_index("ix_router_actions_updated_at", "router_actions", ["updated_at"], unique=False)


def downgrade():
    op.drop_index("ix_router_actions_updated_at", table_name="router_actions")
    op.drop_index("ix_router_actions_subscription_id", table_name="router_actions")
    op.drop_index("ix_router_actions_status_next_run_at_priority", table_name="router_actions")
    op.drop_index("ix_router_actions_status", table_name="router_actions")
    op.drop_index("ix_router_actions_service_type", table_name="router_actions")
    op.drop_index("ix_router_actions_router_id", table_name="router_actions")
    op.drop_index("ix_router_actions_priority", table_name="router_actions")
    op.drop_index("ix_router_actions_package_id", table_name="router_actions")
    op.drop_index("ix_router_actions_next_run_at", table_name="router_actions")
    op.drop_index("ix_router_actions_identity", table_name="router_actions")
    op.drop_index("ix_router_actions_customer_id", table_name="router_actions")
    op.drop_index("ix_router_actions_created_by_admin_id", table_name="router_actions")
    op.drop_index("ix_router_actions_created_by", table_name="router_actions")
    op.drop_index("ix_router_actions_created_at", table_name="router_actions")
    op.drop_index("ix_router_actions_correlation_id", table_name="router_actions")
    op.drop_index("ix_router_actions_action_type", table_name="router_actions")
    op.drop_index("ix_router_actions_action_key", table_name="router_actions")
    op.drop_table("router_actions")
