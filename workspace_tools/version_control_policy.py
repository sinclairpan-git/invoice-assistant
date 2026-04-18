from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath
from typing import Iterable

PROJECT_CONFIG = ".ai-sdlc/project/config/project-config.yaml"
LEGACY_EXECUTION_LOG_EXCEPTION = (
    "specs/002-invoice-assistant-runtime-hardening/execution-log.md"
)


def tracked_file_policy_violations(paths: Iterable[str]) -> list[str]:
    violations: list[str] = []

    for raw_path in sorted({path for path in paths if path}):
        path = raw_path.replace("\\", "/")

        if path == PROJECT_CONFIG:
            violations.append(
                f"{path}: project-config.yaml is runtime adapter state and must stay untracked"
            )
            continue

        if path.startswith(".ai-sdlc/local/"):
            violations.append(
                f"{path}: .ai-sdlc/local/ is runtime state and must stay untracked"
            )
            continue

        if path.startswith(".ai-sdlc/state/"):
            violations.append(
                f"{path}: .ai-sdlc/state/ is runtime state and must stay untracked"
            )
            continue

        if path.startswith(".ai-sdlc/work-items/") and not _is_allowed_work_item_artifact(
            path
        ):
            violations.append(
                f"{path}: .ai-sdlc/work-items/ only allows reviewer-decision*.yaml as tracked formal artifacts"
            )
            continue

        if path.endswith("/execution-log.md") and path != LEGACY_EXECUTION_LOG_EXCEPTION:
            violations.append(
                f"{path}: execution-log.md is a legacy mirror; only the approved specs/002 exception may stay tracked"
            )

    return violations


def git_tracked_file_policy_violations(repo_root: Path) -> list[str]:
    tracked_files = _git_ls_files(repo_root)
    return tracked_file_policy_violations(tracked_files)


def _git_ls_files(repo_root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    return [line for line in completed.stdout.splitlines() if line]


def _is_allowed_work_item_artifact(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.startswith("reviewer-decision") and name.endswith(".yaml")
