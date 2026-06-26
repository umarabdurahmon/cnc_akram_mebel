"""make internal_number required and unique

Revision ID: e3a1f2b8c490
Revises: 2566be302171
Create Date: 2026-06-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3a1f2b8c490"
down_revision: str | None = "2566be302171"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: normalise legacy "#N" format → strip the "#" prefix so the
    # column contains only plain numeric strings going forward.
    op.execute(r"""
        UPDATE orders
        SET internal_number = REGEXP_REPLACE(internal_number, '^#', '')
        WHERE internal_number ~ '^#[0-9]+$'
    """)

    # Step 2: assign sequential numbers to orders that still have NULL
    # internal_number, starting after the current numeric max.
    op.execute("""
        WITH max_existing AS (
            SELECT COALESCE(MAX(CAST(internal_number AS INTEGER)), 0) AS max_n
            FROM orders
            WHERE internal_number IS NOT NULL
              AND internal_number ~ '^[0-9]+$'
        ),
        nulls_ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY created_at, id) AS rn
            FROM orders
            WHERE internal_number IS NULL
        )
        UPDATE orders
        SET internal_number = LPAD(CAST((SELECT max_n FROM max_existing) + rn AS TEXT), 3, '0')
        FROM nulls_ranked
        WHERE orders.id = nulls_ranked.id
    """)

    op.create_unique_constraint("uq_orders_internal_number", "orders", ["internal_number"])
    op.alter_column("orders", "internal_number", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.alter_column("orders", "internal_number", existing_type=sa.Text(), nullable=True)
    op.drop_constraint("uq_orders_internal_number", "orders", type_="unique")
