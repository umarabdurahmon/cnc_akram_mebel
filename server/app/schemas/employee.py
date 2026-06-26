from pydantic import BaseModel, ConfigDict

from app.models.employee import EmployeeLanguage, EmployeeRole


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    full_name: str
    role: EmployeeRole
    language: EmployeeLanguage
    position: str | None
    is_active: bool


class EmployeeCreate(BaseModel):
    telegram_id: int
    full_name: str
    language: EmployeeLanguage = EmployeeLanguage.ru
    position: str | None = None


class EmployeePatch(BaseModel):
    full_name: str | None = None
    role: EmployeeRole | None = None
    language: EmployeeLanguage | None = None
    position: str | None = None
    is_active: bool | None = None
