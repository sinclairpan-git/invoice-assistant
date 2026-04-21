from pathlib import Path

from starlette.testclient import TestClient

from backend.app.main import create_app


def _write_frontend_build(frontend_dir: Path) -> None:
    assets_dir = frontend_dir / "assets"
    assets_dir.mkdir(parents=True)
    (frontend_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>release shell</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('release asset');", encoding="utf-8")


def test_release_runtime_hosts_assets_and_spa_routes(tmp_path):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)

    app = create_app(
        f"sqlite:///{tmp_path / 'release.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    client = TestClient(app)

    asset_response = client.get("/assets/app.js")
    root_response = client.get("/")
    setup_response = client.get("/setup")
    health_response = client.get("/health")
    me_response = client.get("/api/me")

    assert asset_response.status_code == 200
    assert asset_response.text == "console.log('release asset');"

    assert root_response.status_code == 200
    assert "release shell" in root_response.text
    assert root_response.headers["content-type"].startswith("text/html")

    assert setup_response.status_code == 200
    assert "release shell" in setup_response.text
    assert setup_response.headers["content-type"].startswith("text/html")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "service": "invoice-assistant"}

    assert me_response.status_code == 200
    assert me_response.json()["item"]["actor_id"] == "local-admin"


def test_release_runtime_does_not_intercept_unknown_api_paths(tmp_path):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)

    app = create_app(
        f"sqlite:///{tmp_path / 'release-api.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    client = TestClient(app)

    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}


def test_release_runtime_does_not_intercept_reserved_backend_paths(tmp_path):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)

    app = create_app(
        f"sqlite:///{tmp_path / 'release-reserved.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    client = TestClient(app)

    api_root_response = client.get("/api")
    health_subpath_response = client.get("/health/ready")
    openapi_slash_response = client.get("/openapi.json/")
    redoc_slash_response = client.get("/redoc/")

    assert api_root_response.status_code == 404
    assert api_root_response.headers["content-type"].startswith("application/json")
    assert api_root_response.json() == {"detail": "Not Found"}

    assert health_subpath_response.status_code == 404
    assert health_subpath_response.headers["content-type"].startswith("application/json")
    assert health_subpath_response.json() == {"detail": "Not Found"}

    assert openapi_slash_response.status_code == 404
    assert openapi_slash_response.headers["content-type"].startswith("application/json")
    assert openapi_slash_response.json() == {"detail": "Not Found"}

    assert redoc_slash_response.status_code == 404
    assert redoc_slash_response.headers["content-type"].startswith("application/json")
    assert redoc_slash_response.json() == {"detail": "Not Found"}


def test_portable_runtime_rewrites_database_and_runtime_paths(tmp_path):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)

    app = create_app(
        "sqlite:////should/not/be/used.db",
        runtime_overrides={"portable_root": tmp_path},
    )

    runtime_config = app.state.runtime_config

    assert runtime_config.database_url == f"sqlite:///{tmp_path / 'data' / 'app.db'}"
    assert runtime_config.data_dir == (tmp_path / "data").resolve()
    assert runtime_config.logs_dir == (tmp_path / "logs").resolve()
    assert runtime_config.runtime_dir == (tmp_path / "runtime").resolve()
    assert runtime_config.storage_root == (tmp_path / "data" / "storage").resolve()
    assert runtime_config.frontend_static_dir == frontend_dir.resolve()
    assert runtime_config.host == "127.0.0.1"
    assert runtime_config.port == 18080


def test_release_runtime_opens_export_folder_within_portable_data_dir(tmp_path, monkeypatch):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)
    export_file = tmp_path / "data" / "exports" / "BATCH-001" / "manifest.xlsx"
    export_file.parent.mkdir(parents=True)
    export_file.write_text("manifest", encoding="utf-8")

    opened_paths: list[Path] = []

    def fake_open_path(path: Path) -> None:
        opened_paths.append(path)

    app = create_app(
        f"sqlite:///{tmp_path / 'release-open-dir.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    monkeypatch.setattr("backend.app.api.runtime.open_path_in_file_manager", fake_open_path)
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/api/runtime/open-path",
        json={"path": "exports/BATCH-001/manifest.xlsx"},
    )

    assert response.status_code == 200
    assert response.json()["item"] == {
        "requested_path": "exports/BATCH-001/manifest.xlsx",
        "opened_path": str((tmp_path / "data" / "exports" / "BATCH-001").resolve()),
    }
    assert opened_paths == [(tmp_path / "data" / "exports" / "BATCH-001").resolve()]


def test_release_runtime_rejects_open_path_outside_portable_data_dir(tmp_path, monkeypatch):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)

    def fail_open_path(_: Path) -> None:
        raise AssertionError("open_path_in_file_manager should not be called")

    app = create_app(
        f"sqlite:///{tmp_path / 'release-open-reject.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    monkeypatch.setattr("backend.app.api.runtime.open_path_in_file_manager", fail_open_path)
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/api/runtime/open-path",
        json={"path": "../outside"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "仅允许打开便携包数据目录内的路径。"}


def test_release_runtime_rejects_open_path_for_non_portable_runtime(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    def fail_open_path(_: Path) -> None:
        raise AssertionError("open_path_in_file_manager should not be called")

    app = create_app(f"sqlite:///{data_dir / 'runtime.db'}")
    monkeypatch.setattr("backend.app.api.runtime.open_path_in_file_manager", fail_open_path)
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/api/runtime/open-path",
        json={"path": "exports/BATCH-001/manifest.xlsx"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "仅便携包运行态支持打开本地路径。"}


def test_release_runtime_rejects_open_path_from_non_loopback_client(tmp_path, monkeypatch):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)
    export_dir = tmp_path / "data" / "exports" / "BATCH-001"
    export_dir.mkdir(parents=True)

    def fail_open_path(_: Path) -> None:
        raise AssertionError("open_path_in_file_manager should not be called")

    app = create_app(
        f"sqlite:///{tmp_path / 'release-open-remote.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    monkeypatch.setattr("backend.app.api.runtime.open_path_in_file_manager", fail_open_path)
    client = TestClient(app, client=("10.0.0.8", 50000))

    response = client.post(
        "/api/runtime/open-path",
        json={"path": "exports/BATCH-001"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "仅允许本机请求打开本地路径。"}


def test_release_runtime_returns_error_when_opening_file_manager_fails(tmp_path, monkeypatch):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    _write_frontend_build(frontend_dir)
    export_dir = tmp_path / "data" / "exports" / "BATCH-001"
    export_dir.mkdir(parents=True)

    def fail_open_path(_: Path) -> None:
        raise RuntimeError("boom")

    app = create_app(
        f"sqlite:///{tmp_path / 'release-open-error.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )
    monkeypatch.setattr("backend.app.api.runtime.open_path_in_file_manager", fail_open_path)
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/api/runtime/open-path",
        json={"path": "exports/BATCH-001"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "打开本地文件夹失败。"}
