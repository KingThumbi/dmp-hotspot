"""phase d.3 expense categories and templates

Revision ID: 88d5696acf31
Revises: 4177cf17ade1
Create Date: 2026-02-03 12:09:39.697073

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "88d5696acf31"
down_revision = "4177cf17ade1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================
    # 1) expense_categories (supports subcategories via parent_id)
    # =========================================================
    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["expense_categories.id"],
            name="expense_categories_parent_id_fkey",
            ondelete="SET NULL",
        ),
    )

    op.create_index("ix_expense_categories_name", "expense_categories", ["name"])
    op.create_index("ix_expense_categories_parent_id", "expense_categories", ["parent_id"])
    op.create_unique_constraint(
        "uq_expense_categories_parent_name",
        "expense_categories",
        ["parent_id", "name"],
    )

    # =========================================================
    # 2) expense_templates (reusable named expenses)
    # =========================================================
    op.create_table(
        "expense_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),  # e.g. "KPLC Bill"
        sa.Column("default_amount", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["expense_categories.id"],
            name="expense_templates_category_id_fkey",
            ondelete="RESTRICT",
        ),
    )

    op.create_index("ix_expense_templates_category_id", "expense_templates", ["category_id"])
    op.create_index("ix_expense_templates_name", "expense_templates", ["name"])
    op.create_unique_constraint(
        "uq_expense_templates_category_name",
        "expense_templates",
        ["category_id", "name"],
    )

    # =========================================================
    # 3) Link expenses -> categories/templates
    # Keep existing expenses.category TEXT for now to avoid breaking code.
    # =========================================================
    with op.batch_alter_table("expenses") as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("template_id", sa.Integer(), nullable=True))

        batch_op.create_foreign_key(
            "expenses_category_id_fkey",
            "expense_categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "expenses_template_id_fkey",
            "expense_templates",
            ["template_id"],
            ["id"],
            ondelete="SET NULL",
        )

        batch_op.create_index("ix_expenses_category_id", ["category_id"])
        batch_op.create_index("ix_expenses_template_id", ["template_id"])

    # =========================================================
    # 4) Backfill: create root categories from existing expenses.category
    # =========================================================
    op.execute(
        """
        INSERT INTO expense_categories (name, parent_id, is_active, created_at)
        SELECT DISTINCT
            e.category,
            NULL::integer,
            true,
            timezone('utc', now())
        FROM expenses e
        WHERE e.category IS NOT NULL
          AND btrim(e.category) <> ''
          AND NOT EXISTS (
            SELECT 1
            FROM expense_categories c
            WHERE c.parent_id IS NULL
              AND c.name = e.category
          );
        """
    )

    op.execute(
        """
        UPDATE expenses e
        SET category_id = c.id
        FROM expense_categories c
        WHERE c.parent_id IS NULL
          AND c.name = e.category
          AND e.category_id IS NULL;
        """
    )


def downgrade() -> None:
    # =========================================================
    # Reverse: remove expense links first
    # =========================================================
    with op.batch_alter_table("expenses") as batch_op:
        batch_op.drop_index("ix_expenses_template_id")
        batch_op.drop_index("ix_expenses_category_id")

        batch_op.drop_constraint("expenses_template_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("expenses_category_id_fkey", type_="foreignkey")

        batch_op.drop_column("template_id")
        batch_op.drop_column("category_id")

    # =========================================================
    # Drop templates then categories
    # =========================================================
    op.drop_unique_constraint("uq_expense_templates_category_name", "expense_templates", type_="unique")
    op.drop_index("ix_expense_templates_name", table_name="expense_templates")
    op.drop_index("ix_expense_templates_category_id", table_name="expense_templates")
    op.drop_table("expense_templates")

    op.drop_unique_constraint("uq_expense_categories_parent_name", "expense_categories", type_="unique")
    op.drop_index("ix_expense_categories_parent_id", table_name="expense_categories")
    op.drop_index("ix_expense_categories_name", table_name="expense_categories")
    op.drop_table("expense_categories")
