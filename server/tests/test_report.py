"""Несущие инварианты: операционные расходы и месячный отчёт из трёх источников."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.models.finance import ExpenseCategory
from app.models.order import Order
from app.services import expense_category as cat_svc
from app.services import finance as fin_svc
from app.services import order as order_svc
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

YEAR, MONTH = 2025, 3
IN_MONTH = date(2025, 3, 15)
OUT_OF_MONTH = date(2025, 4, 1)


@pytest.fixture
def manager(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_600_001,
        full_name="Manager 10",
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
        telegram_id=999_600_002,
        full_name="Worker 10",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def cat_a(db: Session) -> ExpenseCategory:
    return cat_svc.create_category(db, "Аренда")


@pytest.fixture
def cat_b(db: Session) -> ExpenseCategory:
    return cat_svc.create_category(db, "Материалы")


@pytest.fixture
def order(db: Session, manager: Employee) -> Order:
    return order_svc.create_order(
        db, created_by=manager.id, customer_name="Клиент 10", title="Заказ 10"
    )


def auth(telegram_id: int) -> dict[str, str]:
    return {"Authorization": f"tma {make_test_init_data(telegram_id)}"}


# ---------------------------------------------------------------------------
# 1. Revenue + expenses from all three sources computed correctly
# ---------------------------------------------------------------------------


def test_monthly_report_three_sources(
    db: Session,
    manager: Employee,
    order: Order,
    cat_a: ExpenseCategory,
    cat_b: ExpenseCategory,
) -> None:
    """Revenue, order_expenses, operating_expenses summed correctly; profit = revenue - total."""
    # Revenue (order payment)
    fin_svc.add_payment(
        db,
        order_id=order.id,
        amount=Decimal("100000.00"),
        received_on=IN_MONTH,
        created_by=manager.id,
    )
    # Order expense → cat_a
    fin_svc.add_expense(
        db,
        order_id=order.id,
        direction="general",
        category_id=cat_a.id,
        amount=Decimal("20000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )
    # Operating expense → cat_b (different category, different source)
    fin_svc.add_operating_expense(
        db,
        category_id=cat_b.id,
        amount=Decimal("5000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )

    report = fin_svc.monthly_report(db, YEAR, MONTH)

    assert report.revenue == Decimal("100000.00")
    assert report.order_expenses == Decimal("20000.00")
    assert report.operating_expenses == Decimal("5000.00")
    assert report.total_expenses == Decimal("25000.00")
    assert report.profit == Decimal("75000.00")


# ---------------------------------------------------------------------------
# 2. Invariant: total_expenses == sum of category breakdown
# ---------------------------------------------------------------------------


def test_invariant_total_equals_breakdown_sum(
    db: Session,
    manager: Employee,
    order: Order,
    cat_a: ExpenseCategory,
    cat_b: ExpenseCategory,
) -> None:
    fin_svc.add_expense(
        db,
        order_id=order.id,
        direction="general",
        category_id=cat_a.id,
        amount=Decimal("10000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )
    fin_svc.add_operating_expense(
        db,
        category_id=cat_a.id,
        amount=Decimal("3000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )
    fin_svc.add_operating_expense(
        db,
        category_id=cat_b.id,
        amount=Decimal("2000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )

    report = fin_svc.monthly_report(db, YEAR, MONTH)

    breakdown_sum = sum(item.amount for item in report.breakdown)
    assert breakdown_sum == report.total_expenses


# ---------------------------------------------------------------------------
# 3. Category only in one source is NOT lost
# ---------------------------------------------------------------------------


def test_category_only_in_order_expenses_not_lost(
    db: Session, manager: Employee, order: Order, cat_a: ExpenseCategory
) -> None:
    """cat_a has order_expense only → must appear in breakdown."""
    fin_svc.add_expense(
        db,
        order_id=order.id,
        direction="general",
        category_id=cat_a.id,
        amount=Decimal("7000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )

    report = fin_svc.monthly_report(db, YEAR, MONTH)
    cat_ids = [item.category_id for item in report.breakdown]
    assert cat_a.id in cat_ids


def test_category_only_in_operating_not_lost(
    db: Session, manager: Employee, cat_b: ExpenseCategory
) -> None:
    """cat_b has operating_expense only → must appear in breakdown."""
    fin_svc.add_operating_expense(
        db,
        category_id=cat_b.id,
        amount=Decimal("4000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )

    report = fin_svc.monthly_report(db, YEAR, MONTH)
    cat_ids = [item.category_id for item in report.breakdown]
    assert cat_b.id in cat_ids


# ---------------------------------------------------------------------------
# 4. Deactivated category with historical expense appears in breakdown
# ---------------------------------------------------------------------------


def test_deactivated_category_appears_in_breakdown(
    db: Session, manager: Employee, order: Order, cat_a: ExpenseCategory
) -> None:
    fin_svc.add_expense(
        db,
        order_id=order.id,
        direction="general",
        category_id=cat_a.id,
        amount=Decimal("9000.00"),
        spent_on=IN_MONTH,
        created_by=manager.id,
    )
    cat_svc.patch_category(db, cat_a.id, is_active=False)

    report = fin_svc.monthly_report(db, YEAR, MONTH)
    cat_ids = [item.category_id for item in report.breakdown]
    assert cat_a.id in cat_ids


# ---------------------------------------------------------------------------
# 5. Month without data → all zeros
# ---------------------------------------------------------------------------


def test_empty_month_returns_zeros(db: Session, manager: Employee) -> None:
    report = fin_svc.monthly_report(db, 2020, 1)
    assert report.revenue == Decimal("0.00")
    assert report.total_expenses == Decimal("0.00")
    assert report.profit == Decimal("0.00")
    assert report.breakdown == []


# ---------------------------------------------------------------------------
# 6. Out-of-month data not counted
# ---------------------------------------------------------------------------


def test_out_of_month_data_excluded(
    db: Session, manager: Employee, order: Order, cat_a: ExpenseCategory
) -> None:
    fin_svc.add_payment(
        db,
        order_id=order.id,
        amount=Decimal("50000.00"),
        received_on=OUT_OF_MONTH,
        created_by=manager.id,
    )
    fin_svc.add_expense(
        db,
        order_id=order.id,
        direction="general",
        category_id=cat_a.id,
        amount=Decimal("10000.00"),
        spent_on=OUT_OF_MONTH,
        created_by=manager.id,
    )

    report = fin_svc.monthly_report(db, YEAR, MONTH)
    assert report.revenue == Decimal("0.00")
    assert report.total_expenses == Decimal("0.00")


# ---------------------------------------------------------------------------
# 7. Amounts stay Decimal; serialised as strings in API
# ---------------------------------------------------------------------------


def test_report_amounts_are_decimal(db: Session, manager: Employee) -> None:
    report = fin_svc.monthly_report(db, YEAR, MONTH)
    assert isinstance(report.revenue, Decimal)
    assert isinstance(report.total_expenses, Decimal)
    assert isinstance(report.profit, Decimal)


def test_report_api_amounts_are_strings(
    client: TestClient, manager: Employee, order: Order, cat_a: ExpenseCategory
) -> None:
    res = client.post(
        f"/api/orders/{order.id}/payments",
        json={"amount": "10000.00", "received_on": str(IN_MONTH)},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201

    report_res = client.get(
        f"/api/reports/monthly?year={YEAR}&month={MONTH}",
        headers=auth(manager.telegram_id),
    )
    assert report_res.status_code == 200
    data = report_res.json()
    assert isinstance(data["revenue"], str)
    assert isinstance(data["profit"], str)
    assert isinstance(data["total_expenses"], str)


# ---------------------------------------------------------------------------
# 8. Access control: worker → 403
# ---------------------------------------------------------------------------


def test_operating_expenses_worker_forbidden(client: TestClient, worker: Employee) -> None:
    res = client.get("/api/operating-expenses", headers=auth(worker.telegram_id))
    assert res.status_code == 403


def test_report_worker_forbidden(client: TestClient, worker: Employee) -> None:
    url = f"/api/reports/monthly?year={YEAR}&month={MONTH}"
    res = client.get(url, headers=auth(worker.telegram_id))
    assert res.status_code == 403
