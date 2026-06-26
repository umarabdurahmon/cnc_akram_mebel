import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.services import client_view as cv_svc
from app.services import company_settings as company_svc
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

        # Save customer_chat_id so future notifications can be sent via this bot.
        if message.chat.id and order.customer_chat_id != message.chat.id:
            order.customer_chat_id = message.chat.id
            db.commit()

        view = cv_svc.serialize_for_client(db, order)
        footer = company_svc.format_footer(company_svc.get_or_create(db))

    await message.answer(msg_order_status(lang, view, footer), parse_mode="HTML")


def main() -> None:
    token = settings.client_bot_token
    if not token:
        raise RuntimeError("CLIENT_BOT_TOKEN is not set")

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
            await message.answer(msg_welcome(lang))

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
