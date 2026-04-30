from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Sequence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stop the portable invoice assistant.")
    parser.add_argument("--portable-root", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    portable_root = _normalize_portable_root(args.portable_root)
    runtime_dir = portable_root / "runtime"
    logs_dir = portable_root / "logs"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    startup_log = logs_dir / "startup.log"
    pid_file = runtime_dir / "app.pid"
    url_file = runtime_dir / "app.url"

    if not pid_file.is_file():
        print("Invoice Assistant is not running.")
        return 0

    pid_text = pid_file.read_text(encoding="utf-8").strip()
    try:
        pid = int(pid_text)
    except ValueError:
        _cleanup_runtime_files(pid_file, url_file)
        print("Invoice Assistant is not running.")
        return 0

    if not _process_is_running(pid):
        _cleanup_runtime_files(pid_file, url_file)
        print("Invoice Assistant is not running.")
        return 0

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            with startup_log.open("a", encoding="utf-8") as fh:
                fh.write(result.stdout)
                fh.write(result.stderr)
            print("Failed to stop Invoice Assistant. Check logs/startup.log.")
            return 1
    else:
        os.kill(pid, 9)

    _cleanup_runtime_files(pid_file, url_file)
    print("Invoice Assistant stopped.")
    return 0


def _cleanup_runtime_files(pid_file: Path, url_file: Path) -> None:
    for path in (pid_file, url_file):
        if path.exists():
            path.unlink()


def _normalize_portable_root(raw_portable_root: str) -> Path:
    normalized = raw_portable_root.strip().strip('"').rstrip("\\/")
    return Path(normalized).expanduser().resolve()


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


if __name__ == "__main__":
    raise SystemExit(main())
