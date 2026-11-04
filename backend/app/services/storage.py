"""Storage abstraction for resume files (local filesystem dev storage, cloud-ready)."""

import os
import stat
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class ResumeStorageProvider(Protocol):
    """Protocol for resume file storage backends (Local, S3, GCS)."""

    @property
    def backend_name(self) -> str:
        """Identifier for the storage provider."""
        ...

    def save(self, stored_filename: str, content: bytes) -> str:
        """Persist raw file bytes under a safe key and return storage path."""
        ...

    def resolve_local_path(self, storage_path: str) -> Path:
        """Return local filesystem Path for serving downloads."""
        ...

    def delete(self, storage_path: str) -> None:
        """Remove stored file if it exists."""
        ...


class LocalResumeStorage:
    """Local filesystem storage implementation for development."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def backend_name(self) -> str:
        return "local"

    def _safe_target(self, relative_name: str) -> Path:
        # Prevent path traversal by taking only the basename
        clean_name = Path(relative_name).name
        target = (self.base_dir / clean_name).resolve()
        if self.base_dir not in target.parents:
            raise ValueError("Invalid storage path traversal attempt.")
        return target

    def save(self, stored_filename: str, content: bytes) -> str:
        target = self._safe_target(stored_filename)
        target.write_bytes(content)
        # Ensure uploaded file has non-executable permissions (read/write only)
        try:
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return target.name

    def resolve_local_path(self, storage_path: str) -> Path:
        return self._safe_target(storage_path)

    def delete(self, storage_path: str) -> None:
        try:
            target = self._safe_target(storage_path)
            if target.exists() and target.is_file():
                target.unlink()
        except Exception:
            pass


def get_resume_storage() -> ResumeStorageProvider:
    """Factory returning the configured storage provider (local for dev, extensible for cloud)."""
    return LocalResumeStorage(settings.RESUME_STORAGE_DIR)

