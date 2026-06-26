from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class CompanySettings(Base):
    """Enterprise profile shown to clients as a footer under order-status messages.

    Singleton: there is exactly one enterprise, so the table holds a single row
    with id = 1 (enforced by a DB CHECK, not only in Python).
    All fields are user content (NOT translated) and safe to show to clients.
    """

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    brand_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    working_hours: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (CheckConstraint("id = 1", name="ck_company_settings_singleton"),)
