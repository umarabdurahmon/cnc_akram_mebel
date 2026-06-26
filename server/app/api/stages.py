from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.schemas.catalog import StageCreate, StageOut, StagePatch
from app.services import catalog as catalog_svc

router = APIRouter(prefix="/stages", tags=["stages"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


@router.get("", response_model=list[StageOut])
def list_stages(
    include_inactive: bool = Query(default=False),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[StageOut]:
    if include_inactive:
        _require_manager(employee)
    stages = catalog_svc.list_stages(db, include_inactive=include_inactive)
    return [StageOut.model_validate(s) for s in stages]


@router.post("", response_model=StageOut, status_code=201)
def create_stage(
    body: StageCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> StageOut:
    _require_manager(employee)
    stage = catalog_svc.create_stage(db, body.name, body.position)
    return StageOut.model_validate(stage)


@router.delete("/{stage_id}", status_code=204)
def delete_stage(
    stage_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    try:
        catalog_svc.delete_stage(db, stage_id)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            raise HTTPException(status_code=404, detail="Stage not found")
        if msg == "still_active":
            raise HTTPException(status_code=409, detail="Archive the stage before deleting")
        raise HTTPException(status_code=409, detail="Stage is used in orders and cannot be deleted")


@router.patch("/{stage_id}", response_model=StageOut)
def patch_stage(
    stage_id: int,
    body: StagePatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> StageOut:
    _require_manager(employee)
    try:
        stage = catalog_svc.patch_stage(
            db,
            stage_id,
            name=body.name,
            position=body.position,
            is_active=body.is_active,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Stage not found")
    return StageOut.model_validate(stage)
