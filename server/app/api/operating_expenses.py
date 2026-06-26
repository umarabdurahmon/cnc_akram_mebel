from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.schemas.finance import (
    EmployeeWagesOut,
    MonthlyReportOut,
    OperatingExpenseCreate,
    OperatingExpenseOut,
    OperatingExpensePatch,
    OrdersDetailOut,
)
from app.services import finance as fin_svc

router = APIRouter(tags=["operating-expenses"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


@router.get("/operating-expenses", response_model=list[OperatingExpenseOut])
def list_operating_expenses(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[OperatingExpenseOut]:
    _require_manager(employee)
    items = fin_svc.list_operating_expenses(db)
    return [OperatingExpenseOut.model_validate(e) for e in items]


@router.post("/operating-expenses", response_model=OperatingExpenseOut, status_code=201)
def create_operating_expense(
    body: OperatingExpenseCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OperatingExpenseOut:
    _require_manager(employee)
    expense = fin_svc.add_operating_expense(
        db,
        category_id=body.category_id,
        amount=body.amount,
        spent_on=body.spent_on,
        created_by=employee.id,
        note=body.note,
    )
    return OperatingExpenseOut.model_validate(expense)


@router.patch("/operating-expenses/{expense_id}", response_model=OperatingExpenseOut)
def patch_operating_expense(
    expense_id: int,
    body: OperatingExpensePatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OperatingExpenseOut:
    _require_manager(employee)
    try:
        expense = fin_svc.patch_operating_expense(
            db, expense_id, **body.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OperatingExpenseOut.model_validate(expense)


@router.delete("/operating-expenses/{expense_id}", status_code=204)
def delete_operating_expense(
    expense_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    try:
        fin_svc.delete_operating_expense(db, expense_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports/monthly", response_model=MonthlyReportOut)
def monthly_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> MonthlyReportOut:
    _require_manager(employee)
    return fin_svc.monthly_report(db, year, month)


@router.get("/reports/employee-wages", response_model=EmployeeWagesOut)
def employee_wages_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeWagesOut:
    _require_manager(employee)
    return fin_svc.employee_wages_report(db, year, month)


@router.get("/reports/orders-detail", response_model=OrdersDetailOut)
def orders_detail_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrdersDetailOut:
    _require_manager(employee)
    return fin_svc.orders_detail_report(db, year, month)
