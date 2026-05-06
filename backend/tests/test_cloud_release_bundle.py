from __future__ import annotations

import importlib.util
import json
import tarfile
import zipfile
from pathlib import Path


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_builder():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "build_cloud_release_bundle.py"
    spec = importlib.util.spec_from_file_location("build_cloud_release_bundle", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_cloud_release_bundle


def _create_fixture_project(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "fixture-project"
    wheels_dir = tmp_path / "wheelhouse"

    _write_file(project_root / "pyproject.toml", "[project]\nname='workspace'\nversion='0.2.0'\n")
    _write_file(project_root / "backend" / "__init__.py", "")
    _write_file(project_root / "backend" / "pyproject.toml", "[project]\nname='backend'\nversion='0.3.0'\n")
    _write_file(project_root / "backend" / "app" / "__init__.py", "")
    _write_file(project_root / "backend" / "app" / "main.py", "def create_app(*args, **kwargs):\n    return 'app'\n")
    _write_file(project_root / "backend" / "tests" / "test_local.py", "def test_local():\n    assert True\n")
    _write_file(project_root / "backend" / "data" / "local.db", "db\n")
    _write_file(project_root / "frontend" / "package.json", '{"version":"0.4.0"}\n')
    _write_file(project_root / "frontend" / "dist" / "index.html", "<html>invoice assistant</html>\n")
    _write_file(project_root / "frontend" / "dist" / "assets" / "app.js", "console.log('ok')\n")
    _write_file(project_root / "packaging" / "offline" / "install_offline.sh", "#!/usr/bin/env bash\necho install\n")
    _write_file(project_root / "packaging" / "offline" / "install_offline.ps1", "Write-Host install\n")
    _write_file(project_root / "packaging" / "offline" / "install_offline.bat", "@echo off\r\necho install\r\n")
    _write_file(project_root / "packaging" / "offline" / "start_invoice_assistant.command", "#!/usr/bin/env bash\necho start\n")
    _write_file(project_root / "packaging" / "offline" / "start_invoice_assistant.bat", "@echo off\r\necho start\r\n")
    _write_file(project_root / "packaging" / "offline" / "stop_invoice_assistant.command", "#!/usr/bin/env bash\necho stop\n")
    _write_file(project_root / "packaging" / "offline" / "stop_invoice_assistant.bat", "@echo off\r\necho stop\r\n")
    _write_file(project_root / "packaging" / "windows" / "bootstrap" / "start_server.py", "print('start server')\n")
    _write_file(project_root / "packaging" / "windows" / "bootstrap" / "stop_portable.py", "print('stop server')\n")
    _write_file(wheels_dir / "fastapi-0.0.0-py3-none-any.whl", "wheel\n")
    return project_root, wheels_dir


def test_build_cloud_release_bundle_creates_windows_zip(tmp_path: Path) -> None:
    build_cloud_release_bundle = _load_builder()
    project_root, wheels_dir = _create_fixture_project(tmp_path)
    dist_root = tmp_path / "dist-offline"

    result = build_cloud_release_bundle(
        project_root=project_root,
        dist_root=dist_root,
        wheels_dir=wheels_dir,
        version="v1.2.3",
        platform_os="windows",
        platform_machine="amd64",
        archive_format="zip",
    )

    assert result.bundle_dir == dist_root / "invoice-assistant-offline-v1.2.3-windows-amd64"
    assert result.archive_path == dist_root / "invoice-assistant-offline-v1.2.3-windows-amd64.zip"
    assert result.archive_path.is_file()
    with zipfile.ZipFile(result.archive_path) as archive:
        names = set(archive.namelist())
    assert "invoice-assistant-offline-v1.2.3-windows-amd64/install_offline.bat" in names
    assert "invoice-assistant-offline-v1.2.3-windows-amd64/start_invoice_assistant.bat" in names
    assert "invoice-assistant-offline-v1.2.3-windows-amd64/wheels/fastapi-0.0.0-py3-none-any.whl" in names
    assert "invoice-assistant-offline-v1.2.3-windows-amd64/app/server/backend/app/main.py" in names
    assert "invoice-assistant-offline-v1.2.3-windows-amd64/app/server/frontend-dist/index.html" in names

    manifest = json.loads((result.bundle_dir / "bundle-manifest.json").read_text(encoding="utf-8"))
    assert manifest["platform_os"] == "windows"
    assert manifest["platform_machine"] == "amd64"
    assert manifest["archive_name"] == result.archive_path.name
    assert "backend/tests/test_local.py" not in "\n".join(manifest["artifacts"])
    assert "backend/data/local.db" not in "\n".join(manifest["artifacts"])


def test_build_cloud_release_bundle_creates_macos_tar_with_executable_scripts(tmp_path: Path) -> None:
    build_cloud_release_bundle = _load_builder()
    project_root, wheels_dir = _create_fixture_project(tmp_path)
    dist_root = tmp_path / "dist-offline"

    result = build_cloud_release_bundle(
        project_root=project_root,
        dist_root=dist_root,
        wheels_dir=wheels_dir,
        version="v1.2.3",
        platform_os="macos",
        platform_machine="arm64",
        archive_format="tar.gz",
    )

    assert result.bundle_dir == dist_root / "invoice-assistant-offline-v1.2.3-macos-arm64"
    assert result.archive_path == dist_root / "invoice-assistant-offline-v1.2.3-macos-arm64.tar.gz"
    assert result.archive_path.is_file()
    with tarfile.open(result.archive_path, "r:gz") as archive:
        names = set(archive.getnames())
        modes = {member.name: member.mode for member in archive.getmembers()}
    assert "invoice-assistant-offline-v1.2.3-macos-arm64/install_offline.sh" in names
    assert "invoice-assistant-offline-v1.2.3-macos-arm64/start_invoice_assistant.command" in names
    assert "invoice-assistant-offline-v1.2.3-macos-arm64/wheels/fastapi-0.0.0-py3-none-any.whl" in names
    assert "invoice-assistant-offline-v1.2.3-macos-arm64/app/bootstrap/start_server.py" in names
    assert "invoice-assistant-offline-v1.2.3-macos-arm64/app/server/frontend-dist/assets/app.js" in names
    assert modes["invoice-assistant-offline-v1.2.3-macos-arm64/install_offline.sh"] & 0o111
    assert modes["invoice-assistant-offline-v1.2.3-macos-arm64/start_invoice_assistant.command"] & 0o111
    assert modes["invoice-assistant-offline-v1.2.3-macos-arm64/stop_invoice_assistant.command"] & 0o111


def test_powershell_installer_stops_on_native_command_failures() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "packaging"
        / "offline"
        / "install_offline.ps1"
    ).read_text(encoding="utf-8")

    assert "$PSNativeCommandUseErrorActionPreference = $true" in script
    assert "if ($LASTEXITCODE -ne 0)" in script
