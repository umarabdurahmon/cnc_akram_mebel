from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.schemas.company import CompanySettingsOut, CompanySettingsUpdate
from app.services import company_settings as company_svc

router = APIRouter(prefix="/company", tags=["company"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


@router.get("", response_model=CompanySettingsOut)
def get_company(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> CompanySettingsOut:
    _require_manager(employee)
    company = company_svc.get_or_create(db)
    return CompanySettingsOut.model_validate(company)


@router.patch("", response_model=CompanySettingsOut)
def update_company(
    body: CompanySettingsUpdate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> CompanySettingsOut:
    _require_manager(employee)
    company = company_svc.update(db, body.model_dump(exclude_unset=True))
    return CompanySettingsOut.model_validate(company)
