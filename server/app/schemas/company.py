from pydantic import BaseModel, ConfigDict, field_validator


class CompanySettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_name: str | None
    phone: str | None
    address: str | None
    working_hours: str | None
    website: str | None
    footer_note: str | None


class CompanySettingsUpdate(BaseModel):
    brand_name: str | None = None
    phone: str | None = None
    address: str | None = None
    working_hours: str | None = None
    website: str | None = None
    footer_note: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> object:
        """Normalise blank input to NULL so empty strings never reach the footer."""
        if isinstance(v, str):
            stripped = v.strip()
            return stripped or None
        return v
