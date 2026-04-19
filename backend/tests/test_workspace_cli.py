from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_pytest_wrapper_delegates_to_backend_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from workspace_tools import cli

    calls: dict[str, object] = {}
    repo_root = Path(__file__).resolve().parents[2]

    monkeypatch.setattr(
        sys, "argv", ["pytest", "-q", "backend/tests/test_progress_reporting.py"]
    )

    def fake_run(
        command: list[str], *, cwd: Path, env: dict[str, str], check: bool
    ) -> object:
        calls["command"] = command
        calls["cwd"] = cwd
        calls["env"] = env
        calls["check"] = check

        class Result:
            returncode = 0

        return Result()

    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.setattr(cli, "git_tracked_file_policy_violations", lambda repo_root: [])
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc_info:
        cli.pytest_main()

    assert exc_info.value.code == 0
    assert calls["command"] == [
        "uv",
        "run",
        "--project",
        "backend",
        "--extra",
        "dev",
        "python",
        "-m",
        "pytest",
        "-q",
        "backend/tests/test_progress_reporting.py",
    ]
    assert calls["cwd"] == repo_root
    assert calls["check"] is False
    assert calls["env"]["UV_CACHE_DIR"] == str(repo_root / ".uv-cache")
    assert calls["env"]["UV_TOOL_DIR"] == str(repo_root / ".uv-tools")


def test_ruff_wrapper_delegates_to_uvx(monkeypatch: pytest.MonkeyPatch) -> None:
    from workspace_tools import cli

    calls: dict[str, object] = {}
    repo_root = Path(__file__).resolve().parents[2]

    monkeypatch.setattr(sys, "argv", ["ruff", "check", "backend/app"])

    def fake_run(
        command: list[str], *, cwd: Path, env: dict[str, str], check: bool
    ) -> object:
        calls["command"] = command
        calls["cwd"] = cwd
        calls["env"] = env
        calls["check"] = check

        class Result:
            returncode = 0

        return Result()

    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.setattr(cli, "git_tracked_file_policy_violations", lambda repo_root: [])
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc_info:
        cli.ruff_main()

    assert exc_info.value.code == 0
    assert calls["command"] == [
        "uvx",
        "--cache-dir",
        str(repo_root / ".uv-cache"),
        "--from",
        "ruff",
        "ruff",
        "check",
        "backend/app",
    ]
    assert calls["cwd"] == repo_root
    assert calls["check"] is False
    assert calls["env"]["UV_CACHE_DIR"] == str(repo_root / ".uv-cache")
    assert calls["env"]["UV_TOOL_DIR"] == str(repo_root / ".uv-tools")


def test_pytest_wrapper_rejects_tracked_file_policy_violations(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from workspace_tools import cli

    monkeypatch.setattr(sys, "argv", ["pytest", "-q"])
    monkeypatch.setattr(
        cli,
        "git_tracked_file_policy_violations",
        lambda repo_root: [
            ".ai-sdlc/project/config/project-config.yaml: runtime artifact"
        ],
    )

    def fail_run(**_: object) -> object:
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(cli.subprocess, "run", fail_run)

    with pytest.raises(SystemExit) as exc_info:
        cli.pytest_main()

    assert exc_info.value.code == 2
    assert "Tracked file policy violations:" in capsys.readouterr().err


def test_ruff_wrapper_rejects_tracked_file_policy_violations(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from workspace_tools import cli

    monkeypatch.setattr(sys, "argv", ["ruff", "check", "backend/app"])
    monkeypatch.setattr(
        cli,
        "git_tracked_file_policy_violations",
        lambda repo_root: [".ai-sdlc/state/cache.db: runtime artifact"],
    )

    def fail_run(**_: object) -> object:
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(cli.subprocess, "run", fail_run)

    with pytest.raises(SystemExit) as exc_info:
        cli.ruff_main()

    assert exc_info.value.code == 2
    assert ".ai-sdlc/state/cache.db: runtime artifact" in capsys.readouterr().err


def test_tracked_files_wrapper_reports_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from workspace_tools import cli

    monkeypatch.setattr(sys, "argv", ["tracked-files"])
    monkeypatch.setattr(cli, "git_tracked_file_policy_violations", lambda repo_root: [])

    with pytest.raises(SystemExit) as exc_info:
        cli.tracked_files_main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "Tracked file policy: OK"
