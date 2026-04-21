from sqlalchemy import inspect
from starlette.testclient import TestClient

from backend.app.api.dependencies import CONTROLLED_ROLES
from backend.app.main import app as boot_app
from backend.app.main import create_app


def test_app_boot_and_db_initialization(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    app = create_app(database_url)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "invoice-assistant"}
    assert app.state.trusted_actor == {
        "actor_id": "local-admin",
        "display_name": "本机管理员",
        "roles": list(CONTROLLED_ROLES),
    }

    inspector = inspect(app.state.engine)
    table_names = set(inspector.get_table_names())
    assert {
        "batches",
        "invoice_records",
        "processing_jobs",
        "processing_attempts",
        "document_evidence",
        "extracted_fields",
        "field_checks",
        "rule_versions",
        "review_actions",
        "export_jobs",
        "audit_logs",
    }.issubset(table_names)


def test_module_level_app_boot_initializes_trusted_actor():
    client = TestClient(boot_app)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json() == {
        "item": {
            "actor_id": "local-admin",
            "display_name": "本机管理员",
            "roles": list(CONTROLLED_ROLES),
        }
    }


def test_create_app_can_disable_default_trusted_actor(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'app-no-actor.db'}", trusted_actor=None)
    client = TestClient(app)

    response = client.get("/api/me")

    assert response.status_code == 503
    assert response.json() == {"detail": "后端未配置可信操作者上下文。"}


def test_create_app_exposes_runtime_config_state(tmp_path):
    frontend_dir = tmp_path / "app" / "server" / "frontend-dist"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    app = create_app(
        f"sqlite:///{tmp_path / 'app-runtime.db'}",
        runtime_overrides={"portable_root": tmp_path},
    )

    runtime_config = app.state.runtime_config

    assert runtime_config.portable_root == tmp_path.resolve()
    assert runtime_config.data_dir == (tmp_path / "data").resolve()
    assert runtime_config.logs_dir == (tmp_path / "logs").resolve()
    assert runtime_config.runtime_dir == (tmp_path / "runtime").resolve()
    assert runtime_config.frontend_static_dir == frontend_dir.resolve()
    assert runtime_config.database_url == f"sqlite:///{tmp_path / 'data' / 'app.db'}"
    assert runtime_config.host == "127.0.0.1"
    assert runtime_config.port == 18080
    assert app.state.storage_root == (tmp_path / "data" / "storage").resolve()
    assert str(app.state.engine.url) == f"sqlite:///{tmp_path / 'data' / 'app.db'}"
