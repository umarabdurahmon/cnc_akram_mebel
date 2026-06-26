"""Safe client-facing serializer for order status.

WHITELIST only — new Order fields do NOT reach the client unless explicitly added here.
Never exposes: money, files, employees, internal comments, id, internal_number.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.order import Order
from app.services import catalog as catalog_svc


@dataclass(frozen=True)
class ClientOrderView:
    """The ONLY representation of an order that may be shown to a client."""

    title: str
    description: str | None
    deadline: date | None
    public_note: str | None
    is_closed: bool
    # Stage progress — None values mean "no stage set" or "stage deactivated"
    stage_name: str | None
    stage_x: int | None  # 1-based position in active stage list
    stage_y: int | None  # total number of active stages


def serialize_for_client(db: Session, order: Order) -> ClientOrderView:
    """Build a ClientOrderView from an Order.

    Stage progress is computed against the current ACTIVE ordered stage list:
    - deactivated stages are excluded from Y
    - if the order's current stage was later deactivated, stage_name is shown
      but stage_x is None (no valid position)
    - if current_stage_id is None, all stage fields are None
    """
    active_stages = catalog_svc.list_stages(db, include_inactive=False)
    stage_y = len(active_stages) if active_stages else None

    stage_name: str | None = None
    stage_x: int | None = None

    if order.current_stage_id is not None:
        current_stage = catalog_svc.get_stage(db, order.current_stage_id)
        if current_stage is not None:
            stage_name = current_stage.name
            active_ids = [s.id for s in active_stages]
            if current_stage.id in active_ids:
                stage_x = active_ids.index(current_stage.id) + 1

    return ClientOrderView(
        title=order.title,
        description=order.description,
        deadline=order.deadline,
        public_note=order.public_note,
        is_closed=order.is_closed,
        stage_name=stage_name,
        stage_x=stage_x,
        stage_y=stage_y,
    )


def find_order_by_code(db: Session, raw_code: str) -> Order | None:
    """Lookup order by public_code, normalising to uppercase with whitespace stripped."""
    from sqlalchemy import select

    code = raw_code.strip().upper()
    return db.execute(select(Order).where(Order.public_code == code)).scalar_one_or_none()
