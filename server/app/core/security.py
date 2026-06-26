from datetime import UTC, datetime, timedelta

from aiogram.utils.web_app import WebAppInitData, safe_parse_webapp_init_data

from app.core.config import settings

AUTH_MAX_AGE = timedelta(hours=24)


def verify_init_data(raw: str) -> WebAppInitData:
    """Валидирует initData от Telegram Mini App.

    Бросает ValueError при невалидной подписи или устаревшем auth_date.
    Никогда не доверяй данным без проверки этой функцией.
    """
    data = safe_parse_webapp_init_data(token=settings.bot_token, init_data=raw)
    auth_dt = data.auth_date
    if auth_dt.tzinfo is None:
        auth_dt = auth_dt.replace(tzinfo=UTC)
    if datetime.now(UTC) - auth_dt > AUTH_MAX_AGE:
        raise ValueError("initData expired")
    return data
