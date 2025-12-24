"""Local storage helpers for uploaded files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.core.config import Settings, get_settings


class LocalStorageClient:
    """File-system backed storage client used for uploaded assets."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._upload_dir = Path(self._settings.upload_dir)

    def ensure_bucket(self) -> None:
        """Ensure the upload directory exists."""

        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self, object_name: str, data: bytes, content_type: Optional[str]
    ) -> str:
        self.ensure_bucket()
        target_path = self._upload_dir / object_name
        target_path.write_bytes(data)
        return self.object_url(object_name)

    def object_url(self, object_name: str) -> str:
        return f"/uploads/{object_name}"


@lru_cache
def get_storage_client() -> LocalStorageClient:
    return LocalStorageClient()


__all__ = ["LocalStorageClient", "get_storage_client"]
