from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.models.order import Order
from app.schemas.finance import (
    ExpenseCreate,
    ExpenseOut,
    ExpensePatch,
    OrderBalanceOut,
    PaymentCreate,
    PaymentOut,
    PaymentPatch,
)
from app.services import finance as fin_svc
from app.services import order as order_svc

router = APIRouter(tags=["finance"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = order_svc.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


@router.get("/orders/{order_id}/payments", response_model=list[PaymentOut])
def list_payments(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[PaymentOut]:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    return [PaymentOut.model_validate(p) for p in fin_svc.list_payments(db, order_id)]


@router.post("/orders/{order_id}/payments", response_model=PaymentOut, status_code=201)
def create_payment(
    order_id: int,
    body: PaymentCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> PaymentOut:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    payment = fin_svc.add_payment(
        db,
        order_id=order_id,
        amount=body.amount,
        received_on=body.received_on,
        created_by=employee.id,
        note=body.note,
    )
    return PaymentOut.model_validate(payment)


@router.patch("/orders/{order_id}/payments/{payment_id}", response_model=PaymentOut)
def patch_payment(
    order_id: int,
    payment_id: int,
    body: PaymentPatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> PaymentOut:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    try:
        payment = fin_svc.patch_payment(
            db, payment_id, order_id=order_id, **body.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PaymentOut.model_validate(payment)


@router.delete("/orders/{order_id}/payments/{payment_id}", status_code=204)
def delete_payment(
    order_id: int,
    payment_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    try:
        fin_svc.delete_payment(db, payment_id, order_id=order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------


@router.get("/orders/{order_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[ExpenseOut]:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    return [ExpenseOut.model_validate(e) for e in fin_svc.list_expenses(db, order_id)]


@router.post("/orders/{order_id}/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(
    order_id: int,
    body: ExpenseCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ExpenseOut:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    try:
        expense = fin_svc.add_expense(
            db,
            order_id=order_id,
            direction=body.direction,
            category_id=body.category_id,
            amount=body.amount,
            spent_on=body.spent_on,
            created_by=employee.id,
            employee_id=body.employee_id,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExpenseOut.model_validate(expense)


@router.patch("/orders/{order_id}/expenses/{expense_id}", response_model=ExpenseOut)
def patch_expense(
    order_id: int,
    expense_id: int,
    body: ExpensePatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ExpenseOut:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    try:
        expense = fin_svc.patch_expense(
            db, expense_id, order_id=order_id, **body.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExpenseOut.model_validate(expense)


@router.delete("/orders/{order_id}/expenses/{expense_id}", status_code=204)
def delete_expense(
    order_id: int,
    expense_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    try:
        fin_svc.delete_expense(db, expense_id, order_id=order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Balance summary (optional, per тз 6)
# ---------------------------------------------------------------------------


@router.get("/orders/{order_id}/balance", response_model=OrderBalanceOut)
def order_balance(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderBalanceOut:
    _require_manager(employee)
    order = _get_order_or_404(db, order_id)
    paid = fin_svc.total_paid(db, order_id)
    expenses = fin_svc.total_expenses(db, order_id)
    receivable: Decimal | None = None
    if order.total_amount is not None:
        receivable = order.total_amount - paid
    return OrderBalanceOut(
        order_id=order_id,
        total_amount=order.total_amount,
        total_paid=paid,
        total_expenses=expenses,
        balance=paid - expenses,
        receivable=receivable,
    )
