import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Date,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class FileKind(enum.StrEnum):
    drawing = "drawing"
    photo = "photo"
    other = "other"


class ProductionStage(Base):
    __tablename__ = "production_stage"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    internal_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    customer_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_stage.id"), nullable=True
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    public_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    delivery_lon: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    is_closed: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class OrderEmployee(Base):
    __tablename__ = "order_employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    can_change_status: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    attached_by: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    attached_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("order_id", "employee_id", name="uq_order_employee"),
        # Worker's order list filters by employee_id; the unique index above is
        # keyed on order_id first, so it can't serve this lookup.
        Index("ix_order_employee_employee_id", "employee_id"),
    )


class OrderFile(Base):
    __tablename__ = "order_file"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[FileKind] = mapped_column(
        SAEnum(FileKind, name="file_kind", native_enum=True), nullable=False
    )
    thumbnail_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_order_file_order_id", "order_id"),)


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    stage_id: Mapped[int] = mapped_column(ForeignKey("production_stage.id"), nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("employee.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # get_history filters by order_id and sorts by changed_at; a btree on
    # (order_id, changed_at) serves both (scanned backwards for DESC).
    __table_args__ = (Index("ix_order_status_history_order_id", "order_id", "changed_at"),)
