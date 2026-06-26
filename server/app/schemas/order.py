from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    stage_id: int
    changed_by: int
    changed_at: datetime
    comment: str | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_code: str
    internal_number: str
    customer_name: str
    customer_contact: str | None
    customer_chat_id: int | None
    title: str
    description: str | None
    current_stage_id: int | None
    current_stage_name: str | None = None  # resolved server-side for convenience
    deadline: date | None
    total_amount: Decimal | None
    public_note: str | None
    delivery_lat: float | None = None
    delivery_lon: float | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_closed: bool = False
    closed_at: datetime | None = None
    # Populated per-request by the API layer (not an ORM column)
    can_change_status_for_me: bool = False
    total_paid: Decimal = Decimal("0.00")
    balance: Decimal | None = None  # total_amount - total_paid; None if total_amount unknown


class OrderCreate(BaseModel):
    customer_name: str = Field(max_length=255)
    title: str = Field(max_length=500)
    customer_contact: str | None = Field(default=None, max_length=100)
    customer_chat_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    current_stage_id: int | None = None
    deadline: date | None = None
    total_amount: Decimal | None = Field(default=None, gt=0)
    public_note: str | None = Field(default=None, max_length=2000)
    stage_comment: str | None = Field(default=None, max_length=1000)
    delivery_lat: float | None = None
    delivery_lon: float | None = None


class OrderPatch(BaseModel):
    customer_name: str | None = Field(default=None, max_length=255)
    customer_contact: str | None = Field(default=None, max_length=100)
    customer_chat_id: int | None = None
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    deadline: date | None = None
    total_amount: Decimal | None = Field(default=None, gt=0)
    public_note: str | None = Field(default=None, max_length=2000)
    delivery_lat: float | None = None
    delivery_lon: float | None = None


class StageChangeRequest(BaseModel):
    stage_id: int
    comment: str | None = Field(default=None, max_length=1000)


class AttachRequest(BaseModel):
    employee_id: int
    can_change_status: bool = False


class OrderEmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    employee_id: int
    can_change_status: bool
    attached_by: int | None
    attached_at: datetime
