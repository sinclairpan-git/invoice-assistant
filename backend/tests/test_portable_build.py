from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _load_build_portable_bundle():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "build_windows_portable.py"
    spec = importlib.util.spec_from_file_location("build_windows_portable", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_portable_bundle


def test_build_portable_bundle_creates_expected_layout_from_fixture_project_root(
    tmp_path: Path,
) -> None:
    build_portable_bundle = _load_build_portable_bundle()
    project_root = tmp_path / "fixture-project"
    dist_root = tmp_path / "dist"
    runtime_root = project_root / "packaging" / "windows" / "python"

    _write_file(project_root / "backend" / "__init__.py", "")
    _write_file(project_root / "backend" / "pyproject.toml", "[project]\nname = 'fixture-backend'\nversion = '0.1.0'\n")
    _write_file(project_root / "backend" / "app" / "__init__.py", "")
    _write_file(
        project_root / "backend" / "app" / "main.py",
        "def create_app(*args, **kwargs):\n    return {'ok': True}\n",
    )
    _write_file(project_root / "backend" / "tests" / "test_runtime.py", "def test_placeholder():\n    assert True\n")
    _write_file(project_root / "backend" / "data" / "invoice_assistant.db", "local db\n")
    _write_file(project_root / "backend" / ".venv" / "pyvenv.cfg", "include-system-site-packages = false\n")
    _write_file(project_root / "backend" / "fixture_backend.egg-info" / "PKG-INFO", "Metadata-Version: 2.1\n")
    _write_file(
        project_root / "frontend" / "dist" / "index.html",
        "<!doctype html><html><body>portable frontend</body></html>\n",
    )
    _write_file(
        project_root / "frontend" / "dist" / "assets" / "app.js",
        "console.log('portable');\n",
    )
    _write_file(
        project_root / "packaging" / "windows" / "bootstrap" / "start_server.py",
        "print('bootstrap')\n",
    )
    _write_file(
        project_root / "packaging" / "windows" / "启动发票助手.bat",
        "@echo off\r\necho start\r\n",
    )
    _write_file(
        project_root / "packaging" / "windows" / "停止发票助手.bat",
        "@echo off\r\necho stop\r\n",
    )
    _write_file(
        project_root / "packaging" / "windows" / "用户指引.html",
        "<html><body>guide</body></html>\n",
    )
    _write_file(
        project_root / "packaging" / "windows" / "README-技术维护.md",
        "# maintain\n",
    )
    _write_file(runtime_root / "python.exe", "runtime\n")
    _write_file(runtime_root / "Lib" / "site-packages" / "portable_runtime.txt", "runtime marker\n")

    output_dir = build_portable_bundle(
        project_root=project_root,
        dist_root=dist_root,
        version="0.1.0-test",
    )

    assert output_dir == dist_root / "invoice-assistant-windows-x64-0.1.0-test"
    assert _read_normalized(output_dir / "启动发票助手.bat") == "@echo off\necho start\n"
    assert _read_normalized(output_dir / "停止发票助手.bat") == "@echo off\necho stop\n"
    assert (output_dir / "用户指引.html").read_text(encoding="utf-8") == "<html><body>guide</body></html>\n"
    assert (output_dir / "README-技术维护.md").read_text(encoding="utf-8") == "# maintain\n"
    assert (output_dir / "app" / "bootstrap" / "start_server.py").exists()
    assert (output_dir / "app" / "python" / "python.exe").exists()
    assert (output_dir / "app" / "python" / "Lib" / "site-packages" / "portable_runtime.txt").exists()
    assert (output_dir / "app" / "server" / "frontend-dist" / "index.html").exists()
    assert (output_dir / "app" / "server" / "backend" / "app" / "main.py").exists()
    assert (output_dir / "app" / "server" / "backend" / "pyproject.toml").exists()
    assert (output_dir / "data" / "storage").is_dir()
    assert (output_dir / "data" / "exports").is_dir()
    assert (output_dir / "logs").is_dir()
    assert (output_dir / "runtime").is_dir()
    assert (dist_root / "invoice-assistant-windows-x64-0.1.0-test.zip").is_file()
    assert not (output_dir / "app" / "server" / "backend" / ".venv").exists()
    assert not (output_dir / "app" / "server" / "backend" / "tests").exists()
    assert not (output_dir / "app" / "server" / "backend" / "data").exists()
    assert not (output_dir / "app" / "server" / "backend" / "fixture_backend.egg-info").exists()

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.1.0-test"
    assert manifest["bundle_name"] == "invoice-assistant-windows-x64-0.1.0-test"
    assert "built_at" in manifest
    assert "启动发票助手.bat" in manifest["artifacts"]
    assert "app/python/python.exe" in manifest["artifacts"]
    assert "app/bootstrap/start_server.py" in manifest["artifacts"]
    assert "app/server/frontend-dist/index.html" in manifest["artifacts"]
    assert "app/server/backend/app/main.py" in manifest["artifacts"]
    assert all(".venv" not in path for path in manifest["artifacts"])
    assert all("/tests/" not in path for path in manifest["artifacts"])
    assert all("/data/" not in path for path in manifest["artifacts"])


def test_build_portable_bundle_requires_python_runtime(tmp_path: Path) -> None:
    build_portable_bundle = _load_build_portable_bundle()
    project_root = tmp_path / "fixture-project"
    dist_root = tmp_path / "dist"

    _write_file(project_root / "backend" / "__init__.py", "")
    _write_file(project_root / "frontend" / "dist" / "index.html", "<html></html>\n")
    _write_file(project_root / "packaging" / "windows" / "bootstrap" / "start_server.py", "print('bootstrap')\n")
    _write_file(project_root / "packaging" / "windows" / "启动发票助手.bat", "@echo off\r\necho start\r\n")
    _write_file(project_root / "packaging" / "windows" / "停止发票助手.bat", "@echo off\r\necho stop\r\n")

    try:
        build_portable_bundle(
            project_root=project_root,
            dist_root=dist_root,
            version="0.1.0-test",
        )
    except FileNotFoundError as exc:
        assert "Missing required Python runtime" in str(exc)
    else:
        raise AssertionError("build_portable_bundle should fail when python runtime is missing")


def test_build_portable_bundle_requires_site_packages_in_python_runtime(tmp_path: Path) -> None:
    build_portable_bundle = _load_build_portable_bundle()
    project_root = tmp_path / "fixture-project"
    dist_root = tmp_path / "dist"
    runtime_root = project_root / "packaging" / "windows" / "python"

    _write_file(project_root / "backend" / "__init__.py", "")
    _write_file(project_root / "frontend" / "dist" / "index.html", "<html></html>\n")
    _write_file(project_root / "packaging" / "windows" / "bootstrap" / "start_server.py", "print('bootstrap')\n")
    _write_file(project_root / "packaging" / "windows" / "启动发票助手.bat", "@echo off\r\necho start\r\n")
    _write_file(project_root / "packaging" / "windows" / "停止发票助手.bat", "@echo off\r\necho stop\r\n")
    _write_file(runtime_root / "python.exe", "runtime\n")

    try:
        build_portable_bundle(
            project_root=project_root,
            dist_root=dist_root,
            version="0.1.0-test",
        )
    except FileNotFoundError as exc:
        assert "Missing required Python runtime directory" in str(exc)
        assert "Lib" in str(exc)
    else:
        raise AssertionError("build_portable_bundle should fail when site-packages is missing")
