"""Несущие инварианты: M2M прикрепление + объектное право на смену статуса."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.models.order import Order, OrderEmployee, ProductionStage
from app.services import catalog as catalog_svc
from app.services import order as order_svc
from app.services import order_employee as oe_svc
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_200_001,
        full_name="Manager 5",
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
        telegram_id=999_200_002,
        full_name="Worker 5",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def stage(db: Session) -> ProductionStage:
    return catalog_svc.create_stage(db, "Сборка 5", position=1)


@pytest.fixture
def order_a(db: Session, manager: Employee) -> Order:
    return order_svc.create_order(db, created_by=manager.id, customer_name="А", title="Заказ А")


@pytest.fixture
def order_b(db: Session, manager: Employee) -> Order:
    return order_svc.create_order(db, created_by=manager.id, customer_name="Б", title="Заказ Б")


def auth(telegram_id: int) -> dict:
    return {"Authorization": f"tma {make_test_init_data(telegram_id)}"}


# ---------------------------------------------------------------------------
# 1. IDOR: worker with can_change_status on A cannot touch B
# ---------------------------------------------------------------------------


def test_worker_can_change_stage_on_own_order(
    client: TestClient,
    manager: Employee,
    worker: Employee,
    order_a: Order,
    stage: ProductionStage,
    db: Session,
) -> None:
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=True, attached_by=manager.id)

    res = client.post(
        f"/api/orders/{order_a.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 200
    assert res.json()["current_stage_id"] == stage.id


def test_worker_cannot_change_stage_on_other_order(
    client: TestClient,
    manager: Employee,
    worker: Employee,
    order_a: Order,
    order_b: Order,
    stage: ProductionStage,
    db: Session,
) -> None:
    """Key IDOR test: right on A must not open B."""
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=True, attached_by=manager.id)

    res = client.post(
        f"/api/orders/{order_b.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 2. can_change_status=False and not attached → 403
# ---------------------------------------------------------------------------


def test_worker_attached_but_flag_false_cannot_change_stage(
    client: TestClient,
    manager: Employee,
    worker: Employee,
    order_a: Order,
    stage: ProductionStage,
    db: Session,
) -> None:
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=False, attached_by=manager.id)

    res = client.post(
        f"/api/orders/{order_a.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


def test_worker_not_attached_cannot_change_stage(
    client: TestClient,
    worker: Employee,
    order_a: Order,
    stage: ProductionStage,
) -> None:
    res = client.post(
        f"/api/orders/{order_a.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 3. Manager changes stage on any order without attachment
# ---------------------------------------------------------------------------


def test_manager_can_change_stage_without_attachment(
    client: TestClient,
    manager: Employee,
    order_b: Order,
    stage: ProductionStage,
) -> None:
    res = client.post(
        f"/api/orders/{order_b.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# 4. Stage change writes history with correct changed_by
# ---------------------------------------------------------------------------


def test_worker_stage_change_recorded_with_correct_changed_by(
    client: TestClient,
    manager: Employee,
    worker: Employee,
    order_a: Order,
    stage: ProductionStage,
    db: Session,
) -> None:
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=True, attached_by=manager.id)

    client.post(
        f"/api/orders/{order_a.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(worker.telegram_id),
    )
    history = client.get(
        f"/api/orders/{order_a.id}/history",
        headers=auth(manager.telegram_id),
    ).json()
    assert len(history) == 1
    assert history[0]["changed_by"] == worker.id


# ---------------------------------------------------------------------------
# 5. Revocation: remove can_change_status → immediate 403
# ---------------------------------------------------------------------------


def test_revoke_can_change_status_takes_effect_immediately(
    client: TestClient,
    manager: Employee,
    worker: Employee,
    order_a: Order,
    stage: ProductionStage,
    db: Session,
) -> None:
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=True, attached_by=manager.id)
    # Revoke by upsert with flag=False
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=False, attached_by=manager.id)

    res = client.post(
        f"/api/orders/{order_a.id}/stage",
        json={"stage_id": stage.id},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 6. UNIQUE(order_id, employee_id) at DB level
# ---------------------------------------------------------------------------


def test_unique_constraint_on_order_employee(
    db: Session,
    manager: Employee,
    worker: Employee,
    order_a: Order,
) -> None:
    db.add(OrderEmployee(order_id=order_a.id, employee_id=worker.id, can_change_status=False))
    db.flush()
    db.add(OrderEmployee(order_id=order_a.id, employee_id=worker.id, can_change_status=True))
    with pytest.raises(IntegrityError):
        db.flush()


# ---------------------------------------------------------------------------
# 7. Attachment / detachment / edit fields — manager-only
# ---------------------------------------------------------------------------


def test_attach_requires_manager(
    client: TestClient,
    worker: Employee,
    order_a: Order,
) -> None:
    res = client.post(
        f"/api/orders/{order_a.id}/employees",
        json={"employee_id": worker.id, "can_change_status": True},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


def test_patch_order_requires_manager(
    client: TestClient,
    worker: Employee,
    order_a: Order,
) -> None:
    res = client.patch(
        f"/api/orders/{order_a.id}",
        json={"title": "Hacked"},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


def test_attach_detach_via_api(
    client: TestClient,
    manager: Employee,
    worker: Employee,
    order_a: Order,
) -> None:
    res = client.post(
        f"/api/orders/{order_a.id}/employees",
        json={"employee_id": worker.id, "can_change_status": True},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    assert res.json()["can_change_status"] is True

    del_res = client.delete(
        f"/api/orders/{order_a.id}/employees/{worker.id}",
        headers=auth(manager.telegram_id),
    )
    assert del_res.status_code == 204


def test_worker_sees_only_attached_orders(
    client: TestClient,
    db: Session,
    manager: Employee,
    worker: Employee,
    order_a: Order,
    order_b: Order,
) -> None:
    # До привязки — список пуст
    res = client.get("/api/orders", headers=auth(worker.telegram_id))
    assert res.status_code == 200
    assert res.json() == []

    # Привязываем к order_a
    oe_svc.attach(db, order_a.id, worker.id, can_change_status=False, attached_by=manager.id)

    res = client.get("/api/orders", headers=auth(worker.telegram_id))
    assert res.status_code == 200
    ids = [o["id"] for o in res.json()]
    assert order_a.id in ids
    assert order_b.id not in ids
