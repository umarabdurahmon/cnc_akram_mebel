from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.models.order import Order, OrderEmployee
from app.schemas.order import (
    AttachRequest,
    OrderCreate,
    OrderEmployeeOut,
    OrderOut,
    OrderPatch,
    OrderStatusHistoryOut,
    StageChangeRequest,
)
from app.services import catalog as catalog_svc
from app.services import finance as finance_svc
from app.services import order as order_svc
from app.services import order_employee as oe_svc
from app.services import telegram_notify

router = APIRouter(prefix="/orders", tags=["orders"])


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = order_svc.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _enrich(
    db: Session,
    order: Order,
    employee: Employee,
    paid_map: dict[int, Decimal] | None = None,
) -> OrderOut:
    """Enrich OrderOut: stage name, can_change_status_for_me, payments, worker projection."""
    out = OrderOut.model_validate(order)
    stage_name: str | None = None
    if order.current_stage_id is not None:
        stage = catalog_svc.get_stage(db, order.current_stage_id)
        if stage:
            stage_name = stage.name
    can_change = oe_svc.can_change_order_status(db, employee, order.id)
    is_manager = employee.role == EmployeeRole.manager
    amount = out.total_amount if is_manager else None
    if is_manager:
        paid = (
            paid_map[order.id]
            if paid_map and order.id in paid_map
            else finance_svc.total_paid(db, order.id)
        )
        bal = (out.total_amount - paid) if out.total_amount is not None else None
    else:
        paid = out.total_paid
        bal = None
    return out.model_copy(
        update={
            "current_stage_name": stage_name,
            "can_change_status_for_me": can_change,
            "total_amount": amount,
            "total_paid": paid,
            "balance": bal,
        }
    )


def _bulk_can_change_set(db: Session, employee_id: int, order_ids: list[int]) -> set[int]:
    """Single query: returns order_ids where this worker has can_change_status=True."""
    if not order_ids:
        return set()
    rows = (
        db.execute(
            select(OrderEmployee.order_id)
            .where(OrderEmployee.employee_id == employee_id)
            .where(OrderEmployee.can_change_status.is_(True))
            .where(OrderEmployee.order_id.in_(order_ids))
        )
        .scalars()
        .all()
    )
    return set(rows)


# ---------------------------------------------------------------------------
# Orders — manager-write, worker-read
# ---------------------------------------------------------------------------


@router.get("", response_model=list[OrderOut])
def list_orders(
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    is_manager = employee.role == EmployeeRole.manager
    orders = order_svc.list_orders(db, employee_id=None if is_manager else employee.id)
    order_ids = [o.id for o in orders]

    can_change_set = (
        {o.id for o in orders} if is_manager else _bulk_can_change_set(db, employee.id, order_ids)
    )
    paid_map = finance_svc.bulk_total_paid(db, order_ids) if is_manager else {}

    result = []
    for order in orders:
        out = OrderOut.model_validate(order)
        stage_name: str | None = None
        if order.current_stage_id is not None:
            stage = catalog_svc.get_stage(db, order.current_stage_id)
            if stage:
                stage_name = stage.name
        amount = out.total_amount if is_manager else None
        paid = paid_map.get(order.id, Decimal("0.00")) if is_manager else out.total_paid
        bal = (out.total_amount - paid) if (is_manager and out.total_amount is not None) else None
        result.append(
            out.model_copy(
                update={
                    "current_stage_name": stage_name,
                    "can_change_status_for_me": order.id in can_change_set,
                    "total_amount": amount,
                    "total_paid": paid,
                    "balance": bal,
                }
            )
        )
    return result


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    body: OrderCreate,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderOut:
    _require_manager(employee)
    order = order_svc.create_order(
        db,
        created_by=employee.id,
        customer_name=body.customer_name,
        title=body.title,
        customer_contact=body.customer_contact,
        customer_chat_id=body.customer_chat_id,
        description=body.description,
        current_stage_id=body.current_stage_id,
        deadline=body.deadline,
        total_amount=body.total_amount,
        public_note=body.public_note,
        stage_comment=body.stage_comment,
        delivery_lat=body.delivery_lat,
        delivery_lon=body.delivery_lon,
    )
    return _enrich(db, order, employee)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    return _enrich(db, order, employee)


@router.patch("/{order_id}", response_model=OrderOut)
def patch_order(
    order_id: int,
    body: OrderPatch,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderOut:
    _require_manager(employee)
    order = _get_order_or_404(db, order_id)
    if order.is_closed:
        raise HTTPException(status_code=409, detail="Order is closed")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    order = order_svc.update_order(db, order_id, **updates)
    return _enrich(db, order, employee)


@router.post("/{order_id}/close", response_model=OrderOut)
def close_order(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderOut:
    _require_manager(employee)
    try:
        order = order_svc.close_order(db, order_id, closed_by=employee.id)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            raise HTTPException(status_code=404, detail="Order not found")
        raise HTTPException(status_code=409, detail="Order is already closed")
    return _enrich(db, order, employee)


@router.post("/{order_id}/share-location", status_code=204)
def share_location(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    order = _get_order_or_404(db, order_id)
    if order.delivery_lat is None or order.delivery_lon is None:
        raise HTTPException(status_code=409, detail="Order has no delivery location")
    title = f"📦 {order.title} — {order.customer_name}"
    telegram_notify.send_location(
        chat_id=employee.telegram_id,
        lat=float(order.delivery_lat),
        lon=float(order.delivery_lon),
        title=title,
        phone=order.customer_contact,
    )


@router.post("/{order_id}/stage", response_model=OrderOut)
def change_stage(
    order_id: int,
    body: StageChangeRequest,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderOut:
    _get_order_or_404(db, order_id)
    if not oe_svc.can_change_order_status(db, employee, order_id):
        raise HTTPException(status_code=403, detail="No permission to change this order's stage")
    order = order_svc.change_stage(db, order_id, body.stage_id, employee.id, body.comment)
    return _enrich(db, order, employee)


@router.get("/{order_id}/history", response_model=list[OrderStatusHistoryOut])
def get_history(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[OrderStatusHistoryOut]:
    _get_order_or_404(db, order_id)
    if employee.role != EmployeeRole.manager:
        if not oe_svc.is_attached(db, employee.id, order_id):
            raise HTTPException(status_code=403, detail="Not assigned to this order")
    history = order_svc.get_history(db, order_id)
    return [OrderStatusHistoryOut.model_validate(h) for h in history]


# ---------------------------------------------------------------------------
# Employee attachments — manager-only
# ---------------------------------------------------------------------------


@router.get("/{order_id}/employees", response_model=list[OrderEmployeeOut])
def list_order_employees(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[OrderEmployeeOut]:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    rows = oe_svc.list_attachments(db, order_id)
    return [OrderEmployeeOut.model_validate(r) for r in rows]


@router.post("/{order_id}/employees", response_model=OrderEmployeeOut, status_code=201)
def attach_employee(
    order_id: int,
    body: AttachRequest,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderEmployeeOut:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    row = oe_svc.attach(
        db,
        order_id,
        body.employee_id,
        can_change_status=body.can_change_status,
        attached_by=employee.id,
    )
    return OrderEmployeeOut.model_validate(row)


@router.delete("/{order_id}/employees/{employee_id}", status_code=204)
def detach_employee(
    order_id: int,
    employee_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    found = oe_svc.detach(db, order_id, employee_id)
    if not found:
        raise HTTPException(status_code=404, detail="Attachment not found")
