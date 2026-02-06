"""phase_a_locations_tickets

Revision ID: 94f093d8a103
Revises: 6be60d1c0bf3
Create Date: 2026-02-04 19:24:20.719694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94f093d8a103'
down_revision = '6be60d1c0bf3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # customer_locations
    # ---------------------------------------------------------
    op.create_table(
        "customer_locations",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),

        sa.Column("label", sa.String(length=80), nullable=True),

        sa.Column("county", sa.String(length=60), nullable=True),
        sa.Column("town", sa.String(length=60), nullable=True),
        sa.Column("estate", sa.String(length=80), nullable=True),
        sa.Column("apartment_name", sa.String(length=120), nullable=True),
        sa.Column("house_no", sa.String(length=40), nullable=True),
        sa.Column("landmark", sa.String(length=200), nullable=True),

        sa.Column("gps_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("gps_lng", sa.Numeric(9, 6), nullable=True),

        sa.Column("notes", sa.Text(), nullable=True),

        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active_from_utc", sa.DateTime(), nullable=False),
        sa.Column("active_to_utc", sa.DateTime(), nullable=True),

        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_index("ix_customer_locations_customer_id", "customer_locations", ["customer_id"])
    op.create_index("ix_customer_locations_active", "customer_locations", ["active"])
    op.create_index("ix_customer_locations_active_from_utc", "customer_locations", ["active_from_utc"])
    op.create_index("ix_customer_locations_active_to_utc", "customer_locations", ["active_to_utc"])
    op.create_index("ix_customer_locations_created_by_admin_id", "customer_locations", ["created_by_admin_id"])

    # Enforce ONE active location per customer (Postgres partial unique index)
    op.create_index(
        "uq_customer_one_active_location",
        "customer_locations",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("active = true"),
    )

    # ---------------------------------------------------------
    # tickets
    # ---------------------------------------------------------
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column("code", sa.String(length=30), nullable=False),

        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("customer_locations.id", ondelete="SET NULL"),
            nullable=True,
        ),

        sa.Column("category", sa.String(length=40), nullable=False, server_default=sa.text("'outage'")),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default=sa.text("'med'")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'open'")),

        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        sa.Column(
            "opened_at_utc",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("resolved_at_utc", sa.DateTime(), nullable=True),
        sa.Column("closed_at_utc", sa.DateTime(), nullable=True),

        sa.Column(
            "created_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_to_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_unique_constraint("uq_tickets_code", "tickets", ["code"])
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"])
    op.create_index("ix_tickets_subscription_id", "tickets", ["subscription_id"])
    op.create_index("ix_tickets_location_id", "tickets", ["location_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_created_by_admin_id", "tickets", ["created_by_admin_id"])
    op.create_index("ix_tickets_assigned_to_admin_id", "tickets", ["assigned_to_admin_id"])
    op.create_index("ix_tickets_opened_at_utc", "tickets", ["opened_at_utc"])
    op.create_index("ix_tickets_resolved_at_utc", "tickets", ["resolved_at_utc"])

    # ---------------------------------------------------------
    # ticket_updates
    # ---------------------------------------------------------
    op.create_table(
        "ticket_updates",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),

        sa.Column(
            "actor_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),

        sa.Column("message", sa.Text(), nullable=True),

        sa.Column("status_from", sa.String(length=20), nullable=True),
        sa.Column("status_to", sa.String(length=20), nullable=True),

        sa.Column(
            "assigned_from_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_to_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_index("ix_ticket_updates_ticket_id", "ticket_updates", ["ticket_id"])
    op.create_index("ix_ticket_updates_actor_admin_id", "ticket_updates", ["actor_admin_id"])
    op.create_index("ix_ticket_updates_created_at", "ticket_updates", ["created_at"])
    op.create_index("ix_ticket_updates_status_to", "ticket_updates", ["status_to"])
    op.create_index("ix_ticket_updates_assigned_to_admin_id", "ticket_updates", ["assigned_to_admin_id"])


def downgrade() -> None:
    # ticket_updates
    op.drop_index("ix_ticket_updates_assigned_to_admin_id", table_name="ticket_updates")
    op.drop_index("ix_ticket_updates_status_to", table_name="ticket_updates")
    op.drop_index("ix_ticket_updates_created_at", table_name="ticket_updates")
    op.drop_index("ix_ticket_updates_actor_admin_id", table_name="ticket_updates")
    op.drop_index("ix_ticket_updates_ticket_id", table_name="ticket_updates")
    op.drop_table("ticket_updates")

    # tickets
    op.drop_index("ix_tickets_resolved_at_utc", table_name="tickets")
    op.drop_index("ix_tickets_opened_at_utc", table_name="tickets")
    op.drop_index("ix_tickets_assigned_to_admin_id", table_name="tickets")
    op.drop_index("ix_tickets_created_by_admin_id", table_name="tickets")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_location_id", table_name="tickets")
    op.drop_index("ix_tickets_subscription_id", table_name="tickets")
    op.drop_index("ix_tickets_customer_id", table_name="tickets")
    op.drop_constraint("uq_tickets_code", "tickets", type_="unique")
    op.drop_table("tickets")

    # customer_locations
    op.drop_index("uq_customer_one_active_location", table_name="customer_locations")
    op.drop_index("ix_customer_locations_created_by_admin_id", table_name="customer_locations")
    op.drop_index("ix_customer_locations_active_to_utc", table_name="customer_locations")
    op.drop_index("ix_customer_locations_active_from_utc", table_name="customer_locations")
    op.drop_index("ix_customer_locations_active", table_name="customer_locations")
    op.drop_index("ix_customer_locations_customer_id", table_name="customer_locations")
    op.drop_table("customer_locations")