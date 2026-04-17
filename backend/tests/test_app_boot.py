from sqlalchemy import inspect
from starlette.testclient import TestClient

from backend.app.main import create_app


def test_app_boot_and_db_initialization(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    app = create_app(database_url)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "invoice-assistant"}

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
