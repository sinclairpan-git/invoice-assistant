from __future__ import annotations

import argparse
import json
import os
import shutil
import tarfile
import tomllib
import zipfile
from collections import namedtuple
from datetime import UTC, datetime
from pathlib import Path


BundleBuildResult = namedtuple("BundleBuildResult", ["bundle_dir", "archive_path"])

BACKEND_RUNTIME_FILES = ("__init__.py", "pyproject.toml")
BACKEND_RUNTIME_DIRS = ("app",)
OFFLINE_SCRIPT_NAMES = (
    "install_offline.bat",
    "install_offline.ps1",
    "install_offline.sh",
    "start_invoice_assistant.bat",
    "start_invoice_assistant.ps1",
    "start_invoice_assistant.command",
    "stop_invoice_assistant.bat",
    "stop_invoice_assistant.ps1",
    "stop_invoice_assistant.command",
    "windows_path_alias.ps1",
)
POSIX_EXECUTABLE_SUFFIXES = (".sh", ".command")


def build_cloud_release_bundle(
    *,
    project_root: Path,
    dist_root: Path,
    wheels_dir: Path,
    version: str,
    platform_os: str,
    platform_machine: str,
    archive_format: str,
) -> BundleBuildResult:
    project_root = project_root.expanduser().resolve()
    dist_root = dist_root.expanduser().resolve()
    wheels_dir = wheels_dir.expanduser().resolve()
    platform_os = _normalize_platform_os(platform_os)
    platform_machine = _normalize_platform_machine(platform_machine)
    archive_format = _normalize_archive_format(archive_format)
    bundle_name = f"invoice-assistant-offline-{version}-{platform_os}-{platform_machine}"
    bundle_dir = dist_root / bundle_name

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    dist_root.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True)

    _create_runtime_dirs(bundle_dir)
    _copy_backend_runtime_tree(project_root / "backend", bundle_dir / "app" / "server" / "backend")
    _copy_required_tree(project_root / "frontend" / "dist", bundle_dir / "app" / "server" / "frontend-dist")
    _copy_required_tree(project_root / "packaging" / "windows" / "bootstrap", bundle_dir / "app" / "bootstrap")
    _copy_required_tree(wheels_dir, bundle_dir / "wheels")
    _copy_offline_scripts(project_root / "packaging" / "offline", bundle_dir)
    _write_runtime_requirements(project_root / "backend" / "pyproject.toml", bundle_dir / "runtime-requirements.txt")

    archive_path = _archive_bundle(
        dist_root=dist_root,
        bundle_dir=bundle_dir,
        archive_format=archive_format,
    )
    manifest = _build_manifest(
        project_root=project_root,
        bundle_dir=bundle_dir,
        archive_path=archive_path,
        version=version,
        platform_os=platform_os,
        platform_machine=platform_machine,
        archive_format=archive_format,
    )
    (bundle_dir / "bundle-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    archive_path = _archive_bundle(
        dist_root=dist_root,
        bundle_dir=bundle_dir,
        archive_format=archive_format,
    )
    return BundleBuildResult(bundle_dir=bundle_dir, archive_path=archive_path)


def _normalize_platform_os(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {"darwin": "macos", "win32": "windows", "win": "windows"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"windows", "macos", "linux"}:
        raise ValueError(f"Unsupported platform_os: {value}")
    return normalized


def _normalize_platform_machine(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {"x86_64": "amd64", "x64": "amd64", "aarch64": "arm64"}
    return aliases.get(normalized, normalized)


def _normalize_archive_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"zip", "tar.gz"}:
        raise ValueError(f"Unsupported archive_format: {value}")
    return normalized


def _create_runtime_dirs(bundle_dir: Path) -> None:
    for relative_path in ("data", "data/storage", "data/exports", "logs", "runtime"):
        (bundle_dir / relative_path).mkdir(parents=True, exist_ok=True)


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


def _copy_backend_runtime_tree(source_root: Path, destination_root: Path) -> None:
    if not source_root.is_dir():
        raise FileNotFoundError(f"Missing required directory: {source_root}")
    destination_root.mkdir(parents=True, exist_ok=True)
    for filename in BACKEND_RUNTIME_FILES:
        _copy_required_file(source_root / filename, destination_root / filename)
    for directory in BACKEND_RUNTIME_DIRS:
        _copy_required_tree(source_root / directory, destination_root / directory)


def _copy_offline_scripts(source_root: Path, bundle_dir: Path) -> None:
    for script_name in OFFLINE_SCRIPT_NAMES:
        destination = bundle_dir / script_name
        _copy_required_file(source_root / script_name, destination)
        if destination.suffix in POSIX_EXECUTABLE_SUFFIXES:
            destination.chmod(destination.stat().st_mode | 0o755)


def _write_runtime_requirements(backend_pyproject: Path, output_path: Path) -> None:
    with backend_pyproject.open("rb") as fh:
        payload = tomllib.load(fh)
    dependencies = payload.get("project", {}).get("dependencies", [])
    if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
        raise ValueError("backend pyproject.toml must define project.dependencies as a string list")
    output_path.write_text("\n".join(dependencies) + "\n", encoding="utf-8")


def _archive_bundle(*, dist_root: Path, bundle_dir: Path, archive_format: str) -> Path:
    archive_path = dist_root / f"{bundle_dir.name}.{archive_format}"
    if archive_path.exists():
        archive_path.unlink()
    if archive_format == "zip":
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(dist_root))
        return archive_path

    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(bundle_dir, arcname=bundle_dir.name, filter=_tarinfo_with_portable_modes)
    return archive_path


def _tarinfo_with_portable_modes(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    if tarinfo.isfile() and tarinfo.name.endswith(POSIX_EXECUTABLE_SUFFIXES):
        tarinfo.mode |= 0o755
    return tarinfo


def _build_manifest(
    *,
    project_root: Path,
    bundle_dir: Path,
    archive_path: Path,
    version: str,
    platform_os: str,
    platform_machine: str,
    archive_format: str,
) -> dict[str, object]:
    return {
        "bundle_format_version": 1,
        "bundle_name": bundle_dir.name,
        "version": version,
        "platform_os": platform_os,
        "platform_machine": platform_machine,
        "archive_format": archive_format,
        "archive_name": archive_path.name,
        "built_at": datetime.now(UTC).isoformat(),
        "source_versions": _detect_versions(project_root),
        "artifacts": _list_artifacts(bundle_dir),
    }


def _list_artifacts(bundle_dir: Path) -> list[str]:
    return sorted(
        str(path.relative_to(bundle_dir)).replace("\\", "/")
        for path in bundle_dir.rglob("*")
        if path.is_file()
    )


def _detect_versions(project_root: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for key, path in {
        "workspace": project_root / "pyproject.toml",
        "backend": project_root / "backend" / "pyproject.toml",
    }.items():
        if path.is_file():
            with path.open("rb") as fh:
                payload = tomllib.load(fh)
            version = payload.get("project", {}).get("version")
            if isinstance(version, str):
                versions[key] = version

    frontend_package = project_root / "frontend" / "package.json"
    if frontend_package.is_file():
        payload = json.loads(frontend_package.read_text(encoding="utf-8"))
        version = payload.get("version")
        if isinstance(version, str):
            versions["frontend"] = version
    return versions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a cloud release bundle for one platform.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--platform-os", required=True)
    parser.add_argument("--platform-machine", required=True)
    parser.add_argument("--archive-format", choices=["zip", "tar.gz"], required=True)
    parser.add_argument("--wheels-dir", required=True)
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dist-root", default=Path(__file__).resolve().parents[1] / "dist-offline")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_cloud_release_bundle(
        project_root=Path(args.project_root),
        dist_root=Path(args.dist_root),
        wheels_dir=Path(args.wheels_dir),
        version=args.version,
        platform_os=args.platform_os,
        platform_machine=args.platform_machine,
        archive_format=args.archive_format,
    )
    print(result.archive_path)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    main()
