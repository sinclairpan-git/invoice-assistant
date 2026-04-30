from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_portable_bootstrap_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "packaging"
        / "windows"
        / "bootstrap"
        / "start_server.py"
    )
    spec = importlib.util.spec_from_file_location("portable_start_server", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyThread:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def start(self) -> None:
        return None


class _FakeUvicorn:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, int]] = []

    def run(self, app: object, host: str, port: int) -> None:
        self.calls.append((app, host, port))


def test_select_available_port_prefers_requested_port(monkeypatch) -> None:
    module = _load_portable_bootstrap_module()

    monkeypatch.setattr(module, "_can_bind_port", lambda _host, port: port == 18080)

    assert module._select_available_port("127.0.0.1", 18080) == 18080


def test_select_available_port_falls_back_within_port_pool(monkeypatch) -> None:
    module = _load_portable_bootstrap_module()

    monkeypatch.setattr(module, "_can_bind_port", lambda _host, port: port == 18082)

    assert module._select_available_port("127.0.0.1", 18080) == 18082


def test_select_available_port_raises_when_port_pool_is_exhausted(monkeypatch) -> None:
    module = _load_portable_bootstrap_module()

    monkeypatch.setattr(module, "_can_bind_port", lambda _host, _port: False)

    try:
        module._select_available_port("127.0.0.1", 18080)
    except RuntimeError as exc:
        assert "18080-18089" in str(exc)
    else:
        raise AssertionError("Expected _select_available_port to fail when all candidate ports are occupied")


def test_portable_bootstrap_logs_traceback_when_startup_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_portable_bootstrap_module()
    portable_root = tmp_path / "portable"

    monkeypatch.setattr(module.threading, "Thread", _DummyThread)

    def _boom(_server_root: Path):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "load_create_app", _boom)

    exit_code = module.main(["--portable-root", str(portable_root)])

    assert exit_code == 1
    startup_log = portable_root / "logs" / "startup.log"
    assert startup_log.is_file()
    log_text = startup_log.read_text(encoding="utf-8")
    assert "Portable bootstrap failed." in log_text
    assert "RuntimeError: boom" in log_text


def test_portable_bootstrap_logs_handoff_and_runs_uvicorn(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_portable_bootstrap_module()
    portable_root = tmp_path / "portable"
    resolved_root = portable_root.resolve()
    fake_uvicorn = _FakeUvicorn()

    monkeypatch.setattr(module.threading, "Thread", _DummyThread)
    monkeypatch.setattr(module, "load_uvicorn", lambda: fake_uvicorn)
    monkeypatch.setattr(module, "_select_available_port", lambda _host, _port: 18082)
    monkeypatch.setattr(
        module,
        "load_create_app",
        lambda _server_root: lambda **kwargs: {"ok": True, "kwargs": kwargs},
    )

    exit_code = module.main(
        [
            "--portable-root",
            str(portable_root),
            "--host",
            "127.0.0.1",
            "--port",
            "19090",
        ]
    )

    assert exit_code == 0
    assert fake_uvicorn.calls == [
        (
            {
                "ok": True,
                "kwargs": {
                        "runtime_overrides": {
                        "portable_root": resolved_root,
                        "host": "127.0.0.1",
                        "port": 18082,
                        "frontend_static_dir": resolved_root / "app" / "server" / "frontend-dist",
                    }
                },
            },
            "127.0.0.1",
            18082,
        )
    ]
    log_text = (portable_root / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "Selected listen port: 18082" in log_text
    assert "Application loaded, starting uvicorn." in log_text
    assert "Uvicorn.run returned." in log_text
    assert (portable_root / "runtime" / "app.url").read_text(encoding="utf-8") == "http://127.0.0.1:18082\n"


def test_portable_bootstrap_logs_when_port_pool_is_exhausted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_portable_bootstrap_module()
    portable_root = tmp_path / "portable"

    monkeypatch.setattr(module.threading, "Thread", _DummyThread)
    monkeypatch.setattr(
        module,
        "_select_available_port",
        lambda _host, _port: (_ for _ in ()).throw(RuntimeError("No available port in 18080-18089")),
    )

    exit_code = module.main(["--portable-root", str(portable_root)])

    assert exit_code == 1
    log_text = (portable_root / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "No available port in 18080-18089" in log_text
