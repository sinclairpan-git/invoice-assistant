from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_build_windows_dev_bundle():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "build_windows_dev_bundle.py"
    spec = importlib.util.spec_from_file_location("build_windows_dev_bundle", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_windows_dev_bundle


def test_build_windows_dev_bundle_creates_expected_layout_and_excludes_local_artifacts(
    tmp_path: Path,
) -> None:
    build_windows_dev_bundle = _load_build_windows_dev_bundle()
    project_root = tmp_path / "fixture-project"
    dist_root = tmp_path / "dist"

    _write_file(project_root / "AGENTS.md", "# agents\n")
    _write_file(project_root / "pyproject.toml", "[project]\nname='fixture-workspace'\nversion='0.1.0'\n")
    _write_file(project_root / "uv.lock", "# lock\n")
    _write_file(project_root / "backend" / "pyproject.toml", "[project]\nname='fixture-backend'\nversion='0.1.0'\n")
    _write_file(project_root / "backend" / "app" / "__init__.py", "")
    _write_file(project_root / "backend" / ".venv" / "pyvenv.cfg", "venv\n")
    _write_file(project_root / "frontend" / "package.json", '{"name":"fixture-frontend","version":"0.1.0"}\n')
    _write_file(project_root / "frontend" / "src" / "main.tsx", "console.log('ok')\n")
    _write_file(project_root / "frontend" / "dist" / "index.html", "<html></html>\n")
    _write_file(project_root / "frontend" / "node_modules" / "left-pad" / "index.js", "module.exports = 1\n")
    _write_file(project_root / "scripts" / "build_windows_portable.py", "print('portable')\n")
    _write_file(project_root / "packaging" / "windows-dev" / "初始化开发环境.ps1", "Write-Host 'init'\n")
    _write_file(project_root / "packaging" / "windows-dev" / "启动后端开发.ps1", "Write-Host 'backend'\n")
    _write_file(project_root / "packaging" / "windows-dev" / "启动前端开发.ps1", "Write-Host 'frontend'\n")
    _write_file(project_root / "packaging" / "windows-dev" / "构建便携包.ps1", "Write-Host 'bundle'\n")
    _write_file(project_root / "packaging" / "windows-dev" / "README-Windows-Codex开发.md", "# guide\n")
    _write_file(project_root / ".tmp" / "debug.txt", "tmp\n")
    _write_file(project_root / "dist" / "old.zip", "zip\n")

    output_dir = build_windows_dev_bundle(
        project_root=project_root,
        dist_root=dist_root,
        version="0.1.0-test",
    )

    assert output_dir == dist_root / "invoice-assistant-windows-dev-0.1.0-test"
    assert (output_dir / "workspace" / "AGENTS.md").is_file()
    assert (output_dir / "workspace" / "backend" / "pyproject.toml").is_file()
    assert (output_dir / "workspace" / "frontend" / "package.json").is_file()
    assert (output_dir / "workspace" / "scripts" / "build_windows_portable.py").is_file()
    assert (output_dir / "windows-dev" / "初始化开发环境.ps1").is_file()
    assert (output_dir / "windows-dev" / "README-Windows-Codex开发.md").is_file()
    assert not (output_dir / "workspace" / "backend" / ".venv").exists()
    assert not (output_dir / "workspace" / "frontend" / "node_modules").exists()
    assert not (output_dir / "workspace" / "frontend" / "dist").exists()
    assert not (output_dir / "workspace" / ".tmp").exists()
    assert not (output_dir / "workspace" / "dist").exists()
    assert (dist_root / "invoice-assistant-windows-dev-0.1.0-test.zip").is_file()

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["bundle_name"] == "invoice-assistant-windows-dev-0.1.0-test"
    assert manifest["version"] == "0.1.0-test"
    assert "workspace/AGENTS.md" in manifest["artifacts"]
    assert "windows-dev/初始化开发环境.ps1" in manifest["artifacts"]
    assert all("/node_modules/" not in item for item in manifest["artifacts"])
    assert all("/frontend/dist/" not in item for item in manifest["artifacts"])
    assert all("/backend/.venv/" not in item for item in manifest["artifacts"])
