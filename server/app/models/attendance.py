import enum
from datetime import date, datetime

from sqlalchemy import DATE, TIMESTAMP, CheckConstraint, ForeignKey, Index, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class VerificationStatus(enum.StrEnum):
    not_checked = "not_checked"
    confirmed = "confirmed"
    discrepancy = "discrepancy"


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(DATE, nullable=False)
    check_in_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    check_out_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status", native_enum=True),
        nullable=False,
        server_default="not_checked",
    )
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_by: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_attendance_open_visit",
            "employee_id",
            unique=True,
            postgresql_where="check_out_at IS NULL",
        ),
        Index("ix_attendance_employee_date", "employee_id", "work_date"),
        CheckConstraint(
            "check_out_at IS NULL OR check_out_at > check_in_at",
            name="ck_attendance_checkout_after_checkin",
        ),
    )
