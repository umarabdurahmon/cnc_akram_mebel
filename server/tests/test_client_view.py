"""Несущие инварианты: безопасный сериализатор клиента + поиск по коду."""

import dataclasses
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.models.order import ProductionStage
from app.services import catalog as catalog_svc
from app.services import order as order_svc
from app.services import order_employee as oe_svc
from app.services.client_view import ClientOrderView, find_order_by_code, serialize_for_client
from bot.throttle import RateLimiter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_400_001,
        full_name="Manager 7",
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
        telegram_id=999_400_002,
        full_name="Worker 7",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def stages(db: Session) -> list[ProductionStage]:
    s1 = catalog_svc.create_stage(db, "Раскрой", position=1)
    s2 = catalog_svc.create_stage(db, "Сборка", position=2)
    s3 = catalog_svc.create_stage(db, "Покраска", position=3)
    return [s1, s2, s3]


# ---------------------------------------------------------------------------
# 1. Serializer: whitelist — sensitive fields never leak
# ---------------------------------------------------------------------------


def test_serializer_output_fields_are_exact_whitelist() -> None:
    """ClientOrderView has exactly the safe fields and nothing else."""
    allowed = {
        "title",
        "description",
        "deadline",
        "public_note",
        "is_closed",
        "stage_name",
        "stage_x",
        "stage_y",
    }
    actual = {f.name for f in dataclasses.fields(ClientOrderView)}
    assert actual == allowed, f"Unexpected fields: {actual - allowed}"


def test_serializer_no_money_no_files_no_employees_no_id(
    db: Session, manager: Employee, worker: Employee, stages: list[ProductionStage]
) -> None:
    """Order with all sensitive data → serializer output contains none of it."""
    order = order_svc.create_order(
        db,
        created_by=manager.id,
        customer_name="Sensitive Client",
        title="Сейф-тест",
        total_amount=Decimal("999999.00"),
        customer_contact="+99890000000",
        description="secret description",
        current_stage_id=stages[0].id,
    )
    oe_svc.attach(db, order.id, worker.id, can_change_status=True, attached_by=manager.id)

    view = serialize_for_client(db, order)

    # Check that a serialized dict (or repr) does not contain money
    view_dict = dataclasses.asdict(view)
    assert "total_amount" not in view_dict
    assert "customer_contact" not in view_dict
    assert "customer_chat_id" not in view_dict
    assert "internal_number" not in view_dict
    assert "id" not in view_dict
    assert "created_by" not in view_dict
    assert "public_code" not in view_dict
    # No money value leaking through any string field
    for val in view_dict.values():
        assert "999999" not in str(val)


# ---------------------------------------------------------------------------
# 2. Stage X of Y — active stages only
# ---------------------------------------------------------------------------


def test_stage_x_of_y_counts_active_only(
    db: Session, manager: Employee, stages: list[ProductionStage]
) -> None:
    """Y counts only active stages; deactivated stage not in Y."""
    # Deactivate stage 3 (Покраска)
    catalog_svc.patch_stage(db, stages[2].id, is_active=False)

    order = order_svc.create_order(
        db,
        created_by=manager.id,
        customer_name="X",
        title="T",
        current_stage_id=stages[1].id,  # Сборка = position 2
    )
    view = serialize_for_client(db, order)

    assert view.stage_name == "Сборка"
    assert view.stage_x == 2  # position 2 in active list
    assert view.stage_y == 2  # only 2 active (Раскрой + Сборка)


def test_stage_null_no_crash(db: Session, manager: Employee) -> None:
    """Order with no stage → stage fields are all None, no exception."""
    order = order_svc.create_order(db, created_by=manager.id, customer_name="X", title="T")
    view = serialize_for_client(db, order)
    assert view.stage_name is None
    assert view.stage_x is None


def test_deactivated_stage_shows_name_no_position(
    db: Session, manager: Employee, stages: list[ProductionStage]
) -> None:
    """Order's current stage later deactivated → name shown, stage_x=None, no crash."""
    order = order_svc.create_order(
        db,
        created_by=manager.id,
        customer_name="X",
        title="T",
        current_stage_id=stages[0].id,  # Раскрой
    )
    # Deactivate that stage after the order was set
    catalog_svc.patch_stage(db, stages[0].id, is_active=False)

    view = serialize_for_client(db, order)
    assert view.stage_name == "Раскрой"
    assert view.stage_x is None  # not in active list


# ---------------------------------------------------------------------------
# 3. Code lookup: normalisation
# ---------------------------------------------------------------------------


def test_lookup_uppercase_normalisation(db: Session, manager: Employee) -> None:
    order = order_svc.create_order(db, created_by=manager.id, customer_name="C", title="T")
    code = order.public_code  # e.g. "K7QX2M"
    assert find_order_by_code(db, code.lower()) is not None
    assert find_order_by_code(db, f"  {code}  ") is not None


def test_lookup_unknown_code_returns_none(db: Session) -> None:
    result = find_order_by_code(db, "XXXXXX")
    assert result is None


def test_lookup_no_hint_on_not_found(db: Session) -> None:
    """Unknown code: service returns None, nothing more."""
    result = find_order_by_code(db, "ZZZZZZ")
    # Just None — no exception, no partial data
    assert result is None


# ---------------------------------------------------------------------------
# 4. Deep-link: /start <code> resolves to status
# ---------------------------------------------------------------------------


def test_deeplink_code_resolves_to_status(db: Session, manager: Employee) -> None:
    """Simulates /start payload lookup — the same find_order_by_code path."""
    order = order_svc.create_order(
        db, created_by=manager.id, customer_name="Deeplink Client", title="Диван"
    )
    # Simulate /start ABCDEF → parse payload → lookup
    found = find_order_by_code(db, order.public_code)
    assert found is not None
    assert found.id == order.id


# ---------------------------------------------------------------------------
# 5. Rate limiter
# ---------------------------------------------------------------------------


def test_rate_limiter_allows_up_to_limit() -> None:
    rl = RateLimiter(limit=3, window_seconds=60.0)
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is False  # 4th call blocked


def test_rate_limiter_different_users_independent() -> None:
    rl = RateLimiter(limit=2, window_seconds=60.0)
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is False
    # User 2 unaffected by user 1's exhaustion
    assert rl.is_allowed(2) is True
    assert rl.is_allowed(2) is True
    assert rl.is_allowed(2) is False


def test_rate_limiter_window_expires() -> None:
    import time

    rl = RateLimiter(limit=2, window_seconds=0.05)
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is True
    assert rl.is_allowed(1) is False
    time.sleep(0.1)  # window expires
    assert rl.is_allowed(1) is True  # window reset
