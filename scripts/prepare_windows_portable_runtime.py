from __future__ import annotations

import argparse
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_PYTHON_VERSION = "3.11.9"
WINDOWS_RUNTIME_PACKAGES = [
    "fastapi==0.136.0",
    "python-multipart==0.0.26",
    "sqlalchemy==2.0.49",
    "pydantic==2.12.5",
    "uvicorn==0.44.0",
    "pypdf==6.10.2",
    "pypdfium2==5.7.0",
    "pillow==12.2.0",
    "rapidocr-onnxruntime==1.4.4",
]


def prepare_windows_portable_runtime(
    *,
    project_root: Path,
    runtime_root: Path,
    python_version: str = DEFAULT_PYTHON_VERSION,
) -> Path:
    project_root = project_root.expanduser().resolve()
    runtime_root = runtime_root.expanduser().resolve()
    download_dir = project_root / ".tmp" / "windows-runtime"
    download_dir.mkdir(parents=True, exist_ok=True)

    nupkg_path = download_dir / f"python.{python_version}.nupkg"
    if not nupkg_path.is_file():
        urllib.request.urlretrieve(
            f"https://www.nuget.org/api/v2/package/python/{python_version}",
            nupkg_path,
        )

    extracted_root = download_dir / f"python-{python_version}-extract"
    if extracted_root.exists():
        shutil.rmtree(extracted_root)
    with zipfile.ZipFile(nupkg_path) as zf:
        zf.extractall(extracted_root)

    tools_root = extracted_root / "tools"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    shutil.copytree(tools_root, runtime_root)

    runtime_python = runtime_root / "python.exe"
    if not runtime_python.is_file():
        raise FileNotFoundError(f"Missing required Python runtime file: {runtime_python}")

    site_packages_dir = runtime_root / "Lib" / "site-packages"
    site_packages_dir.mkdir(parents=True, exist_ok=True)
    wheelhouse_dir = download_dir / f"wheelhouse-py{python_version}"
    wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    _ensure_runtime_pip(runtime_python=runtime_python, cwd=project_root)
    _download_runtime_packages(
        runtime_python=runtime_python,
        wheelhouse_dir=wheelhouse_dir,
        cwd=project_root,
    )
    _install_runtime_packages(
        runtime_python=runtime_python,
        wheelhouse_dir=wheelhouse_dir,
        cwd=project_root,
    )
    return runtime_root


def _ensure_runtime_pip(*, runtime_python: Path, cwd: Path) -> None:
    subprocess.run(
        [
            str(runtime_python),
            "-m",
            "ensurepip",
            "--upgrade",
        ],
        check=True,
        cwd=cwd,
    )


def _download_runtime_packages(
    *,
    runtime_python: Path,
    wheelhouse_dir: Path,
    cwd: Path,
) -> None:
    subprocess.run(
        [
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
            *WINDOWS_RUNTIME_PACKAGES,
        ],
        check=True,
        cwd=cwd,
    )


def _install_runtime_packages(
    *,
    runtime_python: Path,
    wheelhouse_dir: Path,
    cwd: Path,
) -> None:
    subprocess.run(
        [
            str(runtime_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--upgrade",
            "--no-index",
            "--find-links",
            str(wheelhouse_dir),
            *WINDOWS_RUNTIME_PACKAGES,
        ],
        check=True,
        cwd=cwd,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the Windows portable runtime payload.")
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python-version", default=DEFAULT_PYTHON_VERSION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime_root = prepare_windows_portable_runtime(
        project_root=Path(args.project_root),
        runtime_root=Path(args.runtime_root),
        python_version=args.python_version,
    )
    print(runtime_root)


if __name__ == "__main__":
    main()
