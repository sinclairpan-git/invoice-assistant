from __future__ import annotations

import ipaddress
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class OpenPathRequest(BaseModel):
    path: str


def open_path_in_file_manager(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
            return
        subprocess.run(["xdg-open", str(path)], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("打开系统文件管理器失败。") from exc


@router.post("/open-path")
def open_runtime_path(
    payload: OpenPathRequest,
    request: Request,
) -> dict[str, object]:
    ensure_runtime_open_allowed(request)
    opened_path = resolve_runtime_open_path(
        requested_path=payload.path,
        data_dir=Path(request.app.state.runtime_config.data_dir),
    )
    try:
        open_path_in_file_manager(opened_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="打开本地文件夹失败。") from exc
    return {
        "item": {
            "requested_path": payload.path,
            "opened_path": str(opened_path),
        }
    }


def resolve_runtime_open_path(*, requested_path: str, data_dir: Path) -> Path:
    if not requested_path.strip():
        raise HTTPException(status_code=400, detail="缺少要打开的路径。")

    raw_path = Path(requested_path).expanduser()
    candidate = (
        raw_path.resolve(strict=False)
        if raw_path.is_absolute()
        else (data_dir / raw_path).resolve(strict=False)
    )
    try:
        candidate.relative_to(data_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="仅允许打开便携包数据目录内的路径。",
        ) from exc

    if not candidate.exists():
        raise HTTPException(status_code=404, detail="目标路径不存在。")

    return candidate.parent if candidate.is_file() else candidate


def ensure_runtime_open_allowed(request: Request) -> None:
    runtime_config = request.app.state.runtime_config
    if runtime_config.portable_root is None:
        raise HTTPException(status_code=403, detail="仅便携包运行态支持打开本地路径。")

    client_host = request.client.host if request.client else None
    if not is_loopback_host(client_host):
        raise HTTPException(status_code=403, detail="仅允许本机请求打开本地路径。")


def is_loopback_host(host: str | None) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
