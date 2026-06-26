import httpx

from app.core.config import settings


def send_location(
    chat_id: int,
    lat: float,
    lon: float,
    title: str | None = None,
    phone: str | None = None,
) -> None:
    """Send a text message then a location reply-to it, grouping them visually in Telegram."""
    token = settings.bot_token
    if not token:
        return

    reply_to: int | None = None
    if title:
        lines = [title]
        if phone:
            lines.append(f"📞 {phone}")
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines)},
            timeout=8,
        )
        data = resp.json()
        if data.get("ok"):
            reply_to = data["result"]["message_id"]

    loc_payload: dict[str, object] = {"chat_id": chat_id, "latitude": lat, "longitude": lon}
    if reply_to is not None:
        loc_payload["reply_to_message_id"] = reply_to

    httpx.post(
        f"https://api.telegram.org/bot{token}/sendLocation",
        json=loc_payload,
        timeout=8,
    )
