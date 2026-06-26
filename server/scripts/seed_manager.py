"""Идемпотентный скрипт создания первого руководителя.

Использование:
    python scripts/seed_manager.py --tg-id 123456789 --name "Акрам Юлдашев"

Если сотрудник с этим telegram_id уже существует — обновляет роль до manager
и устанавливает is_active=True. Если нет — создаёт.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта (server/scripts/../../.env)
if "DATABASE_URL" not in os.environ:
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole  # noqa: E402


def seed_manager(telegram_id: int, full_name: str) -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)
    with Session(engine) as session:
        emp = session.scalar(select(Employee).where(Employee.telegram_id == telegram_id))
        if emp is None:
            emp = Employee(
                telegram_id=telegram_id,
                full_name=full_name,
                role=EmployeeRole.manager,
                language=EmployeeLanguage.ru,
                is_active=True,
            )
            session.add(emp)
            action = "создан"
        else:
            emp.full_name = full_name
            emp.role = EmployeeRole.manager
            emp.is_active = True
            action = "обновлён"
        session.commit()
    print(f"OK: руководитель «{full_name}» (telegram_id={telegram_id}) {action}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать/обновить первого руководителя")
    parser.add_argument("--tg-id", type=int, required=True, help="Telegram user ID")
    parser.add_argument("--name", type=str, required=True, help="ФИО")
    args = parser.parse_args()
    seed_manager(args.tg_id, args.name)


if __name__ == "__main__":
    sys.exit(main())
