from __future__ import annotations

from pathlib import Path


def _workflow_text(name: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    workflow = repo_root / ".github" / "workflows" / name
    return workflow.read_text(encoding="utf-8")


def test_pr_checks_workflow_runs_repo_policy_backend_and_frontend_checks() -> None:
    content = _workflow_text("pr-checks.yml")

    assert "pull_request:" in content
    assert "branches:" in content
    assert "main" in content
    assert "uv run tracked-files" in content
    assert "uv run ruff check workspace_tools backend/tests backend/app" in content
    assert "uv run pytest backend/tests -q" in content
    assert "pnpm --dir frontend install --frozen-lockfile" in content
    assert "pnpm --dir frontend test" in content
    assert "pnpm --dir frontend build" in content


def test_cross_platform_core_workflow_checks_linux_macos_and_windows() -> None:
    content = _workflow_text("cross-platform-core.yml")

    assert "workflow_dispatch:" in content
    assert "pull_request:" in content
    assert "ubuntu-latest" in content
    assert "macos-latest" in content
    assert "windows-latest" in content
    assert "uv run pytest" in content
    assert "pnpm --dir frontend build" in content


def test_release_build_workflow_builds_cloud_artifacts_for_each_platform() -> None:
    content = _workflow_text("release-build.yml")

    assert "workflow_dispatch:" in content
    assert "windows-latest" in content
    assert "macos-latest" in content
    assert "ubuntu-latest" in content
    assert "scripts/build_cloud_release_bundle.py" in content
    assert "invoice-assistant-offline-*.zip" in content
    assert "invoice-assistant-offline-*.tar.gz" in content
    assert "gh release upload" in content


def test_release_artifact_smoke_downloads_and_checks_release_assets() -> None:
    content = _workflow_text("release-artifact-smoke.yml")

    assert "release:" in content
    assert "published" in content
    assert "windows-latest" in content
    assert "macos-latest" in content
    assert "ubuntu-latest" in content
    assert "gh release download" in content
    assert "invoice-assistant-offline-*-windows-*.zip" in content
    assert "invoice-assistant-offline-*-${RELEASE_ASSET_OS}-*.tar.gz" in content
