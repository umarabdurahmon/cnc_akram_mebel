from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finance import ExpenseCategory, OperatingExpense, OrderExpense


def list_categories(db: Session, *, include_inactive: bool = False) -> list[ExpenseCategory]:
    q = select(ExpenseCategory)
    if not include_inactive:
        q = q.where(ExpenseCategory.is_active.is_(True))
    q = q.order_by(ExpenseCategory.name)
    return list(db.execute(q).scalars().all())


def get_category(db: Session, category_id: int) -> ExpenseCategory | None:
    return db.get(ExpenseCategory, category_id)


def create_category(db: Session, name: str) -> ExpenseCategory:
    cat = ExpenseCategory(name=name)
    db.add(cat)
    db.flush()
    return cat


def patch_category(
    db: Session,
    category_id: int,
    *,
    name: str | None = None,
    is_active: bool | None = None,
) -> ExpenseCategory:
    cat = db.get(ExpenseCategory, category_id)
    if cat is None:
        raise ValueError(f"Category {category_id} not found")
    if name is not None:
        cat.name = name
    if is_active is not None:
        cat.is_active = is_active
    db.flush()
    return cat


def delete_category(db: Session, category_id: int) -> None:
    cat = db.get(ExpenseCategory, category_id)
    if cat is None:
        raise ValueError("not_found")
    if cat.is_active:
        raise ValueError("still_active")
    in_order_expenses = db.execute(
        select(OrderExpense.id).where(OrderExpense.category_id == category_id).limit(1)
    ).scalar_one_or_none()
    if in_order_expenses:
        raise ValueError("in_use")
    in_operating = db.execute(
        select(OperatingExpense.id).where(OperatingExpense.category_id == category_id).limit(1)
    ).scalar_one_or_none()
    if in_operating:
        raise ValueError("in_use")
    db.delete(cat)
    db.flush()
