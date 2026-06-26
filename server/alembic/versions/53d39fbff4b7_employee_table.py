"""employee table

Revision ID: 53d39fbff4b7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 18:03:45.147638

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "53d39fbff4b7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Создаём Postgres ENUM-типы до таблицы, чтобы downgrade мог их дропнуть явно.
    # PgEnum(create_type=False) в колонках — тип уже создан выше, не трогаем снова.
    op.execute("CREATE TYPE employee_role AS ENUM ('worker', 'manager')")
    op.execute("CREATE TYPE employee_language AS ENUM ('ru', 'uz')")
    op.create_table(
        "employee",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column(
            "role",
            PgEnum("worker", "manager", name="employee_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "language",
            PgEnum("ru", "uz", name="employee_language", create_type=False),
            nullable=False,
        ),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("employee")
    op.execute("DROP TYPE IF EXISTS employee_role")
    op.execute("DROP TYPE IF EXISTS employee_language")
