import hashlib
import hmac
import time
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee
from app.core.config import settings
from app.db.session import get_db
from app.models.employee import Employee, EmployeeRole
from app.models.order import FileKind, OrderFile
from app.schemas.file import OrderFileOut
from app.services import order as order_svc
from app.services import order_file as file_svc
from app.services.file_type import FileTypeError
from app.storage.base import Storage
from app.storage.deps import get_storage

router = APIRouter(tags=["files"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
_TOKEN_TTL = 60  # seconds


def _signing_key() -> bytes:
    return settings.bot_token.encode()


def _issue_token(file_id: int) -> str:
    """Issue a stateless HMAC-signed download token valid for _TOKEN_TTL seconds.

    Format: "<file_id>:<expires_at>:<hex_sig>" — no server state required,
    works across multiple Gunicorn workers.
    """
    expires_at = int(time.time()) + _TOKEN_TTL
    payload = f"{file_id}:{expires_at}".encode()
    sig = hmac.new(_signing_key(), payload, hashlib.sha256).hexdigest()
    return f"{file_id}:{expires_at}:{sig}"


def _validate_token(token: str) -> int | None:
    """Return file_id if the token is valid and not expired, otherwise None."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        file_id = int(parts[0])
        expires_at = int(parts[1])
        sig = parts[2]
    except (ValueError, IndexError):
        return None

    if time.time() > expires_at:
        return None

    payload = f"{file_id}:{expires_at}".encode()
    expected = hmac.new(_signing_key(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None

    return file_id


def _content_disposition(filename: str) -> str:
    """RFC 5987-compliant Content-Disposition; HTTP headers are latin-1 only."""
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "_")
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _require_manager(employee: Employee) -> None:
    if employee.role != EmployeeRole.manager:
        raise HTTPException(status_code=403, detail="Manager role required")


def _get_order_or_404(db: Session, order_id: int) -> None:
    if order_svc.get_order(db, order_id) is None:
        raise HTTPException(status_code=404, detail="Order not found")


def _get_file_or_404(db: Session, order_id: int, file_id: int) -> OrderFile:
    record = file_svc.get_file(db, file_id)
    if record is None or record.order_id != order_id:
        raise HTTPException(status_code=404, detail="File not found")
    return record


async def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read upload in chunks, rejecting if size exceeds limit."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(65536):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/orders/{order_id}/files", response_model=list[OrderFileOut])
def list_files(
    order_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> list[OrderFileOut]:
    _get_order_or_404(db, order_id)
    files = file_svc.list_files(db, order_id)
    return [OrderFileOut.model_validate(f) for f in files]


@router.post("/orders/{order_id}/files", response_model=OrderFileOut, status_code=201)
async def upload_file(
    order_id: int,
    file: UploadFile = File(...),
    kind: FileKind | None = Form(default=None),
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> OrderFileOut:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    data = await _read_limited(file, MAX_FILE_SIZE)
    try:
        record = file_svc.upload(
            db,
            storage,
            order_id,
            employee.id,
            data,
            file.filename or "file",
            kind_override=kind,
        )
    except FileTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    return OrderFileOut.model_validate(record)


@router.get("/orders/{order_id}/files/{file_id}", response_model=OrderFileOut)
def get_file_meta(
    order_id: int,
    file_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> OrderFileOut:
    _get_order_or_404(db, order_id)
    record = _get_file_or_404(db, order_id, file_id)
    return OrderFileOut.model_validate(record)


@router.get("/orders/{order_id}/files/{file_id}/download")
def download_file(
    order_id: int,
    file_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> StreamingResponse:
    _get_order_or_404(db, order_id)
    record = _get_file_or_404(db, order_id, file_id)
    stream = storage.open(record.storage_key)
    return StreamingResponse(
        stream,
        media_type=record.content_type,
        headers={
            "Content-Disposition": _content_disposition(record.original_filename),
            "Content-Length": str(record.size_bytes),
        },
    )


@router.get("/orders/{order_id}/files/{file_id}/thumbnail")
def get_thumbnail(
    order_id: int,
    file_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> StreamingResponse:
    _get_order_or_404(db, order_id)
    record = _get_file_or_404(db, order_id, file_id)
    if not record.thumbnail_key:
        raise HTTPException(status_code=404, detail="No thumbnail available")
    stream = storage.open(record.thumbnail_key)
    return StreamingResponse(stream, media_type="image/jpeg")


@router.post("/orders/{order_id}/files/{file_id}/token")
def create_download_token(
    order_id: int,
    file_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_order_or_404(db, order_id)
    record = _get_file_or_404(db, order_id, file_id)
    token = _issue_token(record.id)
    return {"token": token, "filename": record.original_filename}


@router.get("/dl/{token}")
def download_by_token(
    token: str,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> StreamingResponse:
    file_id = _validate_token(token)
    if file_id is None:
        raise HTTPException(status_code=404, detail="Invalid or expired download token")
    record = db.get(OrderFile, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_obj = storage.open(record.storage_key)

    def _iter_chunks() -> Any:
        try:
            while chunk := file_obj.read(65536):
                yield chunk
        finally:
            file_obj.close()

    return StreamingResponse(
        _iter_chunks(),
        media_type=record.content_type,
        headers={
            "Content-Disposition": _content_disposition(record.original_filename),
            "Content-Length": str(record.size_bytes),
        },
    )


@router.delete("/orders/{order_id}/files/{file_id}", status_code=204)
def delete_file(
    order_id: int,
    file_id: int,
    employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> None:
    _require_manager(employee)
    _get_order_or_404(db, order_id)
    _get_file_or_404(db, order_id, file_id)
    try:
        file_svc.delete_file(db, storage, file_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
