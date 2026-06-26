from app.services.client_view import ClientOrderView
from bot.i18n import ru as _ru
from bot.i18n import uz as _uz


def get_lang(language_code: str | None) -> str:
    if language_code and language_code.startswith("uz"):
        return "uz"
    return "ru"


def msg_welcome(lang: str) -> str:
    return _uz.WELCOME if lang == "uz" else _ru.WELCOME


def msg_enter_code(lang: str) -> str:
    return _uz.ENTER_CODE if lang == "uz" else _ru.ENTER_CODE


def msg_not_found(lang: str) -> str:
    return _uz.NOT_FOUND if lang == "uz" else _ru.NOT_FOUND


def msg_rate_limited(lang: str) -> str:
    return _uz.RATE_LIMITED if lang == "uz" else _ru.RATE_LIMITED


def msg_order_status(lang: str, view: ClientOrderView, footer: str | None = None) -> str:
    tmpl = _uz if lang == "uz" else _ru
    return tmpl.format_order_status(view, footer)
