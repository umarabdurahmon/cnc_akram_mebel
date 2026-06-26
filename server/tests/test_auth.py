from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from tests.conftest import make_test_init_data


def test_me_valid(client: TestClient, employee: Employee) -> None:
    init_data = make_test_init_data(employee.telegram_id)
    response = client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == employee.id
    assert body["full_name"] == employee.full_name
    assert body["role"] == EmployeeRole.worker.value


def test_me_invalid_signature(client: TestClient, employee: Employee) -> None:
    response = client.get("/api/me", headers={"Authorization": "tma garbage_not_a_real_initdata"})
    assert response.status_code == 401


def test_me_no_header(client: TestClient) -> None:
    response = client.get("/api/me")
    # FastAPI вернёт 422 (missing required header) или 401 — оба допустимы
    assert response.status_code in (401, 422)


def test_me_unknown_telegram_id(client: TestClient) -> None:
    # Подпись валидная, но telegram_id нет в БД
    init_data = make_test_init_data(telegram_id=888_000_000)
    response = client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
    assert response.status_code == 403


def test_me_inactive_employee(client: TestClient, db: Session) -> None:
    inactive = Employee(
        telegram_id=999_000_002,
        full_name="Fired Worker",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=False,
    )
    db.add(inactive)
    db.flush()

    init_data = make_test_init_data(inactive.telegram_id)
    response = client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
    assert response.status_code == 403
