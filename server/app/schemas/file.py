from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order import FileKind


class OrderFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    original_filename: str
    storage_key: str
    content_type: str
    size_bytes: int
    kind: FileKind
    thumbnail_key: str | None
    uploaded_by: int
    uploaded_at: datetime
