from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.attendance import VerificationStatus


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    work_date: date
    check_in_at: datetime
    check_out_at: datetime | None
    verification_status: VerificationStatus
    verified_by: int | None
    verified_at: datetime | None
    note: str | None
    edited_by: int | None
    edited_at: datetime | None


class VerifyRequest(BaseModel):
    status: VerificationStatus


class AttendancePatch(BaseModel):
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    note: str | None = None


class DiscrepancyCount(BaseModel):
    employee_id: int
    full_name: str
    count: int


class DiscrepanciesResponse(BaseModel):
    from_date: date
    to_date: date
    employees: list[DiscrepancyCount]


class ToggleResponse(BaseModel):
    open: bool
    visit: AttendanceRecordOut
    today_hours: float


class TodayResponse(BaseModel):
    visits: list[AttendanceRecordOut]
    open_visit: AttendanceRecordOut | None
    today_hours: float


class EmployeeAttendanceSummary(BaseModel):
    employee_id: int
    full_name: str
    visits: list[AttendanceRecordOut]
    open_visit: AttendanceRecordOut | None
    total_hours: float


class SummaryResponse(BaseModel):
    date: date
    employees: list[EmployeeAttendanceSummary]


class EmployeeStatus(BaseModel):
    employee_id: int
    full_name: str
    open_since: datetime | None


class EmployeesStatusResponse(BaseModel):
    date: date
    employees: list[EmployeeStatus]


class DaySummaryItem(BaseModel):
    date: date
    total_hours: float
    visit_count: int
    has_discrepancy: bool
    has_open_visit: bool


class MonthResponse(BaseModel):
    employee_id: int
    year: int
    month: int
    days: list[DaySummaryItem]


class EmployeeDayResponse(BaseModel):
    employee_id: int
    full_name: str
    date: date
    visits: list[AttendanceRecordOut]
    open_visit: AttendanceRecordOut | None
    total_hours: float
