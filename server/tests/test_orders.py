"""Несущие инварианты: справочник этапов + CRUD заказов + история."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.models.order import Order, ProductionStage
from app.services import catalog as catalog_svc
from app.services import order as order_svc
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_100_001,
        full_name="Test Manager",
        role=EmployeeRole.manager,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def worker(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_100_002,
        full_name="Test Worker",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def stage(db: Session) -> ProductionStage:
    s = catalog_svc.create_stage(db, "Раскрой", position=1)
    return s


@pytest.fixture
def order(db: Session, manager: Employee) -> Order:
    return order_svc.create_order(db, created_by=manager.id, customer_name="Клиент А", title="Шкаф")


def auth(telegram_id: int) -> dict:
    return {"Authorization": f"tma {make_test_init_data(telegram_id)}"}


# ---------------------------------------------------------------------------
# 1. public_code alphabet safety + collision retry
# ---------------------------------------------------------------------------


def test_public_code_uses_safe_alphabet(db: Session, manager: Employee) -> None:
    """Алфавит не содержит двусмысленных символов (0, O, 1, I, l)."""
    ambiguous = set("0O1Il")
    for _ in range(20):
        o = order_svc.create_order(db, created_by=manager.id, customer_name="X", title="Y")
        assert not ambiguous.intersection(set(o.public_code)), f"Ambiguous chars in {o.public_code}"
        assert len(o.public_code) == 6
        assert o.public_code.upper() == o.public_code


def test_public_code_collision_retry(db: Session, manager: Employee) -> None:
    """При IntegrityError на public_code сервис делает ретрай и генерирует новый код."""
    # Первый заказ занимает код "AAAAAA"
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])

    with patch("app.services.order.generate_public_code", side_effect=codes):
        o1 = order_svc.create_order(db, created_by=manager.id, customer_name="C1", title="T1")
        assert o1.public_code == "AAAAAA"

        # Второй заказ: первые две попытки — "AAAAAA" (коллизия), третья — "BBBBBB"
        o2 = order_svc.create_order(db, created_by=manager.id, customer_name="C2", title="T2")
        assert o2.public_code == "BBBBBB"
        assert o1.public_code != o2.public_code


# ---------------------------------------------------------------------------
# 2. Soft-delete этапа + валидность ссылающегося заказа + порядок
# ---------------------------------------------------------------------------


def test_deactivate_stage_does_not_delete_row(db: Session, stage: ProductionStage) -> None:
    """Деактивация этапа не удаляет строку из БД."""
    stage_id = stage.id
    catalog_svc.patch_stage(db, stage_id, is_active=False)

    found = db.get(ProductionStage, stage_id)
    assert found is not None
    assert found.is_active is False


def test_order_stays_valid_after_stage_deactivated(
    db: Session, manager: Employee, stage: ProductionStage
) -> None:
    """Заказ, ссылающийся на деактивированный этап, остаётся валидным."""
    o = order_svc.create_order(
        db, created_by=manager.id, customer_name="C", title="T", current_stage_id=stage.id
    )
    catalog_svc.patch_stage(db, stage.id, is_active=False)
    db.refresh(o)
    assert o.current_stage_id == stage.id  # FK intact, order valid


def test_reorder_changes_position(db: Session) -> None:
    """Изменение position меняет порядок в списке."""
    s1 = catalog_svc.create_stage(db, "Сборка", position=1)
    s2 = catalog_svc.create_stage(db, "Покраска", position=2)

    catalog_svc.patch_stage(db, s1.id, position=10)
    stages = catalog_svc.list_stages(db)
    positions = [s.id for s in stages]
    assert positions.index(s2.id) < positions.index(s1.id)


# ---------------------------------------------------------------------------
# 3. Смена этапа пишет ровно одну запись истории
# ---------------------------------------------------------------------------


def test_change_stage_writes_exactly_one_history_entry(
    db: Session, manager: Employee, stage: ProductionStage, order: Order
) -> None:
    """change_stage создаёт ровно одну запись в order_status_history."""
    order_svc.change_stage(db, order.id, stage.id, manager.id, comment="тест")

    history = order_svc.get_history(db, order.id)
    assert len(history) == 1
    entry = history[0]
    assert entry.stage_id == stage.id
    assert entry.changed_by == manager.id
    assert entry.comment == "тест"


def test_create_order_with_stage_writes_history(
    db: Session, manager: Employee, stage: ProductionStage
) -> None:
    """Создание заказа со стартовым этапом пишет первую запись истории."""
    o = order_svc.create_order(
        db,
        created_by=manager.id,
        customer_name="C",
        title="T",
        current_stage_id=stage.id,
        stage_comment="старт",
    )
    history = order_svc.get_history(db, o.id)
    assert len(history) == 1
    assert history[0].stage_id == stage.id
    assert history[0].changed_by == manager.id
    assert history[0].comment == "старт"


# ---------------------------------------------------------------------------
# 4. Роль: manager OK, worker → 403
# ---------------------------------------------------------------------------


def test_stages_manager_access(client: TestClient, manager: Employee) -> None:
    res = client.get("/api/stages", headers=auth(manager.telegram_id))
    assert res.status_code == 200


def test_stages_worker_can_list_active(client: TestClient, worker: Employee) -> None:
    # Workers can see active stages (needed to change stage on their orders)
    res = client.get("/api/stages", headers=auth(worker.telegram_id))
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_stages_worker_cannot_list_with_inactive(client: TestClient, worker: Employee) -> None:
    res = client.get("/api/stages?include_inactive=true", headers=auth(worker.telegram_id))
    assert res.status_code == 403


def test_orders_create_manager(client: TestClient, manager: Employee) -> None:
    res = client.post(
        "/api/orders",
        json={"customer_name": "Клиент", "title": "Диван"},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data["public_code"]) == 6
    # id and internal_number must not be used as public identifier — just verify field exists
    assert "public_code" in data


def test_orders_list_worker_allowed(client: TestClient, worker: Employee) -> None:
    # Session 5: workers have read-only access to orders (матрица 5.2)
    res = client.get("/api/orders", headers=auth(worker.telegram_id))
    assert res.status_code == 200


def test_orders_change_stage_via_api(
    client: TestClient, manager: Employee, stage: ProductionStage, order: Order
) -> None:
    res = client.post(
        f"/api/orders/{order.id}/stage",
        json={"stage_id": stage.id, "comment": "переход"},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 200
    assert res.json()["current_stage_id"] == stage.id


def test_orders_history_via_api(
    client: TestClient, manager: Employee, stage: ProductionStage, order: Order
) -> None:
    client.post(
        f"/api/orders/{order.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(manager.telegram_id),
    )
    res = client.get(f"/api/orders/{order.id}/history", headers=auth(manager.telegram_id))
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["changed_by"] == manager.id
