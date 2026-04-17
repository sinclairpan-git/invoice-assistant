import json
from decimal import Decimal

from sqlalchemy import select
from starlette.testclient import TestClient

from backend.app.db.models import Batch, DocumentEvidence, ExtractedField, FieldCheck, InvoiceRecord
from backend.app.main import create_app
from backend.app.services.config_service import ConfigService
from backend.app.services.status_service import DISPLAY_STATUS_DUPLICATE, DISPLAY_STATUS_PASS


def seed_active_rules(session) -> dict[str, dict[str, object] | None]:
    service = ConfigService(session)
    service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000X"},
        changed_by="fin-admin",
        change_summary="seed tax profile",
        change_reason="test fixture",
    )
    service.create_version(
        kind="business_rules",
        content={"minimum_confidence": 0.75},
        changed_by="ops-admin",
        change_summary="seed business rules",
        change_reason="test fixture",
    )
    service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="seed naming rules",
        change_reason="test fixture",
    )
    return service.get_active_snapshot()


def seed_batch_fixture(app):
    session = app.state.session_factory()
    snapshot = seed_active_rules(session)

    batch = Batch(
        batch_no="BATCH-API-001",
        created_by="tester",
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
    )
    session.add(batch)
    session.flush()

    pass_invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="pass.pdf",
        renamed_filename="20260417_100.00_PASS.pdf",
        storage_path_original="storage/originals/BATCH-API-001/pass.pdf",
        storage_path_renamed="storage/renamed/BATCH-API-001/20260417_100.00_PASS.pdf",
        file_sha256="pass-sha",
        invoice_number="PASS-001",
        buyer_name="Shanghai Example Co",
        buyer_tax_no="91310000X",
        invoice_amount=Decimal("100.00"),
        processing_status="completed",
        system_decision="suggested_pass",
        review_status="not_reviewed",
        artifact_status="renamed",
        duplicate_flag=False,
        display_status=DISPLAY_STATUS_PASS,
        risk_flags="[]",
        problem_count=0,
    )
    review_invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="duplicate.pdf",
        storage_path_original="storage/originals/BATCH-API-001/duplicate.pdf",
        file_sha256="duplicate-sha",
        invoice_number="DUP-001",
        buyer_name="Shanghai Example Co",
        buyer_tax_no="91310000X",
        invoice_amount=Decimal("88.00"),
        processing_status="completed",
        system_decision="review_required",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=True,
        duplicate_group_key="dup-group-001",
        display_status=DISPLAY_STATUS_DUPLICATE,
        risk_flags=json.dumps(["suspected_duplicate"], ensure_ascii=False),
        problem_count=1,
    )
    session.add_all([pass_invoice, review_invoice])
    session.flush()

    session.add(
        DocumentEvidence(
            invoice_id=review_invoice.id,
            source_type="ocr",
            raw_text="Invoice No: DUP-001",
            pages_json=json.dumps([{"page_no": 1}], ensure_ascii=False),
            text_blocks_json=json.dumps([{"page_no": 1, "text": "Invoice No: DUP-001"}], ensure_ascii=False),
            table_lines_json=json.dumps([{"row_no": 1, "text": "Consulting Service"}], ensure_ascii=False),
            field_candidates_json=json.dumps(
                [{"field_name": "invoice_number", "value": "DUP-001", "confidence": 0.88}],
                ensure_ascii=False,
            ),
            confidence_summary_json=json.dumps({"overall": 0.88}, ensure_ascii=False),
            provider_name="fixture-ocr",
            provider_version="1.0",
        )
    )
    session.add(
        ExtractedField(
            invoice_id=review_invoice.id,
            field_name="invoice_number",
            extracted_value="DUP-001",
            normalized_value="DUP-001",
            confidence=Decimal("0.8800"),
            page_no=1,
            source_fragment="Invoice No: DUP-001",
            bbox_json=json.dumps({"x0": 1, "y0": 2}, ensure_ascii=False),
        )
    )
    session.add(
        FieldCheck(
            invoice_id=review_invoice.id,
            field_name="duplicate_group_key",
            expected_value="dup-group-001",
            actual_value="dup-group-001",
            match_result="matched",
            reason="matched historical duplicate record",
        )
    )

    session.commit()
    batch_id = batch.id
    review_invoice_id = review_invoice.id
    session.close()
    return {"batch_id": batch_id, "review_invoice_id": review_invoice_id}


def test_batch_and_invoice_api_workflows_cover_summary_detail_and_review(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api.db'}")
    fixture = seed_batch_fixture(app)
    client = TestClient(app)

    list_response = client.get("/api/batches")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["items"]) == 1
    batch_item = list_payload["items"][0]
    assert batch_item["batch_no"] == "BATCH-API-001"
    assert batch_item["total_files"] == 2
    assert batch_item["suggested_pass_count"] == 1
    assert batch_item["suggested_pass_total_amount"] == "100.00"
    assert batch_item["progress"]["stage_code"] == "completed"
    assert batch_item["progress"]["suggested_pass_total_amount"] == "100.00"

    detail_response = client.get(f"/api/batches/{fixture['batch_id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["item"]
    assert detail_payload["snapshot"]["tax_profile"]["version_no"] == "v1"
    assert detail_payload["export_jobs"] == []

    filtered_response = client.get(
        f"/api/batches/{fixture['batch_id']}/invoices",
        params={"display_status": DISPLAY_STATUS_PASS},
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["original_filename"] == "pass.pdf"
    assert filtered_payload["status_counts"][DISPLAY_STATUS_PASS] == 1
    assert filtered_payload["status_counts"][DISPLAY_STATUS_DUPLICATE] == 1
    assert filtered_payload["batch_summary"] == {"count": 1, "total_amount": "100.00"}
    assert filtered_payload["filtered_summary"] == {"count": 1, "total_amount": "100.00"}

    invoice_detail_response = client.get(f"/api/invoices/{fixture['review_invoice_id']}")
    assert invoice_detail_response.status_code == 200
    invoice_detail = invoice_detail_response.json()["item"]
    assert invoice_detail["display_status"] == DISPLAY_STATUS_DUPLICATE
    assert invoice_detail["duplicate_flag"] is True
    assert len(invoice_detail["evidence_items"]) == 1
    assert len(invoice_detail["field_checks"]) == 1
    assert invoice_detail["risk_flags"] == ["suspected_duplicate"]

    review_response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={"review_action": "approve", "review_note": "manual ok", "reviewed_by": "reviewer-a"},
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["item"]["review_action"] == "approve"
    assert review_payload["invoice"]["review_status"] == "manually_approved"
    assert review_payload["invoice"]["system_decision"] == "review_required"

    invalid_review_response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={"review_action": "unsupported", "review_note": None, "reviewed_by": "reviewer-a"},
    )
    assert invalid_review_response.status_code == 400

    non_reviewable_response = client.post(
        f"/api/invoices/{filtered_payload['items'][0]['id']}/review-actions",
        json={"review_action": "approve", "review_note": "should fail", "reviewed_by": "reviewer-a"},
    )
    assert non_reviewable_response.status_code == 400

    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    config_payload = config_response.json()
    assert config_payload["active_snapshot"]["tax_profile"]["content"]["buyer_tax_no"] == "91310000X"

    create_version_response = client.post(
        "/api/config/tax_profile/versions",
        json={
            "content": {"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000Y"},
            "changed_by": "fin-admin",
            "change_summary": "adjust profile",
            "change_reason": "test upgrade",
            "activate": True,
        },
    )
    assert create_version_response.status_code == 200
    assert create_version_response.json()["item"]["version_no"] == "v2"

    versions_response = client.get("/api/config/tax_profile/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()["items"]
    assert [item["version_no"] for item in versions] == ["v2", "v1"]

    upload_response = client.post(
        "/api/batches",
        data={"created_by": "uploader-a", "batch_no": "BATCH-UP-001"},
        files=[("files", ("upload.pdf", b"%PDF-1.7\nupload fixture", "application/pdf"))],
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()["item"]
    assert upload_payload["batch_no"] == "BATCH-UP-001"
    assert upload_payload["progress"]["stage_code"] == "processing"
    assert upload_payload["processing_files"] == 1

    session = app.state.session_factory()
    try:
        uploaded_batch = session.scalar(select(Batch).where(Batch.batch_no == "BATCH-UP-001"))
        assert uploaded_batch is not None
        uploaded_invoice = session.scalar(select(InvoiceRecord).where(InvoiceRecord.batch_id == uploaded_batch.id))
        assert uploaded_invoice is not None
        preview_response = client.get(f"/api/invoices/{uploaded_invoice.id}/preview")
        assert preview_response.status_code == 200
        assert preview_response.headers["content-type"].startswith("application/pdf")
    finally:
        session.close()

    missing_batch_response = client.get("/api/batches/missing-batch")
    assert missing_batch_response.status_code == 404

    invalid_export_response = client.post(
        f"/api/batches/{fixture['batch_id']}/exports",
        json={"export_type": "invalid", "created_by": "tester"},
    )
    assert invalid_export_response.status_code == 400

    session = app.state.session_factory()
    try:
        stored_batch = session.scalar(select(Batch).where(Batch.id == fixture["batch_id"]))
        assert stored_batch is not None
        assert stored_batch.total_files == 0
        assert stored_batch.suggested_pass_total_amount == Decimal("0.00")
    finally:
        session.close()
