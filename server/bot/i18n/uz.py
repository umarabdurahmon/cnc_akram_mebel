import html
from datetime import date

from app.services.client_view import ClientOrderView

WELCOME = (
    "Salom! Buyurtmangiz holatini bilish uchun buyurtma kodini kiriting.\n"
    "Kod shartnomangizda yoki menejer xabarida ko'rsatilgan."
)

ENTER_CODE = "Buyurtma kodini kiriting:"

NOT_FOUND = "Bunday kodli buyurtma topilmadi. Kodni tekshirib, qayta urinib ko'ring."

RATE_LIMITED = "Juda ko'p so'rov. Iltimos, biroz kuting."

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
        lines.append("✅ <b>Buyurtma tayyor!</b>")
    elif view.stage_name:
        if view.stage_x is not None and view.stage_y:
            bar = _progress_bar(view.stage_x, view.stage_y)
            lines.append(
                f"🔄 <b>{_e(view.stage_name)}</b> — {view.stage_x} / {view.stage_y} bosqich"
            )
            lines.append(bar)
        else:
            lines.append(f"🔄 <b>{_e(view.stage_name)}</b>")
    else:
        lines.append("🔄 Bosqich belgilanmagan")

    if view.deadline:
        deadline_str = view.deadline.strftime("%d.%m.%Y")
        if not view.is_closed and view.deadline < date.today():
            lines.append(f"⚠️ Muddat: {deadline_str} — <b>kechikdi</b>")
        else:
            lines.append(f"📅 Muddat: {deadline_str}")

    if view.public_note:
        lines.append(_SEP)
        lines.append(f"💬 {_e(view.public_note)}")

    if footer:
        lines.append(_SEP)
        lines.append(_e(footer))

    return "\n".join(lines)
