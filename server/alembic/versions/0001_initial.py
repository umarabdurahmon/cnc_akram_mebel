"""initial

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-04 00:00:00.000000

Первая пустая ревизия — проверяет, что миграционный стек работает.
Таблицы появятся в Сессии 1 (модель employee).
"""

from collections.abc import Sequence

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
