import enum
from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class EmployeeRole(enum.StrEnum):
    worker = "worker"
    manager = "manager"


class EmployeeLanguage(enum.StrEnum):
    ru = "ru"
    uz = "uz"


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str]
    role: Mapped[EmployeeRole] = mapped_column(
        SAEnum(EmployeeRole, name="employee_role", native_enum=True),
        nullable=False,
    )
    language: Mapped[EmployeeLanguage] = mapped_column(
        SAEnum(EmployeeLanguage, name="employee_language", native_enum=True),
        nullable=False,
    )
    position: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
