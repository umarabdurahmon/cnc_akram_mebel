from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.core.config import settings
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.schemas.attendance import (
    AttendancePatch,
    AttendanceRecordOut,
    DaySummaryItem,
    DiscrepanciesResponse,
    DiscrepancyCount,
    EmployeeAttendanceSummary,
    EmployeeDayResponse,
    EmployeesStatusResponse,
    EmployeeStatus,
    MonthResponse,
    SummaryResponse,
    TodayResponse,
    ToggleResponse,
    VerifyRequest,
)
from app.services import attendance as attendance_svc

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _today_in_shop_tz() -> date:
    from datetime import datetime

    return datetime.now(tz=ZoneInfo(settings.shop_tz)).date()


@router.post("/toggle", response_model=ToggleResponse)
def toggle(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> ToggleResponse:
    is_open, visit = attendance_svc.toggle(db, employee.id)
    today = _today_in_shop_tz()
    today_hours = attendance_svc.hours_for_day(db, employee.id, today)
    return ToggleResponse(
        open=is_open,
        visit=AttendanceRecordOut.model_validate(visit),
        today_hours=today_hours,
    )


@router.get("/me/today", response_model=TodayResponse)
def me_today(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> TodayResponse:
    today = _today_in_shop_tz()
    all_visits = attendance_svc.get_visits_for_day(db, employee.id, today)
    open_visit = next((v for v in all_visits if v.check_out_at is None), None)
    closed_visits = [v for v in all_visits if v.check_out_at is not None]
    today_hours = attendance_svc.hours_for_day(db, employee.id, today)
    return TodayResponse(
        visits=[AttendanceRecordOut.model_validate(v) for v in closed_visits],
        open_visit=AttendanceRecordOut.model_validate(open_visit) if open_visit else None,
        today_hours=today_hours,
    )


@router.get("/me/day", response_model=TodayResponse)
def me_day(
    date: date = Query(...),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> TodayResponse:
    all_visits = attendance_svc.get_visits_for_day(db, employee.id, date)
    open_visit = next((v for v in all_visits if v.check_out_at is None), None)
    closed_visits = [v for v in all_visits if v.check_out_at is not None]
    hours = attendance_svc.hours_for_day(db, employee.id, date)
    return TodayResponse(
        visits=[AttendanceRecordOut.model_validate(v) for v in closed_visits],
        open_visit=AttendanceRecordOut.model_validate(open_visit) if open_visit else None,
        today_hours=hours,
    )


@router.get("/summary", response_model=SummaryResponse)
def summary(
    day: date = Query(default=None),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")

    if day is None:
        day = _today_in_shop_tz()

    from app.models.attendance import AttendanceRecord
    from app.models.employee import Employee as EmployeeModel

    # Fetch all employees who have visits on this day
    rows = (
        db.execute(
            select(EmployeeModel).where(
                EmployeeModel.id.in_(
                    select(AttendanceRecord.employee_id)
                    .where(AttendanceRecord.work_date == day)
                    .distinct()
                )
            )
        )
        .scalars()
        .all()
    )

    result: list[EmployeeAttendanceSummary] = []
    for emp in rows:
        visits = attendance_svc.get_visits_for_day(db, emp.id, day)
        open_visit = next((v for v in visits if v.check_out_at is None), None)
        closed_visits = [v for v in visits if v.check_out_at is not None]
        total_hours = attendance_svc.hours_for_day(db, emp.id, day)
        result.append(
            EmployeeAttendanceSummary(
                employee_id=emp.id,
                full_name=emp.full_name,
                visits=[AttendanceRecordOut.model_validate(v) for v in closed_visits],
                open_visit=AttendanceRecordOut.model_validate(open_visit) if open_visit else None,
                total_hours=total_hours,
            )
        )

    return SummaryResponse(date=day, employees=result)


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


@router.post("/{record_id}/verify", response_model=AttendanceRecordOut)
def verify_record(
    record_id: int,
    body: VerifyRequest,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> AttendanceRecordOut:
    _require_manager(employee)
    try:
        record = attendance_svc.verify_record(db, record_id, employee.id, body.status)
    except ValueError:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return AttendanceRecordOut.model_validate(record)


@router.patch("/{record_id}", response_model=AttendanceRecordOut)
def patch_record(
    record_id: int,
    body: AttendancePatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> AttendanceRecordOut:
    _require_manager(employee)

    kwargs: dict[str, object] = {}
    if "check_in_at" in body.model_fields_set:
        kwargs["check_in_at"] = body.check_in_at
    if "check_out_at" in body.model_fields_set:
        kwargs["check_out_at"] = body.check_out_at
    if "note" in body.model_fields_set:
        kwargs["note"] = body.note

    try:
        record = attendance_svc.patch_record(db, record_id, employee.id, **kwargs)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail="Attendance record not found")
        raise HTTPException(status_code=400, detail=msg)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Cannot reopen visit: employee already has another open visit",
        )
    return AttendanceRecordOut.model_validate(record)


@router.get("/employees-status", response_model=EmployeesStatusResponse)
def employees_status(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeesStatusResponse:
    """All active workers + whether they currently have an open visit."""
    _require_manager(employee)
    from app.models.attendance import AttendanceRecord

    workers = (
        db.execute(
            select(Employee)
            .where(Employee.role == EmployeeRole.worker)
            .where(Employee.is_active.is_(True))
            .order_by(Employee.full_name)
        )
        .scalars()
        .all()
    )

    result: list[EmployeeStatus] = []
    for w in workers:
        open_visit = db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == w.id)
            .where(AttendanceRecord.check_out_at.is_(None))
            .where(AttendanceRecord.work_date == _today_in_shop_tz())
        ).scalar_one_or_none()
        result.append(
            EmployeeStatus(
                employee_id=w.id,
                full_name=w.full_name,
                open_since=open_visit.check_in_at if open_visit else None,
            )
        )

    return EmployeesStatusResponse(date=_today_in_shop_tz(), employees=result)


@router.get("/employee/{employee_id}/month", response_model=MonthResponse)
def employee_month(
    employee_id: int,
    year: int = Query(...),
    month: int = Query(...),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> MonthResponse:
    """Daily attendance summary for one employee over a calendar month."""
    _require_manager(employee)
    from calendar import monthrange
    from collections import defaultdict
    from datetime import date as date_cls

    from app.models.attendance import AttendanceRecord, VerificationStatus

    _, days_in_month = monthrange(year, month)
    from_date = date_cls(year, month, 1)
    to_date = date_cls(year, month, days_in_month)

    records = (
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == employee_id)
            .where(AttendanceRecord.work_date >= from_date)
            .where(AttendanceRecord.work_date <= to_date)
            .order_by(AttendanceRecord.work_date, AttendanceRecord.check_in_at)
        )
        .scalars()
        .all()
    )

    by_day: dict[date_cls, list[AttendanceRecord]] = defaultdict(list)
    for r in records:
        by_day[r.work_date].append(r)

    days: list[DaySummaryItem] = []
    for day_date, day_records in sorted(by_day.items()):
        closed = [r for r in day_records if r.check_out_at is not None]
        open_r = next((r for r in day_records if r.check_out_at is None), None)
        total_hours = sum(
            (r.check_out_at - r.check_in_at).total_seconds() / 3600  # type: ignore[operator, misc]
            for r in closed
        )
        days.append(
            DaySummaryItem(
                date=day_date,
                total_hours=round(total_hours, 4),
                visit_count=len(day_records),
                has_discrepancy=any(
                    r.verification_status == VerificationStatus.discrepancy for r in day_records
                ),
                has_open_visit=open_r is not None,
            )
        )

    return MonthResponse(employee_id=employee_id, year=year, month=month, days=days)


@router.get("/employee/{employee_id}/day", response_model=EmployeeDayResponse)
def employee_day(
    employee_id: int,
    date: date = Query(...),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> EmployeeDayResponse:
    """All visit records for one employee on a specific day."""
    _require_manager(employee)
    target = db.get(Employee, employee_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    visits = attendance_svc.get_visits_for_day(db, employee_id, date)
    open_visit = next((v for v in visits if v.check_out_at is None), None)
    closed_visits = [v for v in visits if v.check_out_at is not None]
    total_hours = attendance_svc.hours_for_day(db, employee_id, date)

    return EmployeeDayResponse(
        employee_id=employee_id,
        full_name=target.full_name,
        date=date,
        visits=[AttendanceRecordOut.model_validate(v) for v in closed_visits],
        open_visit=AttendanceRecordOut.model_validate(open_visit) if open_visit else None,
        total_hours=total_hours,
    )


@router.get("/discrepancies", response_model=DiscrepanciesResponse)
def discrepancies(
    from_date: date = Query(...),
    to_date: date = Query(...),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> DiscrepanciesResponse:
    _require_manager(employee)
    rows = attendance_svc.get_discrepancies(db, from_date, to_date)
    return DiscrepanciesResponse(
        from_date=from_date,
        to_date=to_date,
        employees=[
            DiscrepancyCount(employee_id=emp.id, full_name=emp.full_name, count=cnt)
            for emp, cnt in rows
        ],
    )
