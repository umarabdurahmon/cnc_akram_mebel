import hashlib
import hmac
import json
import os
import time
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlencode

import dotenv
import pytest
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from alembic import command as alembic_command
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.employee import Employee, EmployeeLanguage, EmployeeRole

# Загружаем .env из корня проекта (server/../.env)
dotenv.load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


# ---------------------------------------------------------------------------
# Engine и схема
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    url = os.environ["TEST_DATABASE_URL"]
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(test_engine: Engine) -> None:
    """Применяем все миграции к тестовой БД перед запуском тестов (идемпотентно)."""
    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_engine.url.render_as_string(hide_password=False))
    alembic_command.upgrade(cfg, "head")


# ---------------------------------------------------------------------------
# Сессия и клиент
# ---------------------------------------------------------------------------


@pytest.fixture
def db(test_engine: Engine) -> Generator[Session, None, None]:
    """Сессия в транзакции с откатом — БД после теста всегда чистая."""
    with test_engine.connect() as conn:
        with conn.begin():
            with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
                yield session
            # Транзакция откатывается автоматически (без commit)


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Вспомогательные функции / фикстуры для тестов авторизации
# ---------------------------------------------------------------------------


def make_test_init_data(telegram_id: int, first_name: str = "Test") -> str:
    """Генерирует валидную initData, подписанную тем же HMAC что Telegram."""
    user_json = json.dumps(
        {"id": telegram_id, "first_name": first_name, "is_bot": False},
        separators=(",", ":"),
    )
    auth_date = str(int(time.time()))
    raw = {"auth_date": auth_date, "user": user_json}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(raw.items()))

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.bot_token.encode(),
        digestmod=hashlib.sha256,
    )
    hash_ = hmac.new(
        key=secret_key.digest(),
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return urlencode({**raw, "hash": hash_})


@pytest.fixture
def employee(db: Session) -> Employee:
    """Активный сотрудник с ролью worker, создаётся в рамках откатываемой транзакции."""
    emp = Employee(
        telegram_id=999_000_001,
        full_name="Test Worker",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp
