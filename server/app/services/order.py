import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Integer as SAInteger
from sqlalchemy import cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.order import Order, OrderEmployee, OrderStatusHistory

# Unambiguous alphabet: no 0/O, 1/I/l
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6
_MAX_CODE_RETRIES = 10


def generate_public_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


_NUMERIC_RE = r"^[0-9]+$"


def _next_internal_number(db: Session) -> str:
    """Return the next sequential internal order number as a zero-padded string."""
    max_n = (
        db.execute(
            select(func.max(cast(Order.internal_number, SAInteger))).where(
                Order.internal_number.regexp_match(_NUMERIC_RE)
            )
        ).scalar()
        or 0
    )
    return str(max_n + 1).zfill(3)


def _insert_with_retry(db: Session, make_order: Callable[[str, str], Order]) -> Order:
    """Insert order, retrying on any unique-constraint collision via savepoint.

    Generates a fresh public_code and internal_number on each attempt so
    the session stays clean after a rollback.
    """
    for _ in range(_MAX_CODE_RETRIES):
        order = make_order(generate_public_code(), _next_internal_number(db))
        sp = db.begin_nested()
        try:
            db.add(order)
            db.flush()
            sp.commit()
            return order
        except IntegrityError:
            sp.rollback()
    raise RuntimeError("Failed to generate unique order codes after retries")


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _write_history(
    db: Session,
    order_id: int,
    stage_id: int,
    changed_by: int,
    comment: str | None,
) -> OrderStatusHistory:
    entry = OrderStatusHistory(
        order_id=order_id,
        stage_id=stage_id,
        changed_by=changed_by,
        changed_at=_now_utc(),
        comment=comment,
    )
    db.add(entry)
    return entry


def create_order(
    db: Session,
    *,
    created_by: int,
    customer_name: str,
    title: str,
    customer_contact: str | None = None,
    customer_chat_id: int | None = None,
    description: str | None = None,
    current_stage_id: int | None = None,
    deadline: object | None = None,
    total_amount: Decimal | None = None,
    public_note: str | None = None,
    stage_comment: str | None = None,
    delivery_lat: float | None = None,
    delivery_lon: float | None = None,
) -> Order:
    def _make_order(code: str, internal_number: str) -> Order:
        return Order(
            public_code=code,
            internal_number=internal_number,
            customer_name=customer_name,
            customer_contact=customer_contact,
            customer_chat_id=customer_chat_id,
            title=title,
            description=description,
            current_stage_id=current_stage_id,
            deadline=deadline,
            total_amount=total_amount,
            public_note=public_note,
            delivery_lat=delivery_lat,
            delivery_lon=delivery_lon,
            created_by=created_by,
        )

    order = _insert_with_retry(db, _make_order)

    if current_stage_id is not None:
        _write_history(db, order.id, current_stage_id, created_by, stage_comment)
        db.flush()

    return order


def get_order(db: Session, order_id: int) -> Order | None:
    return db.get(Order, order_id)


def list_orders(db: Session, *, employee_id: int | None = None) -> list[Order]:
    # Open orders first (sorted by deadline), then closed orders at the bottom
    stmt = select(Order).order_by(
        Order.is_closed.asc(),
        Order.deadline.asc().nulls_last(),
        Order.created_at.desc(),
    )
    if employee_id is not None:
        stmt = stmt.where(
            Order.id.in_(
                select(OrderEmployee.order_id).where(OrderEmployee.employee_id == employee_id)
            )
        )
    return list(db.execute(stmt).scalars().all())


def close_order(db: Session, order_id: int, closed_by: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError("not_found")
    if order.is_closed:
        raise ValueError("already_closed")
    order.is_closed = True
    order.closed_at = datetime.now(UTC)
    order.closed_by = closed_by
    db.flush()
    return order


def update_order(db: Session, order_id: int, **kwargs: object) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    for key, value in kwargs.items():
        setattr(order, key, value)
    order.updated_at = _now_utc()
    db.flush()
    return order


def change_stage(
    db: Session,
    order_id: int,
    stage_id: int,
    changed_by: int,
    comment: str | None = None,
) -> Order:
    """Change order stage and write one history entry atomically."""
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    order.current_stage_id = stage_id
    order.updated_at = _now_utc()
    _write_history(db, order_id, stage_id, changed_by, comment)
    db.flush()
    return order


def get_history(db: Session, order_id: int) -> list[OrderStatusHistory]:
    return list(
        db.execute(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.changed_at.desc())
        )
        .scalars()
        .all()
    )
