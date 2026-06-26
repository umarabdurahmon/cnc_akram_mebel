"""Несущие инварианты: загрузка файлов, хранилище, миниатюры."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.main import app
from app.models.employee import Employee, EmployeeLanguage, EmployeeRole
from app.models.order import Order
from app.services import order as order_svc
from app.storage.deps import get_storage
from app.storage.local import LocalStorage
from tests.conftest import make_test_init_data

# ---------------------------------------------------------------------------
# Storage override fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_storage(tmp_path: Path) -> LocalStorage:
    storage = LocalStorage(tmp_path)
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage, None)


# ---------------------------------------------------------------------------
# Employee / order fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_300_001,
        full_name="Manager 6",
        role=EmployeeRole.manager,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def worker(db: Session) -> Employee:
    emp = Employee(
        telegram_id=999_300_002,
        full_name="Worker 6",
        role=EmployeeRole.worker,
        language=EmployeeLanguage.ru,
        is_active=True,
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def order(db: Session, manager: Employee) -> Order:
    return order_svc.create_order(
        db, created_by=manager.id, customer_name="Клиент 6", title="Шкаф 6"
    )


def auth(telegram_id: int) -> dict[str, str]:
    return {"Authorization": f"tma {make_test_init_data(telegram_id)}"}


def _make_jpeg() -> bytes:
    """Return bytes of a minimal valid 10x10 JPEG."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, "JPEG")
    return buf.getvalue()


def _make_dwg() -> bytes:
    """Return bytes with DWG magic (AC1015 header)."""
    return b"AC1015" + b"\x00" * 100


# ---------------------------------------------------------------------------
# 1. Image upload → row + file + thumbnail
# ---------------------------------------------------------------------------


def test_upload_image_creates_thumbnail(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    order: Order,
) -> None:
    jpeg = _make_jpeg()
    res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("photo.jpg", jpeg, "image/jpeg")},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["kind"] == "photo"
    assert data["thumbnail_key"] is not None
    assert data["content_type"] == "image/jpeg"
    # Both storage objects must exist
    assert (tmp_storage._root / data["storage_key"]).exists()
    assert (tmp_storage._root / data["thumbnail_key"]).exists()


# ---------------------------------------------------------------------------
# 2. DWG upload → file saved, thumbnail_key null
# ---------------------------------------------------------------------------


def test_upload_dwg_no_thumbnail(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    order: Order,
) -> None:
    dwg = _make_dwg()
    res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("plan.dwg", dwg, "application/octet-stream")},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["kind"] == "drawing"
    assert data["thumbnail_key"] is None
    assert (tmp_storage._root / data["storage_key"]).exists()


# ---------------------------------------------------------------------------
# 3. storage_key is server-generated; traversal in filename has no effect
# ---------------------------------------------------------------------------


def test_storage_key_is_server_generated(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    order: Order,
) -> None:
    jpeg = _make_jpeg()
    res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("../../etc/passwd.jpg", jpeg, "image/jpeg")},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    data = res.json()
    key = data["storage_key"]
    # Key must stay within the storage root (no traversal)
    resolved = (tmp_storage._root / key).resolve()
    assert resolved.is_relative_to(tmp_storage._root)
    # Displayed filename is sanitized (no raw path separators)
    assert "/" not in data["original_filename"]
    assert "\\" not in data["original_filename"]


# ---------------------------------------------------------------------------
# 4. Size limit → 413
# ---------------------------------------------------------------------------


def test_upload_too_large_rejected(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    order: Order,
) -> None:
    from app.api import files as files_api

    original_limit = files_api.MAX_FILE_SIZE
    files_api.MAX_FILE_SIZE = 5  # 5 bytes limit for the test
    try:
        jpeg = _make_jpeg()  # > 5 bytes
        res = client.post(
            f"/api/orders/{order.id}/files",
            files={"file": ("big.jpg", jpeg, "image/jpeg")},
            headers=auth(manager.telegram_id),
        )
        assert res.status_code == 413
    finally:
        files_api.MAX_FILE_SIZE = original_limit


# ---------------------------------------------------------------------------
# 5. Forbidden type → 415
# ---------------------------------------------------------------------------


def test_upload_forbidden_type_rejected(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    order: Order,
) -> None:
    bad_data = b"this is just random text that matches no magic bytes"
    res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("script.sh", bad_data, "text/plain")},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 415


# ---------------------------------------------------------------------------
# 6. Corrupt image → file saved, thumbnail skipped, no 500
# ---------------------------------------------------------------------------


def test_corrupt_image_saves_without_thumbnail(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    order: Order,
) -> None:
    # Valid JPEG magic but garbage body → Pillow will fail to open
    corrupt = b"\xff\xd8\xff" + b"\x00" * 50
    res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("corrupt.jpg", corrupt, "image/jpeg")},
        headers=auth(manager.telegram_id),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["thumbnail_key"] is None
    assert (tmp_storage._root / data["storage_key"]).exists()


# ---------------------------------------------------------------------------
# 7. Upload/delete — manager only; worker can download
# ---------------------------------------------------------------------------


def test_upload_requires_manager(
    client: TestClient,
    tmp_storage: LocalStorage,
    worker: Employee,
    order: Order,
) -> None:
    res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("x.jpg", _make_jpeg(), "image/jpeg")},
        headers=auth(worker.telegram_id),
    )
    assert res.status_code == 403


def test_delete_requires_manager(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    worker: Employee,
    order: Order,
) -> None:
    # Upload as manager
    jpeg = _make_jpeg()
    upload_res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("x.jpg", jpeg, "image/jpeg")},
        headers=auth(manager.telegram_id),
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    # Worker tries to delete → 403
    del_res = client.delete(
        f"/api/orders/{order.id}/files/{file_id}",
        headers=auth(worker.telegram_id),
    )
    assert del_res.status_code == 403


def test_worker_can_download(
    client: TestClient,
    tmp_storage: LocalStorage,
    manager: Employee,
    worker: Employee,
    order: Order,
) -> None:
    jpeg = _make_jpeg()
    upload_res = client.post(
        f"/api/orders/{order.id}/files",
        files={"file": ("x.jpg", jpeg, "image/jpeg")},
        headers=auth(manager.telegram_id),
    )
    file_id = upload_res.json()["id"]

    # Worker downloads via storage interface (streaming)
    dl_res = client.get(
        f"/api/orders/{order.id}/files/{file_id}/download",
        headers=auth(worker.telegram_id),
    )
    assert dl_res.status_code == 200
    # Response body is the file content (from storage, not FS path)
    assert dl_res.content == jpeg
