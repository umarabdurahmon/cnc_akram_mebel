from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatusHistory, ProductionStage


def list_stages(db: Session, *, include_inactive: bool = False) -> list[ProductionStage]:
    q = select(ProductionStage)
    if not include_inactive:
        q = q.where(ProductionStage.is_active.is_(True))
    q = q.order_by(ProductionStage.position, ProductionStage.id)
    return list(db.execute(q).scalars().all())


def get_stage(db: Session, stage_id: int) -> ProductionStage | None:
    return db.get(ProductionStage, stage_id)


def create_stage(db: Session, name: str, position: int | None = None) -> ProductionStage:
    if position is None:
        max_pos = db.execute(
            select(ProductionStage.position).order_by(ProductionStage.position.desc()).limit(1)
        ).scalar_one_or_none()
        position = (max_pos or 0) + 1
    stage = ProductionStage(name=name, position=position)
    db.add(stage)
    db.flush()
    return stage


def patch_stage(
    db: Session,
    stage_id: int,
    *,
    name: str | None = None,
    position: int | None = None,
    is_active: bool | None = None,
) -> ProductionStage:
    stage = db.get(ProductionStage, stage_id)
    if stage is None:
        raise ValueError(f"Stage {stage_id} not found")
    if name is not None:
        stage.name = name
    if position is not None:
        stage.position = position
    if is_active is not None:
        stage.is_active = is_active
    db.flush()
    return stage


def delete_stage(db: Session, stage_id: int) -> None:
    stage = db.get(ProductionStage, stage_id)
    if stage is None:
        raise ValueError("not_found")
    if stage.is_active:
        raise ValueError("still_active")
    in_orders = db.execute(
        select(Order.id).where(Order.current_stage_id == stage_id).limit(1)
    ).scalar_one_or_none()
    if in_orders:
        raise ValueError("in_use")
    in_history = db.execute(
        select(OrderStatusHistory.id).where(OrderStatusHistory.stage_id == stage_id).limit(1)
    ).scalar_one_or_none()
    if in_history:
        raise ValueError("in_use")
    db.delete(stage)
    db.flush()
