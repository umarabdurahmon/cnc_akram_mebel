import html
from datetime import date

from app.services.client_view import ClientOrderView

WELCOME = (
    "Здравствуйте! Введите код вашего заказа, чтобы узнать его статус.\n"
    "Код указан в вашем договоре или сообщении от менеджера."
)

ENTER_CODE = "Введите код заказа:"

NOT_FOUND = "Заказ с таким кодом не найден. Проверьте код и попробуйте ещё раз."

RATE_LIMITED = "Слишком много запросов. Пожалуйста, подождите немного."

_SEP = "─────────────────"


def _progress_bar(x: int, y: int, width: int = 10) -> str:
    filled = round(x / y * width)
    return "▓" * filled + "░" * (width - filled)


def _e(s: str) -> str:
    return html.escape(s)


def format_order_status(view: ClientOrderView, footer: str | None = None) -> str:
    lines: list[str] = []

    lines.append(f"📦 <b>{_e(view.title)}</b>")
    if view.description:
        lines.append(f"<i>{_e(view.description)}</i>")

    lines.append(_SEP)

    if view.is_closed:
        lines.append("✅ <b>Заказ готов!</b>")
    elif view.stage_name:
        if view.stage_x is not None and view.stage_y:
            bar = _progress_bar(view.stage_x, view.stage_y)
            lines.append(f"🔄 <b>{_e(view.stage_name)}</b> — этап {view.stage_x} из {view.stage_y}")
            lines.append(bar)
        else:
            lines.append(f"🔄 <b>{_e(view.stage_name)}</b>")
    else:
        lines.append("🔄 Этап не задан")

    if view.deadline:
        deadline_str = view.deadline.strftime("%d.%m.%Y")
        if not view.is_closed and view.deadline < date.today():
            lines.append(f"⚠️ Срок: {deadline_str} — <b>просрочен</b>")
        else:
            lines.append(f"📅 Срок: {deadline_str}")

    if view.public_note:
        lines.append(_SEP)
        lines.append(f"💬 {_e(view.public_note)}")

    if footer:
        lines.append(_SEP)
        lines.append(_e(footer))

    return "\n".join(lines)
