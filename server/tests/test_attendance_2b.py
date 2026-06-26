"""Invariant tests for Session 2b: verification and manual editing.

All tests run against real Postgres (furniture_test), each in a rolled-back transaction.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, VerificationStatus
from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.services import attendance as svc
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SHOP_TZ = ZoneInfo("Asia/Tashkent")

_next_tid = iter(range(999_200_001, 999_299_999))


def _make_employee(
    db: Session,
    *,
    role: EmployeeRole = EmployeeRole.worker,
) -> Employee:
    emp = Employee(
        telegram_id=next(_next_tid),
        full_name="2b Test",
        role=role,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


def _closed_visit(
    db: Session,
    employee_id: int,
    check_in_at: datetime,
    check_out_at: datetime,
) -> AttendanceRecord:
    r = AttendanceRecord(
        employee_id=employee_id,
        work_date=check_in_at.astimezone(SHOP_TZ).date(),
        check_in_at=check_in_at,
        check_out_at=check_out_at,
    )
    db.add(r)
    db.flush()
    return r


def _open_visit(db: Session, employee_id: int, check_in_at: datetime) -> AttendanceRecord:
    r = AttendanceRecord(
        employee_id=employee_id,
        work_date=check_in_at.astimezone(SHOP_TZ).date(),
        check_in_at=check_in_at,
    )
    db.add(r)
    db.flush()
    return r


# ---------------------------------------------------------------------------
# 1. verify_record sets status, verified_by, verified_at
# ---------------------------------------------------------------------------


def test_verify_sets_fields(db: Session) -> None:
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)
    t0 = datetime(2024, 3, 1, 7, 0, tzinfo=UTC)
    visit = _closed_visit(db, worker.id, t0, t0 + timedelta(hours=8))

    assert visit.verification_status == VerificationStatus.not_checked

    result = svc.verify_record(db, visit.id, manager.id, VerificationStatus.confirmed)

    assert result.verification_status == VerificationStatus.confirmed
    assert result.verified_by == manager.id
    assert result.verified_at is not None


# ---------------------------------------------------------------------------
# 2. Re-verify updates all three verification fields
# ---------------------------------------------------------------------------


def test_reverify_updates_fields(db: Session) -> None:
    manager1 = _make_employee(db, role=EmployeeRole.manager)
    manager2 = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)
    t0 = datetime(2024, 3, 2, 7, 0, tzinfo=UTC)
    visit = _closed_visit(db, worker.id, t0, t0 + timedelta(hours=4))

    svc.verify_record(db, visit.id, manager1.id, VerificationStatus.confirmed)
    result = svc.verify_record(db, visit.id, manager2.id, VerificationStatus.discrepancy)

    assert result.verification_status == VerificationStatus.discrepancy
    assert result.verified_by == manager2.id


# ---------------------------------------------------------------------------
# 3. verify endpoint returns 403 for worker
# ---------------------------------------------------------------------------


def test_verify_forbidden_for_worker(db: Session, client) -> None:  # type: ignore[no-untyped-def]
    worker = _make_employee(db)
    manager = _make_employee(db, role=EmployeeRole.manager)
    t0 = datetime(2024, 3, 3, 7, 0, tzinfo=UTC)
    visit = _closed_visit(db, manager.id, t0, t0 + timedelta(hours=1))

    resp = client.post(
        f"/api/attendance/{visit.id}/verify",
        json={"status": "confirmed"},
        headers={"Authorization": f"tma {make_test_init_data(worker.telegram_id)}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. patch_record with check_out_at < check_in_at raises ValueError
# ---------------------------------------------------------------------------


def test_patch_checkout_before_checkin_raises(db: Session) -> None:
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)
    t0 = datetime(2024, 3, 4, 10, 0, tzinfo=UTC)
    visit = _closed_visit(db, worker.id, t0, t0 + timedelta(hours=2))

    with pytest.raises(ValueError, match="check_out_at must be after check_in_at"):
        svc.patch_record(
            db,
            visit.id,
            manager.id,
            check_out_at=t0 - timedelta(hours=1),
        )


# ---------------------------------------------------------------------------
# 5. patch_record: fixing forgotten checkout closes the visit correctly
# ---------------------------------------------------------------------------


def test_patch_fixes_forgotten_checkout(db: Session) -> None:
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)
    t0 = datetime(2024, 3, 5, 8, 0, tzinfo=UTC)
    visit = _open_visit(db, worker.id, t0)
    assert visit.check_out_at is None

    checkout = t0 + timedelta(hours=9)
    result = svc.patch_record(db, visit.id, manager.id, check_out_at=checkout)

    assert result.check_out_at == checkout
    assert result.edited_by == manager.id
    assert result.edited_at is not None

    hours = svc.hours_for_day(db, worker.id, visit.work_date)
    assert abs(hours - 9.0) < 0.001


# ---------------------------------------------------------------------------
# 6. patch_record: reopening a visit when another is open → IntegrityError (409 via API)
# ---------------------------------------------------------------------------


def test_patch_reopen_conflict_raises_integrity_error(db: Session) -> None:
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)
    t0 = datetime(2024, 3, 6, 8, 0, tzinfo=UTC)

    closed = _closed_visit(db, worker.id, t0, t0 + timedelta(hours=4))
    _open_visit(db, worker.id, t0 + timedelta(hours=5))

    # Try to reopen the closed visit → partial unique index should fire
    with pytest.raises(IntegrityError):
        svc.patch_record(db, closed.id, manager.id, check_out_at=None)


def test_patch_reopen_conflict_returns_409(db: Session, client) -> None:  # type: ignore[no-untyped-def]
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)
    t0 = datetime(2024, 3, 6, 8, 0, tzinfo=UTC)

    closed = _closed_visit(db, worker.id, t0, t0 + timedelta(hours=4))
    _open_visit(db, worker.id, t0 + timedelta(hours=5))

    resp = client.patch(
        f"/api/attendance/{closed.id}",
        json={"check_out_at": None},
        headers={"Authorization": f"tma {make_test_init_data(manager.telegram_id)}"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 7. patch_record: shifting check_in_at past midnight recalculates work_date
# ---------------------------------------------------------------------------


def test_patch_check_in_recalculates_work_date(db: Session) -> None:
    """Shifting check_in_at past local midnight must change work_date.

    Tashkent is UTC+5, so 19:00 UTC = midnight local.

    Setup:
      t_in  = 2024-01-15 10:00 UTC = 15:00 Tashkent → work_date 2024-01-15
      t_out = 2024-01-16 02:00 UTC =  07:00 Tashkent

    After patch check_in_at = 2024-01-15 19:30 UTC = 00:30 Tashkent Jan 16
      → work_date must become 2024-01-16
      → check_in_at (19:30 UTC Jan 15) is still before t_out (02:00 UTC Jan 16) ✓
    """
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker = _make_employee(db)

    t_in = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)  # 15:00 Tashkent Jan 15
    t_out = datetime(2024, 1, 16, 2, 0, tzinfo=UTC)  # 07:00 Tashkent Jan 16
    visit = _closed_visit(db, worker.id, t_in, t_out)
    assert visit.work_date == date(2024, 1, 15)

    new_checkin = datetime(2024, 1, 15, 19, 30, tzinfo=UTC)  # 00:30 Tashkent Jan 16
    result = svc.patch_record(db, visit.id, manager.id, check_in_at=new_checkin)

    assert result.work_date == date(2024, 1, 16)
    assert result.check_in_at == new_checkin


# ---------------------------------------------------------------------------
# 8. get_discrepancies counts correctly per employee and period
# ---------------------------------------------------------------------------


def test_get_discrepancies_counts_per_employee(db: Session) -> None:
    manager = _make_employee(db, role=EmployeeRole.manager)
    worker1 = _make_employee(db)
    worker2 = _make_employee(db)

    t0 = datetime(2024, 4, 1, 8, 0, tzinfo=UTC)
    d0 = date(2024, 4, 1)

    v1a = _closed_visit(db, worker1.id, t0, t0 + timedelta(hours=1))
    v1b = _closed_visit(db, worker1.id, t0 + timedelta(days=1), t0 + timedelta(days=1, hours=1))
    v2 = _closed_visit(db, worker2.id, t0, t0 + timedelta(hours=2))

    svc.verify_record(db, v1a.id, manager.id, VerificationStatus.discrepancy)
    svc.verify_record(db, v1b.id, manager.id, VerificationStatus.discrepancy)
    svc.verify_record(db, v2.id, manager.id, VerificationStatus.confirmed)

    results = svc.get_discrepancies(db, d0, date(2024, 4, 30))
    by_emp = {emp.id: cnt for emp, cnt in results}

    assert by_emp.get(worker1.id) == 2
    assert worker2.id not in by_emp


# ---------------------------------------------------------------------------
# 9. discrepancies endpoint returns 403 for worker
# ---------------------------------------------------------------------------


def test_discrepancies_forbidden_for_worker(db: Session, client) -> None:  # type: ignore[no-untyped-def]
    worker = _make_employee(db)
    resp = client.get(
        "/api/attendance/discrepancies?from_date=2024-01-01&to_date=2024-12-31",
        headers={"Authorization": f"tma {make_test_init_data(worker.telegram_id)}"},
    )
    assert resp.status_code == 403
