from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional


@dataclass(frozen=True)
class ReleaseRuntimeConfig:
    database_url: str
    portable_root: Path | None
    data_dir: Path
    logs_dir: Path
    runtime_dir: Path
    frontend_static_dir: Optional[Path]
    storage_root: Path
    host: str
    port: int


def build_runtime_config(
    database_url: str,
    *,
    backend_root: Path,
    overrides: dict[str, Any] | None = None,
) -> ReleaseRuntimeConfig:
    payload = dict(overrides or {})
    portable_root = _coerce_optional_path(payload.get("portable_root"))
    host = str(payload.get("host", "127.0.0.1"))
    port = int(payload.get("port", 18080))

    if portable_root is not None:
        data_dir = (portable_root / "data").resolve()
        logs_dir = (portable_root / "logs").resolve()
        runtime_dir = (portable_root / "runtime").resolve()
        frontend_static_dir = _coerce_optional_path(
            payload.get("frontend_static_dir"),
            default=portable_root / "app" / "server" / "frontend-dist",
        )
        storage_root = (data_dir / "storage").resolve()
        resolved_database_url = f"sqlite:///{data_dir / 'app.db'}"
    else:
        data_dir = _resolve_data_dir(database_url, backend_root)
        logs_dir = (backend_root / "logs").resolve()
        runtime_dir = (backend_root / "runtime").resolve()
        frontend_static_dir = _coerce_optional_path(payload.get("frontend_static_dir"))
        storage_root = (data_dir / "storage").resolve()
        resolved_database_url = database_url

    return ReleaseRuntimeConfig(
        database_url=resolved_database_url,
        portable_root=portable_root,
        data_dir=data_dir,
        logs_dir=logs_dir,
        runtime_dir=runtime_dir,
        frontend_static_dir=frontend_static_dir,
        storage_root=storage_root,
        host=host,
        port=port,
    )


def _coerce_optional_path(value: object, default: Path | None = None) -> Path | None:
    path_value = default if value is None else value
    if path_value is None:
        return None
    return Path(path_value).expanduser().resolve()


def _resolve_data_dir(database_url: str, backend_root: Path) -> Path:
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        sqlite_path = Path(database_url.removeprefix("sqlite:///")).expanduser()
        return sqlite_path.parent.resolve()
    return (backend_root / "data").resolve()
