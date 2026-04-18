from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(command: list[str]) -> None:
    repo_root = _repo_root()
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(repo_root / ".uv-cache"))
    env.setdefault("UV_TOOL_DIR", str(repo_root / ".uv-tools"))
    completed = subprocess.run(command, cwd=repo_root, env=env, check=False)
    raise SystemExit(completed.returncode)


def pytest_main() -> None:
    _run(
        [
            "uv",
            "run",
            "--project",
            "backend",
            "--extra",
            "dev",
            "python",
            "-m",
            "pytest",
            *sys.argv[1:],
        ]
    )


def ruff_main() -> None:
    _run(
        [
            "uvx",
            "--cache-dir",
            str(_repo_root() / ".uv-cache"),
            "--from",
            "ruff",
            "ruff",
            *sys.argv[1:],
        ]
    )
