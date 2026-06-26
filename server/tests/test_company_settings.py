"""Несущие инварианты профиля предприятия + сборка футера для клиента."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company import CompanySettings
from app.services import company_settings as company_svc


def test_singleton_check_rejects_second_row(db: Session) -> None:
    """CHECK (id = 1): вторую строку с id != 1 вставить нельзя — БД-инвариант."""
    company_svc.get_or_create(db)  # row id=1
    db.add(CompanySettings(id=2, brand_name="Дубликат"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_get_or_create_is_idempotent(db: Session) -> None:
    first = company_svc.get_or_create(db)
    second = company_svc.get_or_create(db)
    assert first.id == second.id == 1


def test_footer_none_when_all_empty(db: Session) -> None:
    company = company_svc.get_or_create(db)
    assert company_svc.format_footer(company) is None


def test_footer_contains_only_filled_fields(db: Session) -> None:
    company = company_svc.update(db, {"brand_name": "CNC Mebel", "phone": "+998 90 123 45 67"})
    footer = company_svc.format_footer(company)
    assert footer is not None
    assert "CNC Mebel" in footer
    assert "+998 90 123 45 67" in footer
    # Незаполненные поля не дают пустых строк/маркеров
    assert "📍" not in footer
    assert "🌐" not in footer


def test_footer_escapes_markdown_special_chars(db: Session) -> None:
    """Спецсимволы Markdown в контенте экранируются — иначе Telegram отклоняет
    сообщение ('can't parse entities')."""
    company = company_svc.update(
        db, {"website": "instagram.com/cnc_mebel", "footer_note": "Скидка *50%*"}
    )
    footer = company_svc.format_footer(company)
    assert footer is not None
    assert "instagram.com/cnc\\_mebel" in footer
    assert "Скидка \\*50%\\*" in footer


def test_update_blank_strings_normalised_to_none(client, db: Session) -> None:
    """Пустой ввод через API → NULL, чтобы футер не показывал пустые строки."""
    from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
    from tests.conftest import make_test_init_data

    manager = Employee(
        telegram_id=999_500_001,
        full_name="Manager Co",
        role=EmployeeRole.manager,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(manager)
    db.flush()
    headers = {"Authorization": f"tma {make_test_init_data(manager.telegram_id)}"}

    resp = client.patch(
        "/api/company", json={"brand_name": "  ", "phone": " +99890 "}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand_name"] is None
    assert body["phone"] == "+99890"
