from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeLanguage
from app.schemas.employee import EmployeeOut

router = APIRouter()


class LanguagePatch(BaseModel):
    language: EmployeeLanguage


@router.get("/me", response_model=EmployeeOut)
def me(employee: Employee = Depends(get_current_employee)) -> Employee:
    return employee


@router.patch("/me/language", response_model=EmployeeOut)
def set_language(
    body: LanguagePatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> Employee:
    employee.language = body.language
    db.flush()
    return employee
