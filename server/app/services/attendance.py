from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attendance import AttendanceRecord, VerificationStatus
from app.models.employee import Employee

# Double check-out guard: ignore a second check-in within this window
_DOUBLE_TAP_SECONDS = 5


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _work_date_from_ts(ts: datetime) -> date:
    """Convert a UTC (or tz-aware) timestamp to local work_date in shop timezone."""
    return ts.astimezone(ZoneInfo(settings.shop_tz)).date()


def _get_open_visit(db: Session, employee_id: int) -> AttendanceRecord | None:
    return db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.employee_id == employee_id)
        .where(AttendanceRecord.check_out_at.is_(None))
    ).scalar_one_or_none()


def toggle(db: Session, employee_id: int) -> tuple[bool, AttendanceRecord]:
    """Toggle check-in/check-out.

    Returns (is_open, record):
    - (True, record)  when a new visit was opened
    - (False, record) when the open visit was closed
    - (False, record) when double-tap check-out was suppressed
    """
    now = _now_utc()

    open_visit = _get_open_visit(db, employee_id)
    if open_visit is not None:
        open_visit.check_out_at = now
        open_visit.updated_at = now
        db.flush()
        return False, open_visit

    # Double check-out protection: if last closed visit ended within the guard window,
    # treat this as an accidental second tap and return it instead of opening a new visit.
    last_visit: AttendanceRecord | None = db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.employee_id == employee_id)
        .where(AttendanceRecord.check_out_at.isnot(None))
        .order_by(AttendanceRecord.check_out_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if last_visit is not None and last_visit.check_out_at is not None:
        checkout_ts = last_visit.check_out_at
        if checkout_ts.tzinfo is None:
            checkout_ts = checkout_ts.replace(tzinfo=UTC)
        if (now - checkout_ts).total_seconds() < _DOUBLE_TAP_SECONDS:
            return False, last_visit

    # Create new open visit; guard against race condition via partial unique index.
    record = AttendanceRecord(
        employee_id=employee_id,
        work_date=_work_date_from_ts(now),
        check_in_at=now,
    )
    db.add(record)
    sp = db.begin_nested()
    try:
        db.flush()
        sp.commit()
    except IntegrityError:
        sp.rollback()
        existing = _get_open_visit(db, employee_id)
        assert existing is not None
        return True, existing

    return True, record


def hours_for_day(db: Session, employee_id: int, day: date) -> float:
    """Sum of closed-visit durations (hours) for the given employee on the given day."""
    rows = (
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == employee_id)
            .where(AttendanceRecord.work_date == day)
            .where(AttendanceRecord.check_out_at.isnot(None))
        )
        .scalars()
        .all()
    )

    total = 0.0
    for r in rows:
        delta = r.check_out_at - r.check_in_at  # type: ignore[operator]
        total += delta.total_seconds() / 3600
    return round(total, 4)


def hours_for_period(db: Session, employee_id: int, from_date: date, to_date: date) -> float:
    """Sum of closed-visit durations (hours) for the given employee over a date range."""
    rows = (
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == employee_id)
            .where(AttendanceRecord.work_date >= from_date)
            .where(AttendanceRecord.work_date <= to_date)
            .where(AttendanceRecord.check_out_at.isnot(None))
        )
        .scalars()
        .all()
    )

    total = 0.0
    for r in rows:
        delta = r.check_out_at - r.check_in_at  # type: ignore[operator]
        total += delta.total_seconds() / 3600
    return round(total, 4)


def get_visits_for_day(db: Session, employee_id: int, day: date) -> list[AttendanceRecord]:
    return list(
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == employee_id)
            .where(AttendanceRecord.work_date == day)
            .order_by(AttendanceRecord.check_in_at)
        )
        .scalars()
        .all()
    )


def verify_record(
    db: Session,
    record_id: int,
    verifier_id: int,
    status: VerificationStatus,
) -> AttendanceRecord:
    record = db.get(AttendanceRecord, record_id)
    if record is None:
        raise ValueError("attendance record not found")
    now = _now_utc()
    record.verification_status = status
    record.verified_by = verifier_id
    record.verified_at = now
    record.updated_at = now
    db.flush()
    return record


_UNSET = object()


def patch_record(
    db: Session,
    record_id: int,
    editor_id: int,
    *,
    check_in_at: datetime | object = _UNSET,
    check_out_at: datetime | None | object = _UNSET,
    note: str | None | object = _UNSET,
) -> AttendanceRecord:
    """Patch an attendance record. Only keyword-args that are NOT _UNSET are applied."""
    record = db.get(AttendanceRecord, record_id)
    if record is None:
        raise ValueError("attendance record not found")

    if check_in_at is not _UNSET:
        record.check_in_at = check_in_at  # type: ignore[assignment]
        record.work_date = _work_date_from_ts(check_in_at)  # type: ignore[arg-type]

    if check_out_at is not _UNSET:
        record.check_out_at = check_out_at  # type: ignore[assignment]

    if note is not _UNSET:
        record.note = note  # type: ignore[assignment]

    effective_cout = record.check_out_at
    if effective_cout is not None and effective_cout <= record.check_in_at:
        raise ValueError("check_out_at must be after check_in_at")

    now = _now_utc()
    record.edited_by = editor_id
    record.edited_at = now
    record.updated_at = now

    sp = db.begin_nested()
    try:
        db.flush()
        sp.commit()
    except IntegrityError:
        sp.rollback()
        raise

    return record


def rollover_midnight_visits(db: Session) -> int:
    """Close stale open visits at midnight and reopen them on the new day.

    Called at midnight shop_tz. Finds every open visit whose work_date is before
    today (i.e. the employee never checked out), closes it at the current UTC
    instant (which corresponds to midnight in shop_tz), and opens a fresh visit
    for the new day at the same instant.

    Returns the number of employees rolled over.
    """
    midnight_utc = _now_utc()
    today = _work_date_from_ts(midnight_utc)

    stale = (
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.check_out_at.is_(None))
            .where(AttendanceRecord.work_date < today)
        )
        .scalars()
        .all()
    )

    for visit in stale:
        visit.check_out_at = midnight_utc
        visit.updated_at = midnight_utc
        db.add(
            AttendanceRecord(
                employee_id=visit.employee_id,
                work_date=today,
                check_in_at=midnight_utc,
            )
        )

    db.flush()
    return len(stale)


def get_discrepancies(db: Session, from_date: date, to_date: date) -> list[tuple[Employee, int]]:
    rows = db.execute(
        select(Employee, func.count(AttendanceRecord.id).label("cnt"))
        .join(AttendanceRecord, AttendanceRecord.employee_id == Employee.id)
        .where(AttendanceRecord.verification_status == VerificationStatus.discrepancy)
        .where(AttendanceRecord.work_date >= from_date)
        .where(AttendanceRecord.work_date <= to_date)
        .group_by(Employee.id)
        .order_by(func.count(AttendanceRecord.id).desc())
    ).all()
    return [(emp, cnt) for emp, cnt in rows]
