from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_portable_launcher_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "packaging"
        / "windows"
        / "bootstrap"
        / "launch_portable.py"
    )
    spec = importlib.util.spec_from_file_location("portable_launch_portable", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_portable_stop_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "packaging"
        / "windows"
        / "bootstrap"
        / "stop_portable.py"
    )
    spec = importlib.util.spec_from_file_location("portable_stop_portable", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_portable_fails_with_log_when_python_runtime_is_missing(tmp_path: Path) -> None:
    module = _load_portable_launcher_module()
    portable_root = tmp_path / "portable"

    exit_code = module.main(["--portable-root", str(portable_root)])

    assert exit_code == 1
    startup_log = portable_root / "logs" / "startup.log"
    assert startup_log.is_file()
    assert "Missing bundled Python runtime." in startup_log.read_text(encoding="utf-8")


def test_launch_portable_starts_server_and_opens_runtime_url(tmp_path: Path, monkeypatch) -> None:
    module = _load_portable_launcher_module()
    portable_root = tmp_path / "portable"
    python_exe = portable_root / "app" / "python" / "python.exe"
    start_server = portable_root / "app" / "bootstrap" / "start_server.py"
    opened_urls: list[str] = []

    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("runtime\n", encoding="utf-8")
    start_server.parent.mkdir(parents=True, exist_ok=True)
    start_server.write_text("print('start')\n", encoding="utf-8")

    monkeypatch.setattr(module, "_resolve_existing_running_url", lambda *_args: None)
    monkeypatch.setattr(module, "_probe_python_runtime", lambda *_args: None)

    def _fake_start_server(*, portable_root: Path, python_exe: Path, start_script: Path) -> None:
        runtime_dir = portable_root / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "app.url").write_text("http://127.0.0.1:18082\n", encoding="utf-8")

    monkeypatch.setattr(module, "_start_server_process", _fake_start_server)
    monkeypatch.setattr(module, "_wait_for_ready_url", lambda *_args: "http://127.0.0.1:18082")
    monkeypatch.setattr(module, "_open_url", lambda url: opened_urls.append(url))

    exit_code = module.main(["--portable-root", str(portable_root)])

    assert exit_code == 0
    assert opened_urls == ["http://127.0.0.1:18082"]
    assert "Launcher opened browser for http://127.0.0.1:18082" in (
        portable_root / "logs" / "startup.log"
    ).read_text(encoding="utf-8")


def test_launch_portable_can_skip_browser_for_ci_smoke(tmp_path: Path, monkeypatch) -> None:
    module = _load_portable_launcher_module()
    portable_root = tmp_path / "portable"
    python_exe = portable_root / "app" / "python" / "python.exe"
    start_server = portable_root / "app" / "bootstrap" / "start_server.py"

    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("runtime\n", encoding="utf-8")
    start_server.parent.mkdir(parents=True, exist_ok=True)
    start_server.write_text("print('start')\n", encoding="utf-8")

    monkeypatch.setattr(module, "_resolve_existing_running_url", lambda *_args: None)
    monkeypatch.setattr(module, "_probe_python_runtime", lambda *_args: None)
    monkeypatch.setattr(module, "_start_server_process", lambda **_kwargs: None)
    monkeypatch.setattr(module, "_wait_for_ready_url", lambda *_args: "http://127.0.0.1:18082")
    monkeypatch.setattr(
        module,
        "_open_url",
        lambda _url: (_ for _ in ()).throw(AssertionError("browser should stay closed")),
    )

    exit_code = module.main(["--portable-root", str(portable_root), "--no-browser"])

    assert exit_code == 0
    assert "Launcher ready without opening browser for http://127.0.0.1:18082" in (
        portable_root / "logs" / "startup.log"
    ).read_text(encoding="utf-8")


def test_normalize_portable_root_strips_trailing_quote_and_backslash(tmp_path: Path) -> None:
    module = _load_portable_launcher_module()
    portable_root = tmp_path / "portable-root"
    raw_value = f'{portable_root}\\\"'

    assert module._normalize_portable_root(raw_value) == portable_root.resolve()


def test_launch_process_is_running_uses_binary_tasklist_output(monkeypatch) -> None:
    module = _load_portable_launcher_module()

    monkeypatch.setattr(module.os, "name", "nt")

    def _fake_run(args, *, capture_output, text, check):
        assert args == ["tasklist", "/FI", "PID eq 11940"]
        assert capture_output is True
        assert text is False
        assert check is False
        return SimpleNamespace(stdout=b"\xcf\xff 11940\r\n")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    assert module._process_is_running(11940) is True


def test_launch_server_process_does_not_inherit_parent_handles(tmp_path: Path, monkeypatch) -> None:
    module = _load_portable_launcher_module()
    calls: list[dict] = []

    def _fake_popen(_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)

    module._start_server_process(
        portable_root=tmp_path,
        python_exe=tmp_path / "python.exe",
        start_script=tmp_path / "start_server.py",
    )

    assert calls
    assert calls[0]["stdout"] is module.subprocess.DEVNULL
    assert calls[0]["stderr"] is module.subprocess.DEVNULL
    assert calls[0]["stdin"] is module.subprocess.DEVNULL
    assert calls[0]["close_fds"] is True


def test_launch_process_is_running_handles_missing_tasklist_stdout(monkeypatch) -> None:
    module = _load_portable_launcher_module()

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=None),
    )

    assert module._process_is_running(11940) is False


def test_launch_resolve_existing_running_url_cleans_stale_runtime_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_portable_launcher_module()
    portable_root = tmp_path / "portable"
    runtime_dir = portable_root / "runtime"
    runtime_dir.mkdir(parents=True)
    pid_file = runtime_dir / "app.pid"
    url_file = runtime_dir / "app.url"
    pid_file.write_text("11940\n", encoding="utf-8")
    url_file.write_text("http://127.0.0.1:18080\n", encoding="utf-8")

    monkeypatch.setattr(module, "_process_is_running", lambda _pid: False)

    assert module._resolve_existing_running_url(portable_root) is None
    assert not pid_file.exists()
    assert not url_file.exists()


def test_stop_process_is_running_uses_binary_tasklist_output(monkeypatch) -> None:
    module = _load_portable_stop_module()

    monkeypatch.setattr(module.os, "name", "nt")

    def _fake_run(args, *, capture_output, text, check):
        assert args == ["tasklist", "/FI", "PID eq 11940"]
        assert capture_output is True
        assert text is False
        assert check is False
        return SimpleNamespace(stdout=b"\xcf\xff 11940\r\n")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    assert module._process_is_running(11940) is True
