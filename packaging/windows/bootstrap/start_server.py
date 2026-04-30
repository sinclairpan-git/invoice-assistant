from __future__ import annotations

import argparse
import atexit
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Sequence

DEFAULT_PORT_POOL_SIZE = 10


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the invoice assistant portable server.")
    parser.add_argument("--portable-root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    return parser.parse_args(argv)


def ensure_runtime_dirs(portable_root: Path) -> None:
    for relative_path in ("data", "data/storage", "data/exports", "logs", "runtime"):
        (portable_root / relative_path).mkdir(parents=True, exist_ok=True)


def load_create_app(server_root: Path):
    if str(server_root) not in sys.path:
        sys.path.insert(0, str(server_root))

    from backend.app.main import create_app

    return create_app


def load_uvicorn():
    import uvicorn

    return uvicorn


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    portable_root = Path(args.portable_root).expanduser().resolve()
    ensure_runtime_dirs(portable_root)
    startup_log = portable_root / "logs" / "startup.log"
    runtime_dir = portable_root / "runtime"
    pid_file = runtime_dir / "app.pid"
    url_file = runtime_dir / "app.url"
    _append_startup_log(startup_log, f"Bootstrap starting with Python: {sys.executable}")
    _append_startup_log(startup_log, f"Portable root: {portable_root}")

    try:
        selected_port = _select_available_port(args.host, args.port)
        app_url = f"http://{args.host}:{selected_port}"
        _append_startup_log(startup_log, f"Selected listen port: {selected_port}")
        _append_startup_log(startup_log, f"App URL: {app_url}")

        atexit.register(_cleanup_runtime_state, pid_file, url_file)
        pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
        url_file.write_text(f"{app_url}\n", encoding="utf-8")
        threading.Thread(
            target=_publish_runtime_state_when_ready,
            args=(app_url, pid_file, url_file, startup_log),
            daemon=True,
        ).start()

        server_root = (portable_root / "app" / "server").resolve()
        frontend_static_dir = portable_root / "app" / "server" / "frontend-dist"
        _append_startup_log(startup_log, f"Server root: {server_root}")
        _append_startup_log(startup_log, f"Frontend static dir: {frontend_static_dir.resolve()}")

        create_app = load_create_app(server_root)
        app = create_app(
            runtime_overrides={
                "portable_root": portable_root,
                "host": args.host,
                "port": selected_port,
                "frontend_static_dir": frontend_static_dir,
            }
        )
        _append_startup_log(startup_log, "Application loaded, starting uvicorn.")
        uvicorn = load_uvicorn()
        uvicorn.run(app, host=args.host, port=selected_port)
        _append_startup_log(startup_log, "Uvicorn.run returned.")
        return 0
    except Exception:
        _append_startup_failure(startup_log, "Portable bootstrap failed.")
        return 1


def _cleanup_runtime_state(pid_file: Path, url_file: Path) -> None:
    for path in (pid_file, url_file):
        if path.exists():
            path.unlink()


def _publish_runtime_state_when_ready(
    app_url: str,
    pid_file: Path,
    url_file: Path,
    startup_log: Path,
) -> None:
    health_url = f"{app_url}/health"
    homepage_url = f"{app_url}/"
    for _ in range(60):
        if _url_is_ready(health_url) and _url_is_ready(homepage_url):
            pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
            url_file.write_text(f"{app_url}\n", encoding="utf-8")
            _append_startup_log(startup_log, "Runtime readiness probe succeeded.")
            return
        time.sleep(0.5)
    _append_startup_log(startup_log, "Runtime readiness probe timed out.")


def _url_is_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError):
        return False


def _append_startup_log(startup_log: Path, message: str) -> None:
    startup_log.parent.mkdir(parents=True, exist_ok=True)
    with startup_log.open("a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")


def _append_startup_failure(startup_log: Path, message: str) -> None:
    _append_startup_log(startup_log, message)
    _append_startup_log(startup_log, traceback.format_exc().rstrip())


def _select_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + DEFAULT_PORT_POOL_SIZE):
        if _can_bind_port(host, port):
            return port
    last_port = preferred_port + DEFAULT_PORT_POOL_SIZE - 1
    raise RuntimeError(f"No available port in {preferred_port}-{last_port}")


def _can_bind_port(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
