from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeePatch

router = APIRouter(prefix="/employees", tags=["employees"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


@router.get("", response_model=list[EmployeeOut])
def list_employees(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[EmployeeOut]:
    _require_manager(employee)
    rows = (
        db.execute(
            select(Employee)
            .where(Employee.role == EmployeeRole.worker)
            .order_by(Employee.full_name)
        )
        .scalars()
        .all()
    )
    return [EmployeeOut.model_validate(e) for e in rows]


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(
    body: EmployeeCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    _require_manager(employee)
    existing = db.scalar(select(Employee).where(Employee.telegram_id == body.telegram_id))
    if existing:
        if existing.role == EmployeeRole.manager:
            raise HTTPException(status_code=409, detail="This Telegram account is the manager")
        existing.full_name = body.full_name
        existing.language = body.language
        existing.position = body.position
        existing.is_active = True
        return EmployeeOut.model_validate(existing)
    emp = Employee(
        telegram_id=body.telegram_id,
        full_name=body.full_name,
        role=EmployeeRole.worker,
        language=body.language,
        position=body.position,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return EmployeeOut.model_validate(emp)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    target = db.get(Employee, employee_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if target.role == EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Cannot delete manager account")
    try:
        db.delete(target)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Employee has related records. Deactivate instead.",
        )


@router.patch("/{employee_id}", response_model=EmployeeOut)
def patch_employee(
    employee_id: int,
    body: EmployeePatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    _require_manager(employee)
    target = db.get(Employee, employee_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    db.flush()
    return EmployeeOut.model_validate(target)
