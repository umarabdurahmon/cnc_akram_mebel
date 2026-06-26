from sqlalchemy.orm import Session

from app.models.company import CompanySettings

_SINGLETON_ID = 1

# Legacy-Markdown special chars: an odd one in user content leaves an entity
# unclosed and Telegram rejects the whole message ("can't parse entities").
_MD_SPECIAL = ("\\", "_", "*", "`", "[")


def _md_escape(text: str) -> str:
    for ch in _MD_SPECIAL:
        text = text.replace(ch, "\\" + ch)
    return text


def get_or_create(db: Session) -> CompanySettings:
    """Return the single enterprise-profile row, creating an empty one if absent."""
    company = db.get(CompanySettings, _SINGLETON_ID)
    if company is None:
        company = CompanySettings(id=_SINGLETON_ID)
        db.add(company)
        db.flush()
    return company


def update(db: Session, data: dict[str, str | None]) -> CompanySettings:
    """Partial update of the enterprise profile (only the provided fields)."""
    company = get_or_create(db)
    for field, value in data.items():
        setattr(company, field, value)
    db.flush()
    return company


def format_footer(company: CompanySettings) -> str | None:
    """Build the client-facing footer from non-empty profile fields.

    Returns None when nothing is filled. Content only (no translated labels) —
    enterprise data is shown as the manager entered it, identical for any language.
    """
    lines: list[str] = []
    if company.brand_name:
        lines.append(f"🏢 *{_md_escape(company.brand_name)}*")
    if company.phone:
        lines.append(f"📞 {_md_escape(company.phone)}")
    if company.address:
        lines.append(f"📍 {_md_escape(company.address)}")
    if company.working_hours:
        lines.append(f"🕒 {_md_escape(company.working_hours)}")
    if company.website:
        lines.append(f"🌐 {_md_escape(company.website)}")
    if company.footer_note:
        lines.append(_md_escape(company.footer_note))
    return "\n".join(lines) if lines else None
