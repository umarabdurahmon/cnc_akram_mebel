"""add delivery location to orders

Revision ID: dd29ae32014b
Revises: e3a1f2b8c490
Create Date: 2026-06-08 19:27:13.341239

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "dd29ae32014b"
down_revision: str | None = "e3a1f2b8c490"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("delivery_lat", sa.Numeric(10, 7), nullable=True))
    op.add_column("orders", sa.Column("delivery_lon", sa.Numeric(10, 7), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_lon")
    op.drop_column("orders", "delivery_lat")
