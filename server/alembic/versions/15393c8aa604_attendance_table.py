"""attendance table

Revision ID: 15393c8aa604
Revises: 53d39fbff4b7
Create Date: 2026-06-05 18:45:57.419129

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "15393c8aa604"
down_revision: str | None = "53d39fbff4b7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_VS = ("not_checked", "confirmed", "discrepancy")


def upgrade() -> None:
    op.execute(
        "CREATE TYPE verification_status AS ENUM ('not_checked', 'confirmed', 'discrepancy')"
    )
    op.create_table(
        "attendance_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.DATE(), nullable=False),
        sa.Column("check_in_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("check_out_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "verification_status",
            PgEnum(*_VS, name="verification_status", create_type=False),
            server_default="not_checked",
            nullable=False,
        ),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["employee.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attendance_employee_date",
        "attendance_record",
        ["employee_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "uq_attendance_open_visit",
        "attendance_record",
        ["employee_id"],
        unique=True,
        postgresql_where="check_out_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_attendance_open_visit",
        table_name="attendance_record",
        postgresql_where="check_out_at IS NULL",
    )
    op.drop_index("ix_attendance_employee_date", table_name="attendance_record")
    op.drop_table("attendance_record")
    op.execute("DROP TYPE IF EXISTS verification_status")
