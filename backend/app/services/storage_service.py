from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


class StorageError(ValueError):
    """Base storage error."""


class InvalidFileTypeError(StorageError):
    """Raised when an unsupported file is uploaded."""


class DuplicateOriginalFileError(StorageError):
    """Raised when an upload would overwrite an immutable original."""


class InvalidFileNameError(StorageError):
    """Raised when the original file name is unsafe."""


@dataclass(frozen=True)
class StoredOriginal:
    original_filename: str
    storage_path: str
    absolute_path: Path
    file_sha256: str


class StorageService:
    def __init__(self, storage_root: Path | str) -> None:
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def save_original(self, batch_no: str, filename: str, content: bytes) -> StoredOriginal:
        safe_name = Path(filename).name
        if safe_name != filename or safe_name in {"", ".", ".."}:
            raise InvalidFileNameError(f"Unsafe original filename: {filename!r}")
        if Path(filename).suffix.lower() != ".pdf":
            raise InvalidFileTypeError(f"Unsupported file type for {filename!r}; only PDF is allowed.")

        batch_dir = self.storage_root / "originals" / batch_no
        batch_dir.mkdir(parents=True, exist_ok=True)
        target_path = batch_dir / safe_name
        if target_path.exists():
            raise DuplicateOriginalFileError(
                f"Original file already exists for batch {batch_no!r}: {safe_name!r}."
            )

        target_path.write_bytes(content)
        file_sha256 = hashlib.sha256(content).hexdigest()
        relative_path = target_path.relative_to(self.storage_root.parent).as_posix()
        return StoredOriginal(
            original_filename=safe_name,
            storage_path=relative_path,
            absolute_path=target_path,
            file_sha256=file_sha256,
        )
