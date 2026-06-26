from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee


def get_by_telegram_id(db: Session, telegram_id: int) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.telegram_id == telegram_id))
