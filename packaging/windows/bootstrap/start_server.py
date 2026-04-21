from __future__ import annotations

import argparse
import atexit
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the invoice assistant portable server.")
    parser.add_argument("--portable-root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    return parser.parse_args()


def ensure_runtime_dirs(portable_root: Path) -> None:
    for relative_path in ("data", "data/storage", "data/exports", "logs", "runtime"):
        (portable_root / relative_path).mkdir(parents=True, exist_ok=True)


def load_create_app(server_root: Path):
    if str(server_root) not in sys.path:
        sys.path.insert(0, str(server_root))

    from backend.app.main import create_app

    return create_app


def main() -> None:
    args = parse_args()
    portable_root = Path(args.portable_root).expanduser().resolve()
    ensure_runtime_dirs(portable_root)
    runtime_dir = portable_root / "runtime"
    pid_file = runtime_dir / "app.pid"
    url_file = runtime_dir / "app.url"
    app_url = f"http://{args.host}:{args.port}"

    atexit.register(_cleanup_runtime_state, pid_file, url_file)
    threading.Thread(
        target=_publish_runtime_state_when_ready,
        args=(app_url, pid_file, url_file),
        daemon=True,
    ).start()

    server_root = (portable_root / "app" / "server").resolve()
    create_app = load_create_app(server_root)
    app = create_app(
        runtime_overrides={
            "portable_root": portable_root,
            "host": args.host,
            "port": args.port,
            "frontend_static_dir": portable_root / "app" / "server" / "frontend-dist",
        }
    )
    uvicorn.run(app, host=args.host, port=args.port)


def _cleanup_runtime_state(pid_file: Path, url_file: Path) -> None:
    for path in (pid_file, url_file):
        if path.exists():
            path.unlink()


def _publish_runtime_state_when_ready(app_url: str, pid_file: Path, url_file: Path) -> None:
    health_url = f"{app_url}/health"
    homepage_url = f"{app_url}/"
    for _ in range(60):
        if _url_is_ready(health_url) and _url_is_ready(homepage_url):
            pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
            url_file.write_text(f"{app_url}\n", encoding="utf-8")
            return
        time.sleep(0.5)


def _url_is_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError):
        return False


if __name__ == "__main__":
    main()
