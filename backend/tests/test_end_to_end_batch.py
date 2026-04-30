from __future__ import annotations

import time
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select
from starlette.testclient import TestClient

from backend.app.db.models import AuditLog, Batch, ExportJob, InvoiceRecord
from backend.app.main import create_app
from backend.app.services.config_service import ConfigService
from backend.app.services.status_service import (
    DISPLAY_STATUS_DUPLICATE,
    DISPLAY_STATUS_PASS,
    DISPLAY_STATUS_REVIEW,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "invoices"


def seed_active_rules(session) -> None:
    service = ConfigService(session)
    service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000X"},
        changed_by="fin-admin",
        change_summary="seed tax profile",
        change_reason="e2e fixture",
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
        change_reason="e2e fixture",
    )
    service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="seed naming rules",
        change_reason="e2e fixture",
    )


def load_fixture_uploads() -> list[tuple[str, tuple[str, bytes, str]]]:
    uploads: list[tuple[str, tuple[str, bytes, str]]] = []
    for fixture_path in sorted(FIXTURE_DIR.glob("*.pdf")):
        uploads.append(
            (
                "files",
                (
                    fixture_path.name,
                    fixture_path.read_bytes(),
                    "application/pdf",
                ),
            )
        )
    return uploads


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


def wait_for_batch_stage(
    client: TestClient, batch_id: str, expected_stage: str, *, timeout: float = 20.0
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


def test_end_to_end_batch_upload_to_export_keeps_ui_export_and_db_consistent(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'e2e.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()
    set_trusted_actor(app, display_name="端到端操作员", roles=["reviewer", "exporter"])

    client = TestClient(app)

    upload_response = client.post(
        "/api/batches",
        data={"created_by": "e2e-operator", "batch_no": "BATCH-E2E-001"},
        files=load_fixture_uploads(),
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()["item"]
    batch_id = upload_payload["id"]
    assert upload_payload["batch_no"] == "BATCH-E2E-001"

    final_progress = wait_for_batch_stage(client, batch_id, "completed")
    assert final_progress["completed_files"] == 4
    assert final_progress["processing_files"] == 0
    assert final_progress["failed_files"] == 0
    assert final_progress["suggested_pass_count"] == 2
    assert final_progress["suggested_pass_total_amount"] == "384.50"

    batch_list_response = client.get("/api/batches")
    assert batch_list_response.status_code == 200
    batch_item = batch_list_response.json()["items"][0]
    assert batch_item["id"] == batch_id
    assert batch_item["progress"]["stage_code"] == "completed"
    assert batch_item["suggested_pass_count"] == 2
    assert batch_item["suggested_pass_total_amount"] == "384.50"

    batch_detail_response = client.get(f"/api/batches/{batch_id}")
    assert batch_detail_response.status_code == 200
    batch_detail = batch_detail_response.json()["item"]
    assert (
        batch_detail["snapshot"]["naming_rules"]["content"]["pattern"]
        == "{date}_{amount}_{number}"
    )
    assert batch_detail["export_jobs"] == []

    all_invoices_response = client.get(f"/api/batches/{batch_id}/invoices")
    assert all_invoices_response.status_code == 200
    all_invoices_payload = all_invoices_response.json()
    assert len(all_invoices_payload["items"]) == 4
    assert all_invoices_payload["status_counts"][DISPLAY_STATUS_PASS] == 2
    assert all_invoices_payload["status_counts"][DISPLAY_STATUS_REVIEW] == 1
    assert all_invoices_payload["status_counts"][DISPLAY_STATUS_DUPLICATE] == 1
    assert all_invoices_payload["batch_summary"] == {
        "count": 2,
        "total_amount": "384.50",
    }
    assert all_invoices_payload["filtered_summary"] == {
        "count": 2,
        "total_amount": "384.50",
    }

    pass_response = client.get(
        f"/api/batches/{batch_id}/invoices",
        params={"display_status": DISPLAY_STATUS_PASS},
    )
    assert pass_response.status_code == 200
    pass_payload = pass_response.json()
    assert len(pass_payload["items"]) == 2
    assert pass_payload["filtered_summary"] == {"count": 2, "total_amount": "384.50"}
    pass_names = {item["renamed_filename"] for item in pass_payload["items"]}
    assert pass_names == {
        "20260417_128.50_STD-001.pdf",
        "20260416_256.00_OCR-001.pdf",
    }

    review_response = client.get(
        f"/api/batches/{batch_id}/invoices",
        params={"display_status": DISPLAY_STATUS_REVIEW},
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert len(review_payload["items"]) == 1
    assert review_payload["filtered_summary"] == {"count": 0, "total_amount": "0.00"}
    review_invoice = review_payload["items"][0]
    assert review_invoice["original_filename"] == "03-review-required.pdf"

    duplicate_invoice = next(
        item
        for item in all_invoices_payload["items"]
        if item["display_status"] == DISPLAY_STATUS_DUPLICATE
    )
    assert duplicate_invoice["original_filename"] == "04-duplicate.pdf"

    review_detail_response = client.get(f"/api/invoices/{review_invoice['id']}")
    assert review_detail_response.status_code == 200
    review_detail = review_detail_response.json()["item"]
    assert review_detail["display_status"] == DISPLAY_STATUS_REVIEW
    assert review_detail["parse_source"] == "ocr"
    assert len(review_detail["evidence_items"]) == 1
    assert len(review_detail["extracted_fields"]) >= 6
    assert len(review_detail["field_checks"]) >= 2
    assert set(review_detail["risk_flags"]) == {
        "attachment_missing",
        "fuzzy_line_items",
        "low_confidence",
    }
    assert review_detail["basic_compliance_status"] == "通过"
    assert review_detail["business_compliance_status"] == "待人工复核"
    assert review_detail["final_decision"] == "需人工复核"
    assert "缺少清单附件" in review_detail["decision_reasons"]
    assert "低置信度" in review_detail["decision_reasons"]
    assert "需人工复核后再导出" in review_detail["suggested_actions"]
    assert review_detail["review_actions"] == []
    assert review_detail["evidence_items"][0]["confidence_summary"]["overall"] == 0.61

    duplicate_detail_response = client.get(f"/api/invoices/{duplicate_invoice['id']}")
    assert duplicate_detail_response.status_code == 200
    duplicate_detail = duplicate_detail_response.json()["item"]
    assert duplicate_detail["duplicate_flag"] is True
    assert duplicate_detail["duplicate_group_key"]
    assert duplicate_detail["risk_flags"] == ["suspected_duplicate"]

    preview_response = client.get(
        f"/api/invoices/{pass_payload['items'][0]['id']}/preview"
    )
    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"] == "application/pdf"
    assert preview_response.content.startswith(b"%PDF")

    blocked_pass_export_response = client.post(
        f"/api/batches/{batch_id}/exports",
        json={"export_type": "suggested_pass_zip", "created_by": "exporter-a"},
    )
    assert blocked_pass_export_response.status_code == 400
    assert (
        blocked_pass_export_response.json()["detail"]
        == "当前批次仍有待复核票据，无法导出建议通过 ZIP。"
    )

    approve_response = client.post(
        f"/api/invoices/{review_invoice['id']}/review-actions",
        json={
            "review_action": "approve",
            "review_note": "finance checked",
            "reviewed_by": "reviewer-a",
        },
    )
    assert approve_response.status_code == 200
    approve_payload = approve_response.json()
    assert approve_payload["item"]["review_action"] == "approve"
    assert approve_payload["invoice"]["review_status"] == "manually_approved"
    assert approve_payload["invoice"]["system_decision"] == "review_required"

    pass_export_response = client.post(
        f"/api/batches/{batch_id}/exports",
        json={"export_type": "suggested_pass_zip", "created_by": "exporter-a"},
    )
    assert pass_export_response.status_code == 200
    pass_export = pass_export_response.json()["item"]
    assert pass_export["summary"] == {"record_count": 3, "total_amount": "472.50"}
    assert Path(pass_export["output_path"]).is_file()
    with ZipFile(pass_export["output_path"]) as archive:
        assert set(archive.namelist()) == {
            "20260417_128.50_STD-001.pdf",
            "20260416_256.00_OCR-001.pdf",
            "03-review-required.pdf",
        }

    issue_export_response = client.post(
        f"/api/batches/{batch_id}/exports",
        json={"export_type": "issue_zip", "created_by": "exporter-a"},
    )
    assert issue_export_response.status_code == 200
    issue_export = issue_export_response.json()["item"]
    assert issue_export["summary"] == {"record_count": 1, "total_amount": "128.50"}
    assert Path(issue_export["output_path"]).is_file()
    with ZipFile(issue_export["output_path"]) as archive:
        assert set(archive.namelist()) == {"04-duplicate.pdf"}

    manifest_export_response = client.post(
        f"/api/batches/{batch_id}/exports",
        json={"export_type": "excel_manifest", "created_by": "exporter-a"},
    )
    assert manifest_export_response.status_code == 200
    manifest_export = manifest_export_response.json()["item"]
    assert manifest_export["summary"] == {
        "record_count": 4,
        "suggested_pass_count": 3,
        "suggested_pass_total_amount": "472.50",
    }
    assert Path(manifest_export["output_path"]).is_file()
    with ZipFile(manifest_export["output_path"]) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "BATCH-E2E-001" in sheet_xml
    assert "基础合规" in sheet_xml
    assert "业务风险分类" in sheet_xml
    assert "最终结论" in sheet_xml
    assert "03-review-required.pdf" in sheet_xml
    assert "04-duplicate.pdf" in sheet_xml
    assert "人工确认通过" in sheet_xml

    batch_detail_after_exports = client.get(f"/api/batches/{batch_id}")
    assert batch_detail_after_exports.status_code == 200
    batch_detail_payload = batch_detail_after_exports.json()["item"]
    assert len(batch_detail_payload["export_jobs"]) == 3
    assert (
        batch_detail_payload["export_manifest_path"] == manifest_export["output_path"]
    )

    session = app.state.session_factory()
    batch_row = session.get(Batch, batch_id)
    invoices = session.scalars(
        select(InvoiceRecord)
        .where(InvoiceRecord.batch_id == batch_id)
        .order_by(InvoiceRecord.original_filename.asc())
    ).all()
    export_jobs = session.scalars(
        select(ExportJob)
        .where(ExportJob.batch_id == batch_id)
        .order_by(ExportJob.created_at.asc())
    ).all()

    assert batch_row is not None
    assert batch_row.status == "completed"
    assert batch_row.suggested_pass_count == 2
    assert f"{batch_row.suggested_pass_total_amount:.2f}" == "384.50"
    assert batch_row.export_manifest_path == manifest_export["output_path"]

    invoice_map = {invoice.original_filename: invoice for invoice in invoices}
    assert invoice_map["01-standard-electronic.pdf"].parse_source == "text"
    assert invoice_map["01-standard-electronic.pdf"].artifact_status == "renamed"
    assert invoice_map["02-scanned-ocr.pdf"].parse_source == "ocr"
    assert invoice_map["02-scanned-ocr.pdf"].artifact_status == "renamed"
    assert invoice_map["03-review-required.pdf"].system_decision == "review_required"
    assert invoice_map["03-review-required.pdf"].review_status == "manually_approved"
    assert invoice_map["04-duplicate.pdf"].duplicate_flag is True

    assert len(export_jobs) == 3
    assert [job.export_type for job in export_jobs] == [
        "suggested_pass_zip",
        "issue_zip",
        "excel_manifest",
    ]

    export_audits = session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "export_job")
        .order_by(AuditLog.changed_at.asc())
    ).all()
    assert [audit.action for audit in export_audits] == [
        "export_denied",
        "export_completed",
        "export_completed",
        "export_completed",
    ]
    assert export_audits[0].entity_id == batch_id

    session.close()
