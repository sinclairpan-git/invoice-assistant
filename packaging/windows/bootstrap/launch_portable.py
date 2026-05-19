from __future__ import annotations

import argparse
import os
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Sequence


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18080
DEFAULT_READY_TIMEOUT_SECONDS = 60.0
READY_PROBE_INTERVAL_SECONDS = 0.5
READY_PROBE_TIMEOUT_SECONDS = 0.5
RUNTIME_DIRS = ("data", "data/storage", "data/exports", "logs", "runtime")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the portable invoice assistant.")
    parser.add_argument("--portable-root", required=True)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_READY_TIMEOUT_SECONDS,
        help="Maximum seconds to wait for the local service to become ready.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    portable_root = _normalize_portable_root(args.portable_root)
    ensure_runtime_dirs(portable_root)
    startup_log = portable_root / "logs" / "startup.log"

    _append_startup_log(startup_log, f"Launcher start: {portable_root}")

    python_exe = portable_root / "app" / "python" / "python.exe"
    start_script = portable_root / "app" / "bootstrap" / "start_server.py"

    if not python_exe.is_file():
        _append_startup_log(startup_log, "Missing bundled Python runtime.")
        return 1
    if not start_script.is_file():
        _append_startup_log(startup_log, "Missing portable bootstrap script.")
        return 1

    existing_url = _resolve_existing_running_url(portable_root)
    if existing_url is not None:
        _append_startup_log(startup_log, f"Reusing running app at {existing_url}")
        if args.no_browser:
            _append_startup_log(
                startup_log,
                f"Launcher ready without opening browser for {existing_url}",
            )
        else:
            _open_url(existing_url)
        return 0

    try:
        _probe_python_runtime(python_exe, startup_log)
        _start_server_process(
            portable_root=portable_root,
            python_exe=python_exe,
            start_script=start_script,
        )
        app_url = _wait_for_ready_url(portable_root, startup_log, args.timeout_seconds)
    except Exception as exc:
        _append_startup_log(startup_log, f"Launcher failed: {exc}")
        return 1

    if args.no_browser:
        _append_startup_log(startup_log, f"Launcher ready without opening browser for {app_url}")
    else:
        _open_url(app_url)
        _append_startup_log(startup_log, f"Launcher opened browser for {app_url}")
    return 0


def ensure_runtime_dirs(portable_root: Path) -> None:
    for relative_path in RUNTIME_DIRS:
        (portable_root / relative_path).mkdir(parents=True, exist_ok=True)


def _normalize_portable_root(raw_portable_root: str) -> Path:
    normalized = raw_portable_root.strip().strip('"').rstrip("\\/")
    return Path(normalized).expanduser().resolve()


def _resolve_existing_running_url(portable_root: Path) -> str | None:
    pid_file = portable_root / "runtime" / "app.pid"
    url_file = portable_root / "runtime" / "app.url"
    if not pid_file.is_file() or not url_file.is_file():
        return None

    pid_text = pid_file.read_text(encoding="utf-8").strip()
    if not pid_text:
        _cleanup_runtime_files(pid_file, url_file)
        return None
    try:
        pid = int(pid_text)
    except ValueError:
        _cleanup_runtime_files(pid_file, url_file)
        return None

    if not _process_is_running(pid):
        _cleanup_runtime_files(pid_file, url_file)
        return None

    app_url = url_file.read_text(encoding="utf-8").strip()
    if not app_url:
        _cleanup_runtime_files(pid_file, url_file)
        return None
    if _is_app_ready(app_url):
        return app_url
    _cleanup_runtime_files(pid_file, url_file)
    return None


def _probe_python_runtime(python_exe: Path, startup_log: Path) -> None:
    _append_startup_log(startup_log, f"Probing bundled Python runtime: {python_exe}")
    result = subprocess.run(
        [str(python_exe), "-c", "import sys; print(sys.executable); print(sys.version)"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        _append_startup_log(startup_log, result.stdout.rstrip())
    if result.stderr:
        _append_startup_log(startup_log, result.stderr.rstrip())
    if result.returncode != 0:
        raise RuntimeError(f"Bundled Python runtime probe failed with exit code {result.returncode}")


def _start_server_process(*, portable_root: Path, python_exe: Path, start_script: Path) -> None:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [
            str(python_exe),
            str(start_script),
            "--portable-root",
            str(portable_root),
            "--host",
            DEFAULT_HOST,
            "--port",
            str(DEFAULT_PORT),
        ],
        cwd=portable_root,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )


def _wait_for_ready_url(portable_root: Path, startup_log: Path, timeout_seconds: float) -> str:
    url_file = portable_root / "runtime" / "app.url"
    deadline = time.monotonic() + max(timeout_seconds, READY_PROBE_INTERVAL_SECONDS)
    while time.monotonic() < deadline:
        if url_file.is_file():
            app_url = url_file.read_text(encoding="utf-8").strip()
            if app_url and _is_app_ready(app_url):
                _append_startup_log(startup_log, f"Ready URL detected: {app_url}")
                return app_url
        time.sleep(READY_PROBE_INTERVAL_SECONDS)
    raise RuntimeError("Timed out waiting for runtime/app.url")


def _is_app_ready(app_url: str) -> bool:
    return _url_ready(f"{app_url}/health") and _url_ready(f"{app_url}/")


def _url_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=READY_PROBE_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError):
        return False


def _process_is_running(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=False,
            check=False,
        )
        stdout = result.stdout or b""
        return str(pid).encode("ascii") in stdout

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _cleanup_runtime_files(pid_file: Path, url_file: Path) -> None:
    for path in (pid_file, url_file):
        if path.exists():
            path.unlink()


def _open_url(app_url: str) -> None:
    if os.name == "nt" and hasattr(os, "startfile"):
        os.startfile(app_url)  # type: ignore[attr-defined]
        return
    webbrowser.open(app_url)


def _append_startup_log(startup_log: Path, message: str) -> None:
    startup_log.parent.mkdir(parents=True, exist_ok=True)
    with startup_log.open("a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")


if __name__ == "__main__":
    raise SystemExit(main())
