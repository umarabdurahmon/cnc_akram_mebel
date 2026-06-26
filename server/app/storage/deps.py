from pathlib import Path

from app.core.config import settings
from app.storage.local import LocalStorage


def get_storage() -> LocalStorage:
    return LocalStorage(Path(settings.storage_root))
