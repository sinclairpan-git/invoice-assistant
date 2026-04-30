from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path


def _load_prepare_windows_portable_runtime_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "prepare_windows_portable_runtime.py"
    )
    spec = importlib.util.spec_from_file_location(
        "prepare_windows_portable_runtime", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_windows_portable_runtime_uses_runtime_python_for_pip_install(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_prepare_windows_portable_runtime_module()
    project_root = tmp_path / "fixture-project"
    runtime_root = project_root / "packaging" / "windows" / "python"
    download_dir = project_root / ".tmp" / "windows-runtime"
    nupkg_path = download_dir / f"python.{module.DEFAULT_PYTHON_VERSION}.nupkg"

    project_root.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(nupkg_path, "w") as zf:
        zf.writestr("tools/python.exe", "runtime")
        zf.writestr("tools/Lib/site-packages/runtime-marker.txt", "runtime")

    subprocess_calls: list[dict[str, object]] = []

    def fake_run(command: list[str], check: bool, cwd: Path) -> None:
        subprocess_calls.append(
            {
                "command": command,
                "check": check,
                "cwd": cwd,
            }
        )

    def fail_urlretrieve(*_args, **_kwargs):
        raise AssertionError(
            "urlretrieve should not run when the runtime archive already exists"
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.urllib.request, "urlretrieve", fail_urlretrieve)

    resolved_runtime_root = module.prepare_windows_portable_runtime(
        project_root=project_root,
        runtime_root=runtime_root,
    )

    runtime_python = runtime_root / "python.exe"
    site_packages_dir = runtime_root / "Lib" / "site-packages"
    wheelhouse_dir = download_dir / f"wheelhouse-py{module.DEFAULT_PYTHON_VERSION}"

    assert resolved_runtime_root == runtime_root
    assert runtime_python.is_file()
    assert (site_packages_dir / "runtime-marker.txt").is_file()
    assert subprocess_calls == [
        {
            "command": [str(runtime_python), "-m", "ensurepip", "--upgrade"],
            "check": True,
            "cwd": project_root,
        },
        {
            "command": [
                str(runtime_python),
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--dest",
                str(wheelhouse_dir),
                "--default-timeout",
                "120",
                "--retries",
                "5",
                "--only-binary=:all:",
                *module.WINDOWS_RUNTIME_PACKAGES,
            ],
            "check": True,
            "cwd": project_root,
        },
        {
            "command": [
                str(runtime_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                "--no-index",
                "--find-links",
                str(wheelhouse_dir),
                *module.WINDOWS_RUNTIME_PACKAGES,
            ],
            "check": True,
            "cwd": project_root,
        },
    ]
