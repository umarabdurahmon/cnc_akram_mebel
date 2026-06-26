"""Несущие инварианты: оплаты, расходы, точность Decimal, CHECK-ограничения."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.models.finance import ExpenseCategory, ExpenseDirection, OrderExpense
from app.models.order import Order
from app.services import expense_category as cat_svc
from app.services import finance as fin_svc
from app.services import order as order_svc
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_500_001,
        full_name="Manager 9",
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
        telegram_id=999_500_002,
        full_name="Worker 9",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def category(db: Session) -> ExpenseCategory:
    return cat_svc.create_category(db, "Материалы")


@pytest.fixture
def order(db: Session, manager: Employee) -> Order:
    return order_svc.create_order(
        db,
        created_by=manager.id,
        customer_name="Клиент Ф",
        title="Шкаф-финансы",
        total_amount=Decimal("500000.00"),
    )


def auth(telegram_id: int) -> dict[str, str]:
    return {"Authorization": f"tma {make_test_init_data(telegram_id)}"}


# ---------------------------------------------------------------------------
# 1. DB CHECK: to_employee without employee_id → IntegrityError
# ---------------------------------------------------------------------------


def test_expense_to_employee_without_employee_raises(
    db: Session, manager: Employee, order: Order, category: ExpenseCategory
) -> None:
    """DB CHECK must fire when to_employee has no employee_id."""
    with pytest.raises(ValueError, match="employee_id is required"):
        fin_svc.add_expense(
            db,
            order_id=order.id,
            direction=ExpenseDirection.to_employee,
            category_id=category.id,
            amount=Decimal("1000.00"),
            spent_on=date.today(),
            created_by=manager.id,
            employee_id=None,
        )


def test_expense_to_employee_without_employee_db_check(
    db: Session, manager: Employee, worker: Employee, order: Order, category: ExpenseCategory
) -> None:
    """Direct DB insert also fires the CHECK (not only the service guard)."""
    db.add(
        OrderExpense(
            order_id=order.id,
            direction=ExpenseDirection.to_employee,
            category_id=category.id,
            employee_id=None,  # violates CHECK
            amount=Decimal("500.00"),
            spent_on=date.today(),
            created_by=manager.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_expense_general_without_employee_ok(
    db: Session, manager: Employee, order: Order, category: ExpenseCategory
) -> None:
    """general expense without employee_id must succeed."""
    expense = fin_svc.add_expense(
        db,
        order_id=order.id,
        direction=ExpenseDirection.general,
        category_id=category.id,
        amount=Decimal("200.00"),
        spent_on=date.today(),
        created_by=manager.id,
    )
    assert expense.id is not None
    assert expense.employee_id is None


# ---------------------------------------------------------------------------
# 2. Decimal precision: no float coercion
# ---------------------------------------------------------------------------


def test_decimal_amount_preserved_in_db(db: Session, manager: Employee, order: Order) -> None:
    """Amounts round-trip through Postgres NUMERIC as Decimal, not float."""
    amount = Decimal("123456.78")
    payment = fin_svc.add_payment(
        db,
        order_id=order.id,
        amount=amount,
        received_on=date.today(),
        created_by=manager.id,
    )
    db.refresh(payment)
    assert isinstance(payment.amount, Decimal)
    assert payment.amount == amount


def test_decimal_serialised_as_string_in_api(
    client: TestClient, manager: Employee, order: Order, category: ExpenseCategory
) -> None:
    """API JSON must not coerce Decimal to float."""
    amount_str = "99999.99"
    res = client.post(
        f"/api/orders/{order.id}/payments",
        json={"amount": amount_str, "received_on": str(date.today())},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    data = res.json()
    # Amount must be a string, not a float
    assert isinstance(data["amount"], str)
    assert data["amount"] == amount_str


# ---------------------------------------------------------------------------
# 3. Payments: SUM and balance
# ---------------------------------------------------------------------------


def test_total_paid_sums_correctly(db: Session, manager: Employee, order: Order) -> None:
    today = date.today()
    _p = dict(db=db, order_id=order.id, received_on=today, created_by=manager.id)
    fin_svc.add_payment(**_p, amount=Decimal("100.00"))
    fin_svc.add_payment(**_p, amount=Decimal("200.50"))
    assert fin_svc.total_paid(db, order.id) == Decimal("300.50")


def test_order_balance_api(
    client: TestClient, manager: Employee, order: Order, category: ExpenseCategory
) -> None:
    """total_paid - total_expenses = balance; receivable = total_amount - total_paid."""
    today = str(date.today())
    client.post(
        f"/api/orders/{order.id}/payments",
        json={"amount": "300000.00", "received_on": today},
        headers=auth(manager.telegram_id),
    )
    client.post(
        f"/api/orders/{order.id}/expenses",
        json={
            "direction": "general",
            "category_id": category.id,
            "amount": "50000.00",
            "spent_on": today,
        },
        headers=auth(manager.telegram_id),
    )

    res = client.get(f"/api/orders/{order.id}/balance", headers=auth(manager.telegram_id))
    assert res.status_code == 200
    data = res.json()
    assert data["total_paid"] == "300000.00"
    assert data["total_expenses"] == "50000.00"
    assert data["balance"] == "250000.00"
    assert data["receivable"] == "200000.00"  # 500000 - 300000


# ---------------------------------------------------------------------------
# 4. Expense category: deactivated not selectable; historical intact
# ---------------------------------------------------------------------------


def test_deactivated_category_historic_expenses_intact(
    db: Session, manager: Employee, order: Order, category: ExpenseCategory
) -> None:
    """Deactivating a category does not remove historical expenses."""
    expense = fin_svc.add_expense(
        db,
        order_id=order.id,
        direction=ExpenseDirection.general,
        category_id=category.id,
        amount=Decimal("1000.00"),
        spent_on=date.today(),
        created_by=manager.id,
    )
    cat_svc.patch_category(db, category.id, is_active=False)
    # Historical expense still exists and references the category
    db.refresh(expense)
    assert expense.category_id == category.id

    # Deactivated category not in active list
    active_cats = cat_svc.list_categories(db, include_inactive=False)
    assert all(c.id != category.id for c in active_cats)


# ---------------------------------------------------------------------------
# 5. Access control: worker → 403
# ---------------------------------------------------------------------------


def test_payments_worker_forbidden(client: TestClient, worker: Employee, order: Order) -> None:
    res = client.get(f"/api/orders/{order.id}/payments", headers=auth(worker.telegram_id))
    assert res.status_code == 403


def test_expenses_worker_forbidden(client: TestClient, worker: Employee, order: Order) -> None:
    res = client.get(f"/api/orders/{order.id}/expenses", headers=auth(worker.telegram_id))
    assert res.status_code == 403


def test_balance_worker_forbidden(client: TestClient, worker: Employee, order: Order) -> None:
    res = client.get(f"/api/orders/{order.id}/balance", headers=auth(worker.telegram_id))
    assert res.status_code == 403


def test_categories_worker_forbidden(client: TestClient, worker: Employee) -> None:
    res = client.get("/api/expense-categories", headers=auth(worker.telegram_id))
    assert res.status_code == 403
