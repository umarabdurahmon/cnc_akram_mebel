"""Invariant tests for attendance module.

All tests run against real Postgres (furniture_test), each in a rolled-back transaction.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.services import attendance as svc
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_employee(
    db: Session,
    *,
    role: EmployeeRole = EmployeeRole.worker,
    telegram_id: int = 999_100_001,
) -> Employee:
    emp = Employee(
        telegram_id=telegram_id,
        full_name="Attendance Test",
        role=role,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


def _insert_open_visit(
    db: Session,
    employee_id: int,
    check_in_at: datetime | None = None,
) -> AttendanceRecord:
    now = check_in_at or datetime.now(tz=UTC)
    r = AttendanceRecord(
        employee_id=employee_id,
        work_date=now.date(),
        check_in_at=now,
    )
    db.add(r)
    db.flush()
    return r


# ---------------------------------------------------------------------------
# 1. Partial unique index rejects two open visits for the same employee
# ---------------------------------------------------------------------------


def test_two_open_visits_raises_integrity_error(db: Session) -> None:
    emp = _make_employee(db)
    _insert_open_visit(db, emp.id)
    with pytest.raises(IntegrityError):
        sp = db.begin_nested()
        try:
            _insert_open_visit(db, emp.id)
            db.flush()
        except IntegrityError:
            sp.rollback()
            raise


# ---------------------------------------------------------------------------
# 2. Double check-in via toggle is idempotent (treated as check-out)
# ---------------------------------------------------------------------------


def test_double_checkin_is_idempotent(db: Session) -> None:
    from sqlalchemy import select

    emp = _make_employee(db)
    is_open1, _visit1 = svc.toggle(db, emp.id)
    assert is_open1 is True

    # Second toggle closes the open visit — exactly one record, closed
    svc.toggle(db, emp.id)
    records = list(
        db.execute(select(AttendanceRecord).where(AttendanceRecord.employee_id == emp.id))
        .scalars()
        .all()
    )
    assert len(records) == 1
    assert records[0].check_out_at is not None


# ---------------------------------------------------------------------------
# 3. Check-in then check-out closes the visit and records duration
# ---------------------------------------------------------------------------


def test_checkin_then_checkout(db: Session) -> None:
    emp = _make_employee(db, telegram_id=999_100_002)
    is_open, visit = svc.toggle(db, emp.id)
    assert is_open is True
    assert visit.check_out_at is None

    is_open2, closed = svc.toggle(db, emp.id)
    assert is_open2 is False
    assert closed.check_out_at is not None
    assert closed.check_out_at > closed.check_in_at


# ---------------------------------------------------------------------------
# 4. Double check-out does not open a new visit (5-second guard)
# ---------------------------------------------------------------------------


def test_double_checkout_does_not_open_new_visit(db: Session) -> None:
    from sqlalchemy import select

    emp = _make_employee(db, telegram_id=999_100_003)
    svc.toggle(db, emp.id)  # check-in
    svc.toggle(db, emp.id)  # check-out

    # Immediately tap again — within the 5-second guard window
    is_open, _visit = svc.toggle(db, emp.id)
    assert is_open is False

    records = list(
        db.execute(select(AttendanceRecord).where(AttendanceRecord.employee_id == emp.id))
        .scalars()
        .all()
    )
    # Only one record — no second open visit created
    assert len(records) == 1


# ---------------------------------------------------------------------------
# 5. hours_for_day sums closed visits; open visit is excluded
# ---------------------------------------------------------------------------


def test_hours_for_day_excludes_open_visit(db: Session) -> None:
    emp = _make_employee(db, telegram_id=999_100_004)
    today = date.today()

    t0 = datetime(today.year, today.month, today.day, 8, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(hours=2)
    r1 = AttendanceRecord(employee_id=emp.id, work_date=today, check_in_at=t0, check_out_at=t1)
    db.add(r1)

    # Open visit — must not count
    t2 = t0 + timedelta(hours=3)
    r2 = AttendanceRecord(employee_id=emp.id, work_date=today, check_in_at=t2)
    db.add(r2)
    db.flush()

    hours = svc.hours_for_day(db, emp.id, today)
    assert abs(hours - 2.0) < 0.001


# ---------------------------------------------------------------------------
# 6. work_date is determined by Asia/Tashkent, not UTC
# ---------------------------------------------------------------------------


def test_work_date_uses_shop_timezone(db: Session) -> None:
    """23:30 UTC on Jan 15 = 04:30 on Jan 16 in Tashkent → work_date is Jan 16."""
    from zoneinfo import ZoneInfo

    emp = _make_employee(db, telegram_id=999_100_005)
    checkin_utc = datetime(2024, 1, 15, 23, 30, 0, tzinfo=UTC)

    expected_date = checkin_utc.astimezone(ZoneInfo("Asia/Tashkent")).date()
    assert expected_date == date(2024, 1, 16)

    record = AttendanceRecord(
        employee_id=emp.id,
        work_date=svc._work_date_from_ts(checkin_utc),
        check_in_at=checkin_utc,
    )
    db.add(record)
    db.flush()

    assert record.work_date == date(2024, 1, 16)


# ---------------------------------------------------------------------------
# 7. summary endpoint: worker gets 403, manager gets 200
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 7. Midnight rollover: stale open visits are closed and reopened on new day
# ---------------------------------------------------------------------------


def test_midnight_rollover_closes_and_reopens(db: Session) -> None:
    """Open visit from yesterday → closed at midnight, new visit opened for today."""
    yesterday = date.today() - timedelta(days=1)
    checkin_yesterday = datetime(
        yesterday.year, yesterday.month, yesterday.day, 20, 0, 0, tzinfo=UTC
    )

    emp = _make_employee(db, telegram_id=999_100_010)
    old = AttendanceRecord(employee_id=emp.id, work_date=yesterday, check_in_at=checkin_yesterday)
    db.add(old)
    db.flush()

    count = svc.rollover_midnight_visits(db)

    assert count == 1
    db.refresh(old)
    assert old.check_out_at is not None
    assert old.check_out_at > old.check_in_at

    from sqlalchemy import select

    new_visits = (
        db.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == emp.id)
            .where(AttendanceRecord.work_date == date.today())
        )
        .scalars()
        .all()
    )
    assert len(new_visits) == 1
    assert new_visits[0].check_out_at is None
    assert new_visits[0].check_in_at == old.check_out_at


def test_midnight_rollover_ignores_todays_open_visit(db: Session) -> None:
    """Open visit with today's work_date must not be touched."""
    today = date.today()
    emp = _make_employee(db, telegram_id=999_100_011)
    r = AttendanceRecord(
        employee_id=emp.id,
        work_date=today,
        check_in_at=datetime(today.year, today.month, today.day, 8, 0, 0, tzinfo=UTC),
    )
    db.add(r)
    db.flush()

    count = svc.rollover_midnight_visits(db)

    assert count == 0
    db.refresh(r)
    assert r.check_out_at is None


def test_midnight_rollover_ignores_already_closed_visit(db: Session) -> None:
    """Closed visit from yesterday must not be duplicated."""
    yesterday = date.today() - timedelta(days=1)
    t0 = datetime(yesterday.year, yesterday.month, yesterday.day, 8, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(hours=8)

    emp = _make_employee(db, telegram_id=999_100_012)
    r = AttendanceRecord(employee_id=emp.id, work_date=yesterday, check_in_at=t0, check_out_at=t1)
    db.add(r)
    db.flush()

    count = svc.rollover_midnight_visits(db)

    assert count == 0


# ---------------------------------------------------------------------------
# 8. summary endpoint: worker gets 403, manager gets 200
# ---------------------------------------------------------------------------


def test_summary_requires_manager_role(db: Session, client) -> None:  # type: ignore[no-untyped-def]
    worker = _make_employee(db, telegram_id=999_100_006, role=EmployeeRole.worker)
    resp = client.get(
        "/api/attendance/summary",
        headers={"Authorization": f"tma {make_test_init_data(worker.telegram_id)}"},
    )
    assert resp.status_code == 403

    manager = _make_employee(db, telegram_id=999_100_007, role=EmployeeRole.manager)
    resp2 = client.get(
        "/api/attendance/summary",
        headers={"Authorization": f"tma {make_test_init_data(manager.telegram_id)}"},
    )
    assert resp2.status_code == 200
