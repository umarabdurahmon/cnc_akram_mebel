"""Order file upload, thumbnail generation, and management."""

import io
import uuid

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import FileKind, OrderFile
from app.services.file_type import MIME_TO_EXT, detect_type, sanitize_filename
from app.storage.base import Storage

_THUMBNAIL_MAX_PX = (300, 300)
_THUMBNAIL_QUALITY = 80


def _generate_key(order_id: int, ext: str) -> str:
    return f"orders/{order_id}/{uuid.uuid4().hex}{ext}"


def _generate_thumbnail(data: bytes) -> bytes | None:
    """Return JPEG thumbnail bytes, or None if generation fails."""
    try:
        Image.MAX_IMAGE_PIXELS = 100_000_000  # decompression bomb guard
        raw = Image.open(io.BytesIO(data))
        oriented = ImageOps.exif_transpose(raw)
        oriented.thumbnail(_THUMBNAIL_MAX_PX, Image.Resampling.LANCZOS)
        if oriented.mode not in ("RGB", "RGBA"):
            oriented = oriented.convert("RGB")
        out = io.BytesIO()
        oriented.save(out, "JPEG", quality=_THUMBNAIL_QUALITY)
        return out.getvalue()
    except Exception:
        return None


def upload(
    db: Session,
    storage: Storage,
    order_id: int,
    uploaded_by: int,
    data: bytes,
    original_filename: str,
    kind_override: FileKind | None = None,
) -> OrderFile:
    """
    Upload sequence (consistency):
      1. Detect type (raises FileTypeError if not allowed)
      2. Write file bytes to storage
      3. Generate and write thumbnail if image
      4. Flush DB row — on failure best-effort delete both storage objects
    """
    mime, default_kind = detect_type(data)
    kind = kind_override if kind_override is not None else default_kind
    ext = MIME_TO_EXT.get(mime, "")
    key = _generate_key(order_id, ext)
    safe_name = sanitize_filename(original_filename)

    # Write main file first
    storage.save(key, data)

    thumb_key: str | None = None
    if default_kind == FileKind.photo:
        thumb_data = _generate_thumbnail(data)
        if thumb_data is not None:
            thumb_key = _generate_key(order_id, ".jpg")
            try:
                storage.save(thumb_key, thumb_data)
            except Exception:
                thumb_key = None  # thumbnail failure doesn't fail the upload

    record = OrderFile(
        order_id=order_id,
        original_filename=safe_name,
        storage_key=key,
        content_type=mime,
        size_bytes=len(data),
        kind=kind,
        thumbnail_key=thumb_key,
        uploaded_by=uploaded_by,
    )
    db.add(record)
    try:
        db.flush()
    except Exception:
        storage.delete(key)
        if thumb_key:
            storage.delete(thumb_key)
        raise

    return record


def delete_file(db: Session, storage: Storage, file_id: int) -> OrderFile:
    """
    Delete sequence (consistency):
      1. Delete DB row (in caller's transaction)
      2. Best-effort delete storage objects after flush
    Returns the deleted record for reference.
    Raises ValueError if file not found.
    """
    record = db.get(OrderFile, file_id)
    if record is None:
        raise ValueError(f"File {file_id} not found")
    key = record.storage_key
    thumb_key = record.thumbnail_key
    db.delete(record)
    db.flush()

    # Storage deletion is best-effort: an orphaned file is less harmful than a dangling DB ref
    storage.delete(key)
    if thumb_key:
        storage.delete(thumb_key)

    return record


def list_files(db: Session, order_id: int) -> list[OrderFile]:
    return list(
        db.execute(
            select(OrderFile).where(OrderFile.order_id == order_id).order_by(OrderFile.uploaded_at)
        )
        .scalars()
        .all()
    )


def get_file(db: Session, file_id: int) -> OrderFile | None:
    return db.get(OrderFile, file_id)
