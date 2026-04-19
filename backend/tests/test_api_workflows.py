import json
import threading
import time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from starlette.testclient import TestClient

from backend.app.db.models import (
    AttachmentDocument,
    AuditLog,
    Batch,
    DocumentEvidence,
    ExtractedField,
    FieldCheck,
    InvoiceRecord,
    ProcessingAttempt,
    ProcessingJob,
)
from backend.app.main import create_app
from backend.app.services.batch_service import BatchService, IncomingFile
from backend.app.services.config_service import ConfigService
from backend.app.services.processing_service import ProcessingService
from backend.app.services.storage_service import StorageService
from backend.app.services.status_service import (
    DISPLAY_STATUS_DUPLICATE,
    DISPLAY_STATUS_PASS,
)


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

    session.add_all(
        [
            AttachmentDocument(
                batch_id=batch.id,
                original_filename="duplicate-销货清单.pdf",
                storage_path_original="storage/originals/BATCH-API-001/duplicate-销货清单.pdf",
                file_sha256="attachment-consumed-sha",
                attachment_status="consumed",
                matched_invoice_id=review_invoice.id,
                match_reason="Matched by invoice_number; reclassified the invoice using attachment line items.",
            ),
            AttachmentDocument(
                batch_id=batch.id,
                original_filename="unmatched-销货清单.pdf",
                storage_path_original="storage/originals/BATCH-API-001/unmatched-销货清单.pdf",
                file_sha256="attachment-unmatched-sha",
                attachment_status="unmatched",
                match_reason="No same-batch invoice matched the attachment summary.",
            ),
        ]
    )

    session.add(
        DocumentEvidence(
            invoice_id=review_invoice.id,
            source_type="ocr",
            raw_text="Invoice No: DUP-001",
            pages_json=json.dumps([{"page_no": 1}], ensure_ascii=False),
            text_blocks_json=json.dumps(
                [{"page_no": 1, "text": "Invoice No: DUP-001"}], ensure_ascii=False
            ),
            table_lines_json=json.dumps(
                [{"row_no": 1, "text": "Consulting Service"}], ensure_ascii=False
            ),
            field_candidates_json=json.dumps(
                [
                    {
                        "field_name": "invoice_number",
                        "value": "DUP-001",
                        "confidence": 0.88,
                    }
                ],
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


def seed_failure_diagnostic_fixture(app):
    session = app.state.session_factory()
    snapshot = seed_active_rules(session)

    batch = Batch(
        batch_no="BATCH-API-DIAG-001",
        created_by="tester",
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
        status="failed",
        total_files=1,
        completed_files=0,
        processing_files=0,
        failed_files=1,
    )
    session.add(batch)
    session.flush()

    invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="broken.pdf",
        storage_path_original="storage/originals/BATCH-API-DIAG-001/broken.pdf",
        file_sha256="broken-sha",
        parse_source="ocr",
        processing_status="processing_failed",
        processing_stage="failed",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
        failure_reason="OCR timed out",
        last_error_stage="ocr_processing",
        last_error_code="ocr_timeout",
        last_error_message="OCR timed out",
        retryable=True,
    )
    session.add(invoice)
    session.flush()

    job = ProcessingJob(
        batch_id=batch.id,
        status="completed_with_failures",
        current_stage="failed",
        total_items=1,
        completed_items=0,
        failed_items=1,
        summary_json=json.dumps(
            {"failure_count": 1}, ensure_ascii=False, sort_keys=True
        ),
    )
    session.add(job)
    session.flush()

    attempt = ProcessingAttempt(
        job_id=job.id,
        invoice_id=invoice.id,
        attempt_no=1,
        status="retryable_failed",
        stage="ocr_processing",
        parse_source="ocr",
        provider_name="rapidocr-onnxruntime",
        provider_version="1.3.24",
        error_code="ocr_timeout",
        error_message="OCR timed out",
        retryable=True,
        diagnostic_json=json.dumps(
            {
                "provider_name": "rapidocr-onnxruntime",
                "provider_version": "1.3.24",
                "provider_error_code": "ocr_timeout",
                "confidence_summary": {"overall": 0.0},
                "stage": "ocr_processing",
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    session.add(attempt)
    session.flush()

    batch.active_job_id = job.id
    batch.last_stage_code = "failed"
    batch.last_stage_text = "批次处理失败"
    invoice.last_attempt_id = attempt.id
    session.commit()
    fixture = {"batch_id": batch.id, "invoice_id": invoice.id}
    session.close()
    return fixture


def set_trusted_actor(
    app,
    *,
    actor_id: str = "trusted-actor-1",
    display_name: str = "可信操作员",
    roles: list[str] | None = None,
):
    app.state.trusted_actor = {
        "actor_id": actor_id,
        "display_name": display_name,
        "roles": roles or [],
    }


def test_missing_trusted_actor_returns_config_error_for_read_and_write_paths(tmp_path):
    app = create_app(
        f"sqlite:///{tmp_path / 'api-missing-actor.db'}",
        trusted_actor=None,
    )
    fixture = seed_batch_fixture(app)
    client = TestClient(app)

    actor_response = client.get("/api/me")
    assert actor_response.status_code == 503
    assert actor_response.json()["detail"] == "后端未配置可信操作者上下文。"

    batch_response = client.post(
        "/api/batches",
        data={"created_by": "前端伪造姓名", "batch_no": "BATCH-MISSING-ACTOR-001"},
        files=[
            ("files", ("upload.pdf", b"%PDF-1.7\nupload fixture", "application/pdf"))
        ],
    )
    assert batch_response.status_code == 503
    assert batch_response.json()["detail"] == "后端未配置可信操作者上下文。"

    config_response = client.post(
        "/api/config/tax_profile/versions",
        json={
            "content": {
                "buyer_name": "Shanghai Example Co",
                "buyer_tax_no": "91310000Y",
            },
            "changed_by": "前端伪造姓名",
            "change_summary": "adjust profile",
            "change_reason": "test upgrade",
            "activate": True,
        },
    )
    assert config_response.status_code == 503
    assert config_response.json()["detail"] == "后端未配置可信操作者上下文。"

    review_response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={
            "review_action": "approve",
            "review_note": "manual ok",
            "reviewed_by": "前端伪造姓名",
        },
    )
    assert review_response.status_code == 503
    assert review_response.json()["detail"] == "后端未配置可信操作者上下文。"

    export_response = client.post(
        f"/api/batches/{fixture['batch_id']}/exports",
        json={"export_type": "excel_manifest", "created_by": "前端伪造姓名"},
    )
    assert export_response.status_code == 503
    assert export_response.json()["detail"] == "后端未配置可信操作者上下文。"

    session = app.state.session_factory()
    try:
        assert (
            session.scalar(
                select(Batch).where(Batch.batch_no == "BATCH-MISSING-ACTOR-001")
            )
            is None
        )
        assert (
            session.scalar(
                select(AuditLog)
                .where(
                    AuditLog.action.in_(
                        ["create_denied", "review_denied", "export_denied"]
                    )
                )
                .limit(1)
            )
            is None
        )
    finally:
        session.close()


def wait_for_batch_stage(
    client: TestClient, batch_id: str, expected_stage: str, *, timeout: float = 5.0
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    last_payload: dict[str, object] | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/batches/{batch_id}/progress")
        assert response.status_code == 200
        last_payload = response.json()["item"]
        is_terminal = (
            last_payload["total_files"] > 0
            and last_payload["processing_files"] == 0
            and last_payload["completed_files"] + last_payload["failed_files"]
            == last_payload["total_files"]
        )
        if last_payload["stage_code"] == expected_stage and is_terminal:
            return last_payload
        time.sleep(0.05)
    raise AssertionError(
        f"Timed out waiting for batch {batch_id} to reach stage {expected_stage!r}: {last_payload!r}"
    )


class StubProcessingRunner:
    def __init__(self) -> None:
        self.enqueued_batch_ids: list[str] = []

    def enqueue(self, batch_id: str) -> bool:
        if batch_id in self.enqueued_batch_ids:
            return False
        self.enqueued_batch_ids.append(batch_id)
        return True


def test_controlled_identity_comes_from_backend_actor_context(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-actor.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()
    set_trusted_actor(
        app, display_name="财务复核员", roles=["config_admin", "reviewer", "exporter"]
    )
    client = TestClient(app)

    actor_response = client.get("/api/me")
    assert actor_response.status_code == 200
    assert actor_response.json()["item"] == {
        "actor_id": "trusted-actor-1",
        "display_name": "财务复核员",
        "roles": ["config_admin", "reviewer", "exporter"],
    }

    upload_response = client.post(
        "/api/batches",
        data={"created_by": "前端伪造姓名", "batch_no": "BATCH-ACTOR-001"},
        files=[
            ("files", ("upload.pdf", b"%PDF-1.7\nupload fixture", "application/pdf"))
        ],
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["item"]["created_by"] == "财务复核员"

    create_version_response = client.post(
        "/api/config/tax_profile/versions",
        json={
            "content": {
                "buyer_name": "Shanghai Example Co",
                "buyer_tax_no": "91310000Y",
            },
            "changed_by": "前端伪造姓名",
            "change_summary": "adjust profile",
            "change_reason": "test upgrade",
            "activate": True,
        },
    )
    assert create_version_response.status_code == 200
    assert create_version_response.json()["item"]["changed_by"] == "财务复核员"


def test_review_action_uses_trusted_actor_even_when_request_spoofs_name(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-review-actor.db'}")
    fixture = seed_batch_fixture(app)
    set_trusted_actor(app, display_name="财务复核员", roles=["reviewer"])
    client = TestClient(app)

    review_response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={
            "review_action": "approve",
            "review_note": "manual ok",
            "reviewed_by": "前端伪造姓名",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["item"]["reviewed_by"] == "财务复核员"
    assert review_payload["invoice"]["review_status"] == "manually_approved"


def test_rule_version_requires_config_admin_and_records_denied_audit(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-config-role.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()
    set_trusted_actor(app, display_name="普通复核员", roles=["reviewer"])
    client = TestClient(app)

    response = client.post(
        "/api/config/tax_profile/versions",
        json={
            "content": {
                "buyer_name": "Shanghai Example Co",
                "buyer_tax_no": "91310000Y",
            },
            "change_summary": "adjust profile",
            "change_reason": "test upgrade",
            "activate": True,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前操作者缺少 config_admin 角色。"

    session = app.state.session_factory()
    try:
        audits = session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "rule_version",
                AuditLog.action == "create_denied",
            )
            .order_by(AuditLog.changed_at.desc())
        ).all()
        assert len(audits) == 1
        assert audits[0].changed_by == "普通复核员"
    finally:
        session.close()


def test_review_action_requires_reviewer_and_records_denied_audit(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-review-role.db'}")
    fixture = seed_batch_fixture(app)
    set_trusted_actor(app, display_name="导出专员", roles=["exporter"])
    client = TestClient(app)

    response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={"review_action": "approve", "review_note": "manual ok"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前操作者缺少 reviewer 角色。"

    session = app.state.session_factory()
    try:
        audits = session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "invoice_review",
                AuditLog.action == "review_denied",
            )
            .order_by(AuditLog.changed_at.desc())
        ).all()
        assert len(audits) == 1
        assert audits[0].entity_id == fixture["review_invoice_id"]
        assert audits[0].changed_by == "导出专员"
    finally:
        session.close()


def test_export_requires_exporter_and_records_denied_audit(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-export-role.db'}")
    fixture = seed_batch_fixture(app)
    set_trusted_actor(app, display_name="配置管理员", roles=["config_admin"])
    client = TestClient(app)

    response = client.post(
        f"/api/batches/{fixture['batch_id']}/exports",
        json={"export_type": "excel_manifest"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前操作者缺少 exporter 角色。"

    session = app.state.session_factory()
    try:
        audits = session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "export_job", AuditLog.action == "export_denied"
            )
            .order_by(AuditLog.changed_at.desc())
        ).all()
        assert len(audits) == 1
        assert audits[0].entity_id == fixture["batch_id"]
        assert audits[0].changed_by == "配置管理员"
    finally:
        session.close()


def test_batch_and_invoice_api_workflows_cover_summary_detail_and_review(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api.db'}")
    fixture = seed_batch_fixture(app)
    set_trusted_actor(
        app, display_name="财务复核员", roles=["config_admin", "reviewer", "exporter"]
    )
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
    assert batch_item["attachment_file_count"] == 2
    assert batch_item["attachment_status_counts"] == {"consumed": 1, "unmatched": 1}
    assert batch_item["progress"]["stage_code"] == "completed"
    assert batch_item["progress"]["suggested_pass_total_amount"] == "100.00"

    detail_response = client.get(f"/api/batches/{fixture['batch_id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["item"]
    assert detail_payload["snapshot"]["tax_profile"]["version_no"] == "v1"
    assert detail_payload["export_jobs"] == []
    assert detail_payload["attachment_status_counts"] == {"consumed": 1, "unmatched": 1}

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
    assert filtered_payload["filtered_summary"] == {
        "count": 1,
        "total_amount": "100.00",
    }

    invoice_detail_response = client.get(
        f"/api/invoices/{fixture['review_invoice_id']}"
    )
    assert invoice_detail_response.status_code == 200
    invoice_detail = invoice_detail_response.json()["item"]
    assert invoice_detail["display_status"] == DISPLAY_STATUS_DUPLICATE
    assert invoice_detail["duplicate_flag"] is True
    assert len(invoice_detail["attachments"]) == 1
    assert (
        invoice_detail["attachments"][0]["original_filename"]
        == "duplicate-销货清单.pdf"
    )
    assert invoice_detail["attachments"][0]["attachment_status"] == "consumed"
    assert invoice_detail["attachments"][0]["attachment_status_label"] == "已消费"
    assert (
        "reclassified the invoice" in invoice_detail["attachments"][0]["match_reason"]
    )
    assert len(invoice_detail["evidence_items"]) == 1
    assert len(invoice_detail["field_checks"]) == 1
    assert invoice_detail["risk_flags"] == ["suspected_duplicate"]

    review_response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={
            "review_action": "approve",
            "review_note": "manual ok",
            "reviewed_by": "reviewer-a",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["item"]["review_action"] == "approve"
    assert review_payload["invoice"]["review_status"] == "manually_approved"
    assert review_payload["invoice"]["system_decision"] == "review_required"

    invalid_review_response = client.post(
        f"/api/invoices/{fixture['review_invoice_id']}/review-actions",
        json={
            "review_action": "unsupported",
            "review_note": None,
            "reviewed_by": "reviewer-a",
        },
    )
    assert invalid_review_response.status_code == 400

    non_reviewable_response = client.post(
        f"/api/invoices/{filtered_payload['items'][0]['id']}/review-actions",
        json={
            "review_action": "approve",
            "review_note": "should fail",
            "reviewed_by": "reviewer-a",
        },
    )
    assert non_reviewable_response.status_code == 400

    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    config_payload = config_response.json()
    assert (
        config_payload["active_snapshot"]["tax_profile"]["content"]["buyer_tax_no"]
        == "91310000X"
    )

    create_version_response = client.post(
        "/api/config/tax_profile/versions",
        json={
            "content": {
                "buyer_name": "Shanghai Example Co",
                "buyer_tax_no": "91310000Y",
            },
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
        files=[
            ("files", ("upload.pdf", b"%PDF-1.7\nupload fixture", "application/pdf"))
        ],
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()["item"]
    assert upload_payload["batch_no"] == "BATCH-UP-001"
    failed_progress = wait_for_batch_stage(client, upload_payload["id"], "failed")
    assert failed_progress["completed_files"] == 0
    assert failed_progress["processing_files"] == 0
    assert failed_progress["failed_files"] == 1

    session = app.state.session_factory()
    try:
        uploaded_batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-UP-001")
        )
        assert uploaded_batch is not None
        uploaded_invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == uploaded_batch.id)
        )
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
        stored_batch = session.scalar(
            select(Batch).where(Batch.id == fixture["batch_id"])
        )
        assert stored_batch is not None
        assert stored_batch.total_files == 0
        assert stored_batch.suggested_pass_total_amount == Decimal("0.00")
    finally:
        session.close()


def test_create_batch_returns_without_waiting_for_processing_completion(
    tmp_path, monkeypatch
):
    app = create_app(f"sqlite:///{tmp_path / 'api-async.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()
    set_trusted_actor(app, display_name="异步上传员")

    processing_started = threading.Event()
    release_processing = threading.Event()
    original_process_batch = ProcessingService.process_batch

    def blocked_process_batch(self, batch_id: str):
        processing_started.set()
        assert release_processing.wait(timeout=2.0)
        return original_process_batch(self, batch_id)

    monkeypatch.setattr(ProcessingService, "process_batch", blocked_process_batch)

    with TestClient(app) as client:
        response_holder: dict[str, object] = {}

        def send_request() -> None:
            response_holder["response"] = client.post(
                "/api/batches",
                data={"created_by": "async-uploader", "batch_no": "BATCH-ASYNC-001"},
                files=[
                    (
                        "files",
                        ("upload.pdf", b"%PDF-1.7\nupload fixture", "application/pdf"),
                    ),
                    (
                        "files",
                        (
                            "upload-销货清单.pdf",
                            b"%PDF-1.7\nattachment fixture",
                            "application/pdf",
                        ),
                    ),
                ],
            )

        request_thread = threading.Thread(target=send_request)
        request_thread.start()

        assert processing_started.wait(timeout=1.0)
        request_thread.join(timeout=0.2)
        assert not request_thread.is_alive()

        response = response_holder["response"]
        assert response.status_code == 200
        payload = response.json()["item"]
        assert payload["batch_no"] == "BATCH-ASYNC-001"
        assert payload["total_files"] == 1
        assert payload["invoice_file_count"] == 1
        assert payload["attachment_file_count"] == 1
        assert payload["progress"]["stage_code"] in {"queued", "processing"}

        session = app.state.session_factory()
        try:
            batch = session.scalar(
                select(Batch).where(Batch.batch_no == "BATCH-ASYNC-001")
            )
            assert batch is not None
            assert batch.status in {"queued", "processing"}
            assert batch.total_files == 1
        finally:
            session.close()

        release_processing.set()
        final_progress = wait_for_batch_stage(client, payload["id"], "failed")
        assert final_progress["failed_files"] == 1


def test_progress_and_invoice_detail_expose_failure_diagnostics(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-diagnostics.db'}")
    fixture = seed_failure_diagnostic_fixture(app)
    client = TestClient(app)

    progress_response = client.get(f"/api/batches/{fixture['batch_id']}/progress")
    assert progress_response.status_code == 200
    progress_item = progress_response.json()["item"]
    assert progress_item["stage_code"] == "failed"
    assert progress_item["recent_failures"] == [
        {
            "invoice_id": fixture["invoice_id"],
            "original_filename": "broken.pdf",
            "failure_reason": "OCR timed out",
            "failure_stage": "ocr_processing",
            "error_code": "ocr_timeout",
            "retryable": True,
            "parse_source": "ocr",
            "provider_diagnostic": {
                "provider_name": "rapidocr-onnxruntime",
                "provider_version": "1.3.24",
                "provider_error_code": "ocr_timeout",
                "confidence_summary": {"overall": 0.0},
                "stage": "ocr_processing",
            },
        }
    ]

    detail_response = client.get(f"/api/invoices/{fixture['invoice_id']}")
    assert detail_response.status_code == 200
    detail_item = detail_response.json()["item"]
    assert detail_item["parse_source"] == "ocr"
    assert detail_item["last_error_stage"] == "ocr_processing"
    assert detail_item["last_error_code"] == "ocr_timeout"
    assert detail_item["last_error_message"] == "OCR timed out"
    assert detail_item["retryable"] is True
    assert detail_item["provider_diagnostic"] == {
        "provider_name": "rapidocr-onnxruntime",
        "provider_version": "1.3.24",
        "provider_error_code": "ocr_timeout",
        "confidence_summary": {"overall": 0.0},
        "stage": "ocr_processing",
    }


def test_batch_retry_endpoint_retries_failed_subset_idempotently(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-batch-retry.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)

    batch = BatchService(
        session=session,
        storage_service=StorageService(app.state.storage_root),
        config_service=ConfigService(session),
    ).create_batch(
        files=[
            IncomingFile(
                filename="01-standard-electronic.pdf",
                content=(
                    Path(__file__).parent
                    / "fixtures"
                    / "invoices"
                    / "01-standard-electronic.pdf"
                ).read_bytes(),
            ),
            IncomingFile(
                filename="broken.pdf",
                content=b"%PDF-1.7\nbroken fixture",
            ),
        ],
        created_by="tester",
        batch_no="BATCH-API-RETRY-001",
    )
    ProcessingService(
        session=session, storage_root=app.state.storage_root
    ).process_batch(batch.id)

    completed_invoice = session.scalar(
        select(InvoiceRecord)
        .where(
            InvoiceRecord.batch_id == batch.id,
            InvoiceRecord.processing_status == "completed",
        )
        .order_by(InvoiceRecord.original_filename.asc())
    )
    failed_invoice = session.scalar(
        select(InvoiceRecord)
        .where(
            InvoiceRecord.batch_id == batch.id,
            InvoiceRecord.processing_status == "processing_failed",
        )
        .order_by(InvoiceRecord.original_filename.asc())
    )
    assert completed_invoice is not None
    assert failed_invoice is not None
    completed_attempt_id = completed_invoice.last_attempt_id
    session.close()

    app.state.processing_runner = StubProcessingRunner()
    client = TestClient(app)

    retry_response = client.post(f"/api/batches/{batch.id}/retry-failures")
    assert retry_response.status_code == 200
    assert retry_response.json()["item"] == {
        "batch_id": batch.id,
        "retried_invoice_ids": [failed_invoice.id],
    }

    verify_session = app.state.session_factory()
    try:
        refreshed_completed = verify_session.get(InvoiceRecord, completed_invoice.id)
        refreshed_failed = verify_session.get(InvoiceRecord, failed_invoice.id)
        assert refreshed_completed is not None
        assert refreshed_failed is not None
        assert refreshed_completed.last_attempt_id == completed_attempt_id
        assert refreshed_failed.processing_status == "queued"
        assert refreshed_failed.processing_stage == "queued"
        assert refreshed_failed.failure_reason is None
    finally:
        verify_session.close()

    repeat_response = client.post(f"/api/batches/{batch.id}/retry-failures")
    assert repeat_response.status_code == 200
    assert repeat_response.json()["item"] == {
        "batch_id": batch.id,
        "retried_invoice_ids": [],
    }
    assert app.state.processing_runner.enqueued_batch_ids == [batch.id]


def test_invoice_retry_endpoint_is_idempotent_for_already_requeued_invoice(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api-invoice-retry.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)

    batch = BatchService(
        session=session,
        storage_service=StorageService(app.state.storage_root),
        config_service=ConfigService(session),
    ).create_batch(
        files=[
            IncomingFile(filename="broken.pdf", content=b"%PDF-1.7\nbroken fixture")
        ],
        created_by="tester",
        batch_no="BATCH-API-RETRY-002",
    )
    ProcessingService(
        session=session, storage_root=app.state.storage_root
    ).process_batch(batch.id)
    failed_invoice = session.scalar(
        select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
    )
    assert failed_invoice is not None
    session.close()

    app.state.processing_runner = StubProcessingRunner()
    client = TestClient(app)

    retry_response = client.post(f"/api/invoices/{failed_invoice.id}/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["item"] == {
        "invoice_id": failed_invoice.id,
        "batch_id": batch.id,
        "retried": True,
    }

    repeat_response = client.post(f"/api/invoices/{failed_invoice.id}/retry")
    assert repeat_response.status_code == 200
    assert repeat_response.json()["item"] == {
        "invoice_id": failed_invoice.id,
        "batch_id": batch.id,
        "retried": False,
    }
    assert app.state.processing_runner.enqueued_batch_ids == [batch.id]
