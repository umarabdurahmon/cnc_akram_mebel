"""Идемпотентный seed начальных данных справочников.

Создаёт этапы производства и категории расходов, если их ещё нет.
Безопасно запускать повторно — существующие записи не трогает.

Использование:
    python scripts/seed_catalog.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if "DATABASE_URL" not in os.environ:
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.finance import ExpenseCategory  # noqa: E402
from app.models.order import ProductionStage  # noqa: E402

DEFAULT_STAGES = [
    "Замер и проектирование",
    "Раскрой",
    "Сборка",
    "Покраска / отделка",
    "Готово",
]

DEFAULT_CATEGORIES = [
    "Материалы",
    "Зарплата / подотчёт",
    "Транспорт",
    "Аренда",
    "Коммунальные услуги",
    "Прочее",
]


def seed() -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)
    with Session(engine) as db:
        # Stages
        existing_stages = set(db.scalars(select(ProductionStage.name)).all())
        added_stages = 0
        for i, name in enumerate(DEFAULT_STAGES, start=1):
            if name not in existing_stages:
                db.add(ProductionStage(name=name, position=i))
                added_stages += 1

        # Categories
        existing_cats = set(db.scalars(select(ExpenseCategory.name)).all())
        added_cats = 0
        for name in DEFAULT_CATEGORIES:
            if name not in existing_cats:
                db.add(ExpenseCategory(name=name))
                added_cats += 1

        db.commit()

    print(f"Этапы: добавлено {added_stages} (пропущено {len(DEFAULT_STAGES) - added_stages})")
    print(f"Категории: добавлено {added_cats} (пропущено {len(DEFAULT_CATEGORIES) - added_cats})")


if __name__ == "__main__":
    sys.exit(seed())
