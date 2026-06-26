from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.schemas.finance import (
    ExpenseCategoryCreate,
    ExpenseCategoryOut,
    ExpenseCategoryPatch,
)
from app.services import expense_category as cat_svc

router = APIRouter(prefix="/expense-categories", tags=["categories"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


@router.get("", response_model=list[ExpenseCategoryOut])
def list_categories(
    include_inactive: bool = Query(default=False),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[ExpenseCategoryOut]:
    _require_manager(employee)
    cats = cat_svc.list_categories(db, include_inactive=include_inactive)
    return [ExpenseCategoryOut.model_validate(c) for c in cats]


@router.post("", response_model=ExpenseCategoryOut, status_code=201)
def create_category(
    body: ExpenseCategoryCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ExpenseCategoryOut:
    _require_manager(employee)
    cat = cat_svc.create_category(db, body.name)
    return ExpenseCategoryOut.model_validate(cat)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    try:
        cat_svc.delete_category(db, category_id)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            raise HTTPException(status_code=404, detail="Category not found")
        if msg == "still_active":
            raise HTTPException(status_code=409, detail="Archive the category before deleting")
        raise HTTPException(
            status_code=409, detail="Category is used in expenses and cannot be deleted"
        )


@router.patch("/{category_id}", response_model=ExpenseCategoryOut)
def patch_category(
    category_id: int,
    body: ExpenseCategoryPatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ExpenseCategoryOut:
    _require_manager(employee)
    try:
        cat = cat_svc.patch_category(db, category_id, name=body.name, is_active=body.is_active)
    except ValueError:
        raise HTTPException(status_code=404, detail="Category not found")
    return ExpenseCategoryOut.model_validate(cat)
