from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select
from starlette.testclient import TestClient

from backend.app.db.models import Batch, InvoiceRecord
from backend.app.main import create_app
from backend.app.services.config_service import ConfigService
from backend.app.services.processing_service import ProcessingService
from backend.app.services.status_service import DISPLAY_STATUS_REVIEW


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "invoices"


def seed_active_rules(session) -> None:
    service = ConfigService(session)
    service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000X"},
        changed_by="fin-admin",
        change_summary="seed tax profile",
        change_reason="runtime fixture",
    )
    service.create_version(
        kind="business_rules",
        content={
            "minimum_confidence": 0.75,
            "seller_whitelist": ["Acme Supplies Ltd", "Scan Services Co"],
            "review_keywords": ["DETAIL LIST ATTACHED"],
        },
        changed_by="ops-admin",
        change_summary="seed business rules",
        change_reason="runtime fixture",
    )
    service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="seed naming rules",
        change_reason="runtime fixture",
    )


def test_parse_document_uses_real_pdf_text_provider_for_electronic_fixture(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-text.db'}")
    session = app.state.session_factory()
    try:
        service = ProcessingService(session, storage_root=app.state.storage_root)
        parsed = service._parse_document((FIXTURE_DIR / "01-standard-electronic.pdf").read_bytes())
    finally:
        session.close()

    assert parsed.evidence.source_type == "text"
    assert parsed.evidence.provider_name == "pypdf"
    assert parsed.evidence.best_candidate("invoice_number").value == "STD-001"
    assert parsed.evidence.best_candidate("buyer_name").value == "Shanghai Example Co"
    assert parsed.metadata["parse_mode"] == "text"


def test_parse_document_forces_local_ocr_for_scanned_fixture(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-ocr.db'}")
    session = app.state.session_factory()
    try:
        service = ProcessingService(session, storage_root=app.state.storage_root)
        parsed = service._parse_document((FIXTURE_DIR / "02-scanned-ocr.pdf").read_bytes())
    finally:
        session.close()

    assert parsed.evidence.source_type == "ocr"
    assert parsed.evidence.provider_name == "rapidocr-onnxruntime"
    assert parsed.evidence.best_candidate("invoice_number").value == "OCR-001"
    assert parsed.evidence.best_candidate("seller_name").value == "Scan Services Co"
    assert parsed.evidence.confidence_summary.overall == pytest.approx(0.88)


def test_low_confidence_ocr_fixture_is_review_required(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-review.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={"created_by": "runtime-tester", "batch_no": "BATCH-RUNTIME-LOW-001"},
        files=[
            (
                "files",
                (
                    "03-review-required.pdf",
                    (FIXTURE_DIR / "03-review-required.pdf").read_bytes(),
                    "application/pdf",
                ),
            )
        ],
    )

    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["progress"]["stage_code"] == "completed"
    assert payload["completed_files"] == 1
    assert payload["failed_files"] == 0
    assert payload["suggested_pass_total_amount"] == "0.00"

    session = app.state.session_factory()
    try:
        batch = session.scalar(select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-LOW-001"))
        assert batch is not None
        invoice = session.scalar(select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id))
        assert invoice is not None

        invoice_id = invoice.id
        assert invoice.parse_source == "ocr"
        assert invoice.system_decision == "review_required"
        assert invoice.artifact_status == "original_only"
        assert "low_confidence" in json.loads(invoice.risk_flags or "[]")
    finally:
        session.close()

    detail_response = client.get(f"/api/invoices/{invoice_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["item"]
    assert detail["display_status"] == DISPLAY_STATUS_REVIEW
    assert detail["evidence_items"][0]["provider_name"] == "rapidocr-onnxruntime"
    assert detail["evidence_items"][0]["confidence_summary"]["overall"] == pytest.approx(0.61)
    assert "low_confidence" in detail["risk_flags"]


def test_invalid_pdf_records_structured_failure_reason(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-invalid.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={"created_by": "runtime-tester", "batch_no": "BATCH-RUNTIME-FAIL-001"},
        files=[("files", ("broken.pdf", b"%PDF-1.7\nbroken fixture", "application/pdf"))],
    )

    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["progress"]["stage_code"] == "failed"
    assert payload["failed_files"] == 1
    assert payload["completed_files"] == 0

    session = app.state.session_factory()
    try:
        batch = session.scalar(select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-FAIL-001"))
        assert batch is not None
        invoice = session.scalar(select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id))
        assert invoice is not None

        assert invoice.processing_status == "processing_failed"
        assert invoice.failure_reason is not None
        assert "ocr_pdf_render_failed" in invoice.failure_reason
        assert "pdf_text_extraction_failed" in invoice.failure_reason
    finally:
        session.close()
