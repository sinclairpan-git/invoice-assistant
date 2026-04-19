from __future__ import annotations

from pathlib import Path


def _ci_workflow_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    workflow = repo_root / ".github" / "workflows" / "ci.yml"
    return workflow.read_text(encoding="utf-8")


def test_ci_workflow_runs_repo_policy_and_backend_checks() -> None:
    content = _ci_workflow_text()

    assert "pull_request:" in content
    assert "push:" in content
    assert 'branches: ["main"]' in content
    assert "uv run tracked-files" in content
    assert "uv run ruff check workspace_tools backend/tests backend/app" in content
    assert "uv run pytest backend/tests -q" in content


def test_ci_workflow_runs_frontend_test_and_build() -> None:
    content = _ci_workflow_text()

    assert "pnpm --dir frontend install --frozen-lockfile" in content
    assert "pnpm --dir frontend test" in content
    assert "pnpm --dir frontend build" in content
