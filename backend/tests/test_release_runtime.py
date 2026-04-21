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
