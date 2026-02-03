"""phase-e add roles to admin_users

Revision ID: 6be60d1c0bf3
Revises: 88d5696acf31
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6be60d1c0bf3"
down_revision = "88d5696acf31"
branch_labels = None
depends_on = None


def upgrade():
    # Add Phase E columns (production-safe defaults)
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=80), nullable=True))

        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'admin'"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "is_superadmin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

        batch_op.create_index("ix_admin_users_role", ["role"], unique=False)
        batch_op.create_index("ix_admin_users_is_superadmin", ["is_superadmin"], unique=False)

    # Keep DB defaults for future inserts too
    op.execute("ALTER TABLE admin_users ALTER COLUMN role SET DEFAULT 'admin'")
    op.execute("ALTER TABLE admin_users ALTER COLUMN is_superadmin SET DEFAULT false")


def downgrade():
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.drop_index("ix_admin_users_is_superadmin")
        batch_op.drop_index("ix_admin_users_role")

        batch_op.drop_column("is_superadmin")
        batch_op.drop_column("role")
        batch_op.drop_column("name")
