import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, CheckConstraint, Date, ForeignKey, Index, Numeric, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class ExpenseDirection(enum.StrEnum):
    to_employee = "to_employee"
    general = "general"


class OrderPayment(Base):
    __tablename__ = "order_payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Per-order payment totals (total_paid, bulk_total_paid, list_payments).
        Index("ix_order_payment_order_id", "order_id"),
        # Monthly revenue range scan (monthly_report, orders_detail_report).
        Index("ix_order_payment_received_on", "received_on"),
    )


class OrderExpense(Base):
    __tablename__ = "order_expense"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    direction: Mapped[ExpenseDirection] = mapped_column(
        SAEnum(ExpenseDirection, name="expense_direction", native_enum=True), nullable=False
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("expense_category.id"), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # to_employee requires employee_id; general forbids it
        CheckConstraint(
            "(direction = 'to_employee' AND employee_id IS NOT NULL)"
            " OR (direction = 'general' AND employee_id IS NULL)",
            name="ck_expense_direction_employee",
        ),
        # Per-order expense totals (total_expenses, list_expenses).
        Index("ix_order_expense_order_id", "order_id"),
        # Monthly expense range scan over all directions (monthly_report).
        Index("ix_order_expense_spent_on", "spent_on"),
        # employee_wages_report: only to_employee rows, by date. Partial index
        # keeps it small and selective.
        Index(
            "ix_order_expense_wage_spent_on",
            "spent_on",
            postgresql_where=text("direction = 'to_employee'"),
        ),
    )


class OperatingExpense(Base):
    """Enterprise-level expense not tied to a specific order (rent, utilities, etc.)."""

    __tablename__ = "operating_expense"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("expense_category.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Monthly operating-expense range scan (monthly_report).
    __table_args__ = (Index("ix_operating_expense_spent_on", "spent_on"),)
