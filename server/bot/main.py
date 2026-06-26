import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.services import attendance as attendance_svc
from app.services import client_view as cv_svc
from bot.i18n import (
    get_lang,
    msg_enter_code,
    msg_not_found,
    msg_order_status,
    msg_rate_limited,
    msg_welcome,
)
from bot.throttle import RateLimiter

logger = logging.getLogger(__name__)

_rate_limiter = RateLimiter(limit=5, window_seconds=60.0)


async def _handle_code(message: Message, raw_code: str) -> None:
    user = message.from_user
    if user is None:
        return
    lang = get_lang(user.language_code)

    if not _rate_limiter.is_allowed(user.id):
        await message.answer(msg_rate_limited(lang))
        return

    with Session(engine) as db:
        order = cv_svc.find_order_by_code(db, raw_code)
        if order is None:
            await message.answer(msg_not_found(lang))
            return

        view = cv_svc.serialize_for_client(db, order)

    await message.answer(msg_order_status(lang, view), parse_mode="HTML")


async def _midnight_rollover_loop() -> None:
    """Background task: at shop-timezone midnight, roll over any open visits."""
    while True:
        now_local = datetime.now(tz=ZoneInfo(settings.shop_tz))
        tomorrow_midnight = (now_local + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await asyncio.sleep((tomorrow_midnight - now_local).total_seconds())
        try:
            with Session(engine) as db:
                count = attendance_svc.rollover_midnight_visits(db)
                db.commit()
            if count:
                logger.info("Midnight rollover: %d visit(s) carried over", count)
        except Exception:
            logger.exception("Midnight rollover failed")


def main() -> None:
    token = settings.bot_token
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        user = message.from_user
        if user is None:
            return
        lang = get_lang(user.language_code)

        # Deep-link: /start <code>
        text = message.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            await _handle_code(message, parts[1])
        else:
            # Show Mini App button if URL is configured, otherwise plain text
            keyboard = None
            if settings.miniapp_url:
                open_label = "Открыть рабочий кабинет" if lang == "ru" else "Ish kabinetini ochish"
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=open_label,
                                web_app=WebAppInfo(url=settings.miniapp_url),
                            )
                        ]
                    ]
                )
            await message.answer(msg_welcome(lang), reply_markup=keyboard)

    @dp.startup()
    async def on_startup() -> None:
        asyncio.create_task(_midnight_rollover_loop())

    @dp.message()
    async def handle_text(message: Message) -> None:
        text = (message.text or "").strip()
        if not text:
            user = message.from_user
            lang = get_lang(user.language_code if user else None)
            await message.answer(msg_enter_code(lang))
            return
        await _handle_code(message, text)

    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
