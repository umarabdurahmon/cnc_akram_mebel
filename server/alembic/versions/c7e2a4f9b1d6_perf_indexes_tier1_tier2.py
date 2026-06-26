"""perf indexes: FK hot paths (tier 1) and report date ranges (tier 2)

Adds covering indexes for the query patterns in app.services:

Tier 1 — per-order child lookups (order detail screen, order list):
  order_payment(order_id), order_expense(order_id),
  order_file(order_id), order_status_history(order_id, changed_at),
  order_employee(employee_id).

Tier 2 — monthly report date-range scans:
  order_payment(received_on), order_expense(spent_on),
  operating_expense(spent_on), and a partial order_expense(spent_on)
  WHERE direction = 'to_employee' for the wages report.

Revision ID: c7e2a4f9b1d6
Revises: dd29ae32014b
Create Date: 2026-06-08 20:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7e2a4f9b1d6"
down_revision: str | None = "dd29ae32014b"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # --- Tier 1: FK / per-order hot paths ---------------------------------
    op.create_index("ix_order_payment_order_id", "order_payment", ["order_id"])
    op.create_index("ix_order_expense_order_id", "order_expense", ["order_id"])
    op.create_index("ix_order_file_order_id", "order_file", ["order_id"])
    op.create_index(
        "ix_order_status_history_order_id",
        "order_status_history",
        ["order_id", "changed_at"],
    )
    op.create_index("ix_order_employee_employee_id", "order_employee", ["employee_id"])

    # --- Tier 2: report date-range scans ----------------------------------
    op.create_index("ix_order_payment_received_on", "order_payment", ["received_on"])
    op.create_index("ix_order_expense_spent_on", "order_expense", ["spent_on"])
    op.create_index("ix_operating_expense_spent_on", "operating_expense", ["spent_on"])
    op.create_index(
        "ix_order_expense_wage_spent_on",
        "order_expense",
        ["spent_on"],
        postgresql_where="direction = 'to_employee'",
    )


def downgrade() -> None:
    op.drop_index("ix_order_expense_wage_spent_on", table_name="order_expense")
    op.drop_index("ix_operating_expense_spent_on", table_name="operating_expense")
    op.drop_index("ix_order_expense_spent_on", table_name="order_expense")
    op.drop_index("ix_order_payment_received_on", table_name="order_payment")

    op.drop_index("ix_order_employee_employee_id", table_name="order_employee")
    op.drop_index("ix_order_status_history_order_id", table_name="order_status_history")
    op.drop_index("ix_order_file_order_id", table_name="order_file")
    op.drop_index("ix_order_expense_order_id", table_name="order_expense")
    op.drop_index("ix_order_payment_order_id", table_name="order_payment")
