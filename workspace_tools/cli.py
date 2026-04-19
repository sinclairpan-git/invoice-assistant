from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from workspace_tools.version_control_policy import git_tracked_file_policy_violations


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _tracked_file_policy_violations() -> list[str]:
    return git_tracked_file_policy_violations(_repo_root())


def _enforce_tracked_file_policy() -> None:
    violations = _tracked_file_policy_violations()
    if not violations:
        return

    sys.stderr.write("Tracked file policy violations:\n")
    for violation in violations:
        sys.stderr.write(f"- {violation}\n")
    raise SystemExit(2)


def _run(command: list[str]) -> None:
    repo_root = _repo_root()
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(repo_root / ".uv-cache"))
    env.setdefault("UV_TOOL_DIR", str(repo_root / ".uv-tools"))
    completed = subprocess.run(command, cwd=repo_root, env=env, check=False)
    raise SystemExit(completed.returncode)


def pytest_main() -> None:
    _enforce_tracked_file_policy()
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
    _enforce_tracked_file_policy()
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


def tracked_files_main() -> None:
    violations = _tracked_file_policy_violations()
    if violations:
        sys.stderr.write("Tracked file policy violations:\n")
        for violation in violations:
            sys.stderr.write(f"- {violation}\n")
        raise SystemExit(2)

    print("Tracked file policy: OK")
    raise SystemExit(0)
