from __future__ import annotations

import argparse
import json
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path


DOCS_DIRNAME = "windows-dev"
WORKSPACE_DIRNAME = "workspace"
EXCLUDED_PATTERNS = (
    ".git",
    ".DS_Store",
    ".venv",
    ".uv-cache",
    ".uv-tools",
    ".tmp",
    ".worktrees",
    ".pytest_cache",
    ".ruff_cache",
    ".playwright",
    ".vite",
    "dist",
    "__pycache__",
    "*.pyc",
    "*.db",
    "*.egg-info",
    "node_modules",
    ".pnpm-store",
    ".npm-cache",
    ".corepack",
    "*.tsbuildinfo",
)


def build_windows_dev_bundle(*, project_root: Path, dist_root: Path, version: str) -> Path:
    project_root = project_root.expanduser().resolve()
    dist_root = dist_root.expanduser().resolve()
    output_dir = dist_root / f"invoice-assistant-windows-dev-{version}"
    zip_output = dist_root / f"{output_dir.name}.zip"
    workspace_output = output_dir / WORKSPACE_DIRNAME
    docs_output = output_dir / DOCS_DIRNAME
    docs_source = project_root / "packaging" / "windows-dev"

    if output_dir.exists():
        shutil.rmtree(output_dir)
    if zip_output.exists():
        zip_output.unlink()

    shutil.copytree(
        project_root,
        workspace_output,
        ignore=shutil.ignore_patterns(*EXCLUDED_PATTERNS),
    )
    shutil.copytree(
        docs_source,
        docs_output,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    manifest = _build_manifest(project_root=project_root, output_dir=output_dir, version=version)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.make_archive(str(output_dir), "zip", root_dir=dist_root, base_dir=output_dir.name)
    return output_dir


def _build_manifest(*, project_root: Path, output_dir: Path, version: str) -> dict[str, object]:
    return {
        "bundle_name": output_dir.name,
        "version": version,
        "built_at": datetime.now(UTC).isoformat(),
        "artifacts": _list_artifacts(output_dir),
        "source_versions": _detect_versions(project_root),
    }


def _list_artifacts(output_dir: Path) -> list[str]:
    return sorted(
        str(path.relative_to(output_dir)).replace("\\", "/")
        for path in output_dir.rglob("*")
        if path.is_file()
    )


def _detect_versions(project_root: Path) -> dict[str, str]:
    versions: dict[str, str] = {}

    workspace_pyproject = project_root / "pyproject.toml"
    if workspace_pyproject.is_file():
        with workspace_pyproject.open("rb") as fh:
            workspace_payload = tomllib.load(fh)
        workspace_version = workspace_payload.get("project", {}).get("version")
        if isinstance(workspace_version, str):
            versions["workspace"] = workspace_version

    backend_pyproject = project_root / "backend" / "pyproject.toml"
    if backend_pyproject.is_file():
        with backend_pyproject.open("rb") as fh:
            backend_payload = tomllib.load(fh)
        backend_version = backend_payload.get("project", {}).get("version")
        if isinstance(backend_version, str):
            versions["backend"] = backend_version

    frontend_package_json = project_root / "frontend" / "package.json"
    if frontend_package_json.is_file():
        frontend_payload = json.loads(frontend_package_json.read_text(encoding="utf-8"))
        frontend_version = frontend_payload.get("version")
        if isinstance(frontend_version, str):
            versions["frontend"] = frontend_version

    return versions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Windows Codex development bundle.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dist-root", default=Path(__file__).resolve().parents[1] / "dist")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = build_windows_dev_bundle(
        project_root=Path(args.project_root),
        dist_root=Path(args.dist_root),
        version=args.version,
    )
    print(output_dir)


if __name__ == "__main__":
    main()
