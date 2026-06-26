"""company settings (enterprise profile footer)

Revision ID: f4a8c1e9d2b7
Revises: c7e2a4f9b1d6
Create Date: 2026-06-08 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4a8c1e9d2b7"
down_revision: str | None = "c7e2a4f9b1d6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("brand_name", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("working_hours", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("footer_note", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_company_settings_singleton"),
    )


def downgrade() -> None:
    op.drop_table("company_settings")
