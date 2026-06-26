"""Finance schemas.

MoneyDecimal serialises Decimal as a JSON string to preserve exactness —
never as float (which would silently lose precision for values like 0.1 + 0.2).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.models.finance import ExpenseDirection

# Decimal → string in JSON; stays Decimal in Python. No float coercion.
MoneyDecimal = Annotated[
    Decimal,
    PlainSerializer(str, return_type=str, when_used="json"),
]


class ExpenseCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
    created_at: datetime


class ExpenseCategoryCreate(BaseModel):
    name: str


class ExpenseCategoryPatch(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    amount: MoneyDecimal
    received_on: date
    note: str | None
    created_by: int
    created_at: datetime


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    received_on: date
    note: str | None = Field(default=None, max_length=500)


class PaymentPatch(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    received_on: date | None = None
    note: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    direction: ExpenseDirection
    category_id: int
    employee_id: int | None
    amount: MoneyDecimal
    spent_on: date
    note: str | None
    created_by: int
    created_at: datetime


class ExpenseCreate(BaseModel):
    direction: ExpenseDirection
    category_id: int
    employee_id: int | None = None
    amount: Decimal = Field(gt=0)
    spent_on: date
    note: str | None = Field(default=None, max_length=500)


class ExpensePatch(BaseModel):
    direction: ExpenseDirection | None = None
    category_id: int | None = None
    employee_id: int | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    spent_on: date | None = None
    note: str | None = None


class OrderBalanceOut(BaseModel):
    order_id: int
    total_amount: MoneyDecimal | None
    total_paid: MoneyDecimal
    total_expenses: MoneyDecimal
    balance: MoneyDecimal  # total_paid - total_expenses (money received minus money spent)
    receivable: MoneyDecimal | None  # total_amount - total_paid (client still owes)


class OperatingExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    amount: MoneyDecimal
    spent_on: date
    note: str | None
    created_by: int
    created_at: datetime


class OperatingExpenseCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(gt=0)
    spent_on: date
    note: str | None = Field(default=None, max_length=500)


class OperatingExpensePatch(BaseModel):
    category_id: int | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    spent_on: date | None = None
    note: str | None = None


class CategoryBreakdownItem(BaseModel):
    category_id: int
    category_name: str
    amount: MoneyDecimal


class MonthlyReportOut(BaseModel):
    year: int
    month: int
    revenue: MoneyDecimal
    order_expenses: MoneyDecimal
    operating_expenses: MoneyDecimal
    total_expenses: MoneyDecimal
    profit: MoneyDecimal
    breakdown: list[CategoryBreakdownItem]


# ── Employee wages report ────────────────────────────────────────────────────


class EmployeeWageExpense(BaseModel):
    order_id: int
    order_title: str
    order_internal_number: str | None
    category_name: str
    amount: MoneyDecimal
    spent_on: date
    note: str | None


class EmployeeWageItem(BaseModel):
    employee_id: int
    full_name: str
    total: MoneyDecimal
    expenses: list[EmployeeWageExpense]


class EmployeeWagesOut(BaseModel):
    year: int
    month: int
    total: MoneyDecimal
    employees: list[EmployeeWageItem]


# ── Orders detail report ─────────────────────────────────────────────────────


class OrderDetailItem(BaseModel):
    order_id: int
    title: str
    customer_name: str
    internal_number: str | None
    total_amount: MoneyDecimal | None
    paid_in_month: MoneyDecimal
    expenses_in_month: MoneyDecimal
    net_in_month: MoneyDecimal
    # Total received from client across all time (not just this month) — for receivable calc
    total_paid_all_time: MoneyDecimal


class OrdersDetailOut(BaseModel):
    year: int
    month: int
    orders: list[OrderDetailItem]
