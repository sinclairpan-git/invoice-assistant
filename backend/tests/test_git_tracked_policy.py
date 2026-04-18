from __future__ import annotations

from pathlib import Path

from workspace_tools.version_control_policy import (
    git_tracked_file_policy_violations,
    tracked_file_policy_violations,
)


def test_tracked_file_policy_flags_runtime_artifacts_but_allows_exceptions() -> None:
    violations = tracked_file_policy_violations(
        [
            ".ai-sdlc/project/config/project-config.yaml",
            ".ai-sdlc/local/session.json",
            ".ai-sdlc/state/cache.db",
            ".ai-sdlc/work-items/005-attachment-list-recognition/runtime.yaml",
            ".ai-sdlc/work-items/005-attachment-list-recognition/reviewer-decision-pre-close.yaml",
            "specs/002-invoice-assistant-runtime-hardening/execution-log.md",
            "specs/006-future-item/execution-log.md",
        ]
    )

    assert violations == [
        ".ai-sdlc/local/session.json: .ai-sdlc/local/ is runtime state and must stay untracked",
        ".ai-sdlc/project/config/project-config.yaml: project-config.yaml is runtime adapter state and must stay untracked",
        ".ai-sdlc/state/cache.db: .ai-sdlc/state/ is runtime state and must stay untracked",
        ".ai-sdlc/work-items/005-attachment-list-recognition/runtime.yaml: .ai-sdlc/work-items/ only allows reviewer-decision*.yaml as tracked formal artifacts",
        "specs/006-future-item/execution-log.md: execution-log.md is a legacy mirror; only the approved specs/002 exception may stay tracked",
    ]


def test_current_repo_tracked_files_follow_version_control_policy() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    assert git_tracked_file_policy_violations(repo_root) == []
