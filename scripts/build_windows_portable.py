from __future__ import annotations

import argparse
import json
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path


DOC_FILENAMES = ("用户指引.html", "README-技术维护.md")
REQUIRED_ROOT_FILES = ("启动发票助手.bat", "停止发票助手.bat")


def build_portable_bundle(
    *,
    project_root: Path,
    dist_root: Path,
    version: str,
    python_runtime_root: Path | None = None,
) -> Path:
    project_root = project_root.expanduser().resolve()
    dist_root = dist_root.expanduser().resolve()
    output_dir = dist_root / f"invoice-assistant-windows-x64-{version}"
    runtime_source = _resolve_python_runtime_root(project_root, python_runtime_root)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    zip_output = dist_root / f"{output_dir.name}.zip"
    if zip_output.exists():
        zip_output.unlink()

    output_dir.mkdir(parents=True, exist_ok=True)
    _create_runtime_dirs(output_dir)

    packaging_root = project_root / "packaging" / "windows"
    _copy_required_tree(
        runtime_source,
        output_dir / "app" / "python",
    )
    _copy_required_tree(
        project_root / "frontend" / "dist",
        output_dir / "app" / "server" / "frontend-dist",
    )
    _copy_required_tree(
        project_root / "backend",
        output_dir / "app" / "server" / "backend",
    )
    _copy_required_tree(
        packaging_root / "bootstrap",
        output_dir / "app" / "bootstrap",
    )

    for filename in REQUIRED_ROOT_FILES:
        _copy_required_file(packaging_root / filename, output_dir / filename)
    for filename in DOC_FILENAMES:
        _copy_optional_file(packaging_root / filename, output_dir / filename)

    manifest = _build_manifest(
        project_root=project_root,
        output_dir=output_dir,
        version=version,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.make_archive(str(output_dir), "zip", root_dir=dist_root, base_dir=output_dir.name)
    return output_dir


def _create_runtime_dirs(output_dir: Path) -> None:
    for relative_path in ("data/storage", "data/exports", "logs", "runtime"):
        (output_dir / relative_path).mkdir(parents=True, exist_ok=True)


def _copy_required_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Missing required directory: {source}")
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _copy_required_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Missing required file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_optional_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


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


def _resolve_python_runtime_root(project_root: Path, python_runtime_root: Path | None) -> Path:
    runtime_root = (
        python_runtime_root.expanduser().resolve()
        if python_runtime_root is not None
        else (project_root / "packaging" / "windows" / "python").resolve()
    )
    if not runtime_root.is_dir():
        raise FileNotFoundError(f"Missing required Python runtime directory: {runtime_root}")
    python_exe = runtime_root / "python.exe"
    if not python_exe.is_file():
        raise FileNotFoundError(f"Missing required Python runtime file: {python_exe}")
    site_packages_dir = runtime_root / "Lib" / "site-packages"
    if not site_packages_dir.is_dir():
        raise FileNotFoundError(f"Missing required Python runtime directory: {site_packages_dir}")
    return runtime_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Windows portable invoice assistant bundle.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dist-root", default=Path(__file__).resolve().parents[1] / "dist")
    parser.add_argument("--python-runtime-root")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = build_portable_bundle(
        project_root=Path(args.project_root),
        dist_root=Path(args.dist_root),
        version=args.version,
        python_runtime_root=Path(args.python_runtime_root) if args.python_runtime_root else None,
    )
    print(output_dir)


if __name__ == "__main__":
    main()
