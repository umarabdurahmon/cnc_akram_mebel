"""attendance verify constraints and provenance

Revision ID: 09cad9b7b635
Revises: 15393c8aa604
Create Date: 2026-06-05 19:29:22.108473

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "09cad9b7b635"
down_revision: str | None = "15393c8aa604"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("attendance_record", sa.Column("edited_by", sa.Integer(), nullable=True))
    op.add_column(
        "attendance_record",
        sa.Column("edited_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_attendance_edited_by", "attendance_record", "employee", ["edited_by"], ["id"]
    )
    op.create_check_constraint(
        "ck_attendance_checkout_after_checkin",
        "attendance_record",
        "check_out_at IS NULL OR check_out_at > check_in_at",
    )


def downgrade() -> None:
    op.drop_constraint("ck_attendance_checkout_after_checkin", "attendance_record", type_="check")
    op.drop_constraint("fk_attendance_edited_by", "attendance_record", type_="foreignkey")
    op.drop_column("attendance_record", "edited_at")
    op.drop_column("attendance_record", "edited_by")
