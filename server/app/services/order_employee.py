from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeRole
from app.models.order import OrderEmployee


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def attach(
    db: Session,
    order_id: int,
    employee_id: int,
    *,
    can_change_status: bool,
    attached_by: int,
) -> OrderEmployee:
    """Attach employee to order (upsert: repeat call updates can_change_status)."""
    now = _now_utc()
    stmt = (
        pg_insert(OrderEmployee)
        .values(
            order_id=order_id,
            employee_id=employee_id,
            can_change_status=can_change_status,
            attached_by=attached_by,
            attached_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_order_employee",
            set_={
                "can_change_status": can_change_status,
                "attached_by": attached_by,
                "attached_at": now,
            },
        )
    )
    db.execute(stmt)
    db.flush()
    row = db.execute(
        select(OrderEmployee)
        .where(OrderEmployee.order_id == order_id)
        .where(OrderEmployee.employee_id == employee_id)
    ).scalar_one()
    return row


def detach(db: Session, order_id: int, employee_id: int) -> bool:
    """Remove attachment. Returns True if a row was deleted."""
    from sqlalchemy.engine import CursorResult

    result: CursorResult[tuple[()]] = db.execute(  # type: ignore[assignment]
        delete(OrderEmployee)
        .where(OrderEmployee.order_id == order_id)
        .where(OrderEmployee.employee_id == employee_id)
    )
    db.flush()
    return bool(result.rowcount > 0)


def list_attachments(db: Session, order_id: int) -> list[OrderEmployee]:
    return list(
        db.execute(
            select(OrderEmployee)
            .where(OrderEmployee.order_id == order_id)
            .order_by(OrderEmployee.attached_at)
        )
        .scalars()
        .all()
    )


def is_attached(db: Session, employee_id: int, order_id: int) -> bool:
    """Check if an employee has any attachment to the order (regardless of can_change_status)."""
    row = db.execute(
        select(OrderEmployee)
        .where(OrderEmployee.order_id == order_id)
        .where(OrderEmployee.employee_id == employee_id)
    ).scalar_one_or_none()
    return row is not None


def can_change_order_status(db: Session, employee: Employee, order_id: int) -> bool:
    """Centralised permission check — filters on BOTH order_id AND employee_id (IDOR-safe)."""
    if employee.role == EmployeeRole.manager:
        return True
    row = db.execute(
        select(OrderEmployee)
        .where(OrderEmployee.order_id == order_id)
        .where(OrderEmployee.employee_id == employee.id)
        .where(OrderEmployee.can_change_status.is_(True))
    ).scalar_one_or_none()
    return row is not None
