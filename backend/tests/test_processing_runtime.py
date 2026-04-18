from __future__ import annotations

import json
import time
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy import select
from starlette.testclient import TestClient

from backend.app.db.models import AttachmentDocument, Batch, InvoiceRecord
from backend.app.main import create_app
from backend.app.services.config_service import ConfigService
from backend.app.services.export_service import ExportService
from backend.app.services.processing_service import ProcessingService
from backend.app.services.status_service import DISPLAY_STATUS_REVIEW


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "invoices"


def build_fixture_pdf_bytes(lines: list[str]) -> bytes:
    escaped_lines = []
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        escaped_lines.append(f"({escaped}) Tj")
    stream = "BT /F1 12 Tf 72 720 Td " + " 0 -14 Td ".join(escaped_lines) + " ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        ),
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream.encode('latin-1'))} >> stream\n{stream}\nendstream endobj\n",
    ]
    payload = b"%PDF-1.4\n"
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(payload))
        payload += obj.encode("latin-1")
    startxref = len(payload)
    xref = "xref\n0 6\n0000000000 65535 f \n" + "".join(
        f"{offset:010d} 00000 n \n" for offset in offsets
    )
    trailer = f"trailer << /Root 1 0 R /Size 6 >>\nstartxref\n{startxref}\n%%EOF\n"
    return payload + xref.encode("latin-1") + trailer.encode("latin-1")


def build_invoice_fixture_pdf(
    *,
    invoice_number: str,
    seller_name: str,
    invoice_amount: str,
    line_text: str,
    overall_confidence: str = "0.98",
) -> bytes:
    return build_fixture_pdf_bytes(
        [
            "INVOICE_ASSISTANT_FIXTURE_START",
            "parse_mode=text",
            f"invoice_number={invoice_number}",
            "invoice_date=2026-04-17",
            f"invoice_amount={invoice_amount}",
            "buyer_name=Shanghai Example Co",
            "buyer_tax_no=91310000X",
            f"seller_name={seller_name}",
            f"line_text={line_text}",
            f"overall_confidence={overall_confidence}",
            "INVOICE_ASSISTANT_FIXTURE_END",
        ]
    )


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


def test_parse_document_uses_real_pdf_text_provider_for_electronic_fixture(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-text.db'}")
    session = app.state.session_factory()
    try:
        service = ProcessingService(session, storage_root=app.state.storage_root)
        parsed = service._parse_document(
            (FIXTURE_DIR / "01-standard-electronic.pdf").read_bytes()
        )
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
        parsed = service._parse_document(
            (FIXTURE_DIR / "02-scanned-ocr.pdf").read_bytes()
        )
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
    assert payload["batch_no"] == "BATCH-RUNTIME-LOW-001"
    batch_id = payload["id"]

    final_progress = wait_for_batch_stage(client, batch_id, "completed")
    assert final_progress["completed_files"] == 1
    assert final_progress["failed_files"] == 0
    assert final_progress["suggested_pass_total_amount"] == "0.00"

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-LOW-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
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
    assert detail["evidence_items"][0]["confidence_summary"][
        "overall"
    ] == pytest.approx(0.61)
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
        files=[
            ("files", ("broken.pdf", b"%PDF-1.7\nbroken fixture", "application/pdf"))
        ],
    )

    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["batch_no"] == "BATCH-RUNTIME-FAIL-001"
    batch_id = payload["id"]

    final_progress = wait_for_batch_stage(client, batch_id, "failed")
    assert final_progress["failed_files"] == 1
    assert final_progress["completed_files"] == 0

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-FAIL-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        assert invoice is not None

        assert invoice.processing_status == "processing_failed"
        assert invoice.failure_reason is not None
        assert "ocr_pdf_render_failed" in invoice.failure_reason
        assert "pdf_text_extraction_failed" in invoice.failure_reason
    finally:
        session.close()


def test_attachment_match_can_reclassify_review_keyword_invoice(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-match.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={"created_by": "runtime-tester", "batch_no": "BATCH-RUNTIME-ATTACH-001"},
        files=[
            (
                "files",
                (
                    "main-invoice.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="128.50",
                        line_text="DETAIL LIST ATTACHED",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "detail-list.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="128.50",
                        line_text="Office Supplies",
                    ),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    final_progress = wait_for_batch_stage(client, batch_id, "completed")
    assert final_progress["total_files"] == 1
    assert final_progress["failed_files"] == 0
    assert final_progress["recent_failures"] == []

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        attachment = session.scalar(
            select(AttachmentDocument).where(AttachmentDocument.batch_id == batch.id)
        )
        assert invoice is not None
        assert attachment is not None

        assert invoice.processing_status == "completed"
        assert invoice.system_decision == "suggested_pass"
        assert attachment.attachment_status == "consumed"
        assert attachment.matched_invoice_id == invoice.id
    finally:
        session.close()


def test_multiple_attachments_for_same_invoice_are_preserved_and_exposed(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-multi.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={"created_by": "runtime-tester", "batch_no": "BATCH-RUNTIME-ATTACH-002"},
        files=[
            (
                "files",
                (
                    "main-invoice.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-002",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="256.80",
                        line_text="DETAIL LIST ATTACHED",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "detail-list-part-1.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-002",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="256.80",
                        line_text="Office Supplies",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "detail-list-part-2.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-002",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="256.80",
                        line_text="Printer Paper",
                    ),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    final_progress = wait_for_batch_stage(client, batch_id, "completed")
    assert final_progress["total_files"] == 1
    assert final_progress["failed_files"] == 0

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-002")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        attachments = session.scalars(
            select(AttachmentDocument)
            .where(AttachmentDocument.batch_id == batch.id)
            .order_by(AttachmentDocument.original_filename.asc())
        ).all()
        assert invoice is not None

        assert invoice.processing_status == "completed"
        assert invoice.system_decision == "suggested_pass"
        assert len(attachments) == 2
        assert [attachment.matched_invoice_id for attachment in attachments] == [
            invoice.id,
            invoice.id,
        ]

        detail_response = client.get(f"/api/invoices/{invoice.id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()["item"]
        assert len(detail_payload["attachments"]) == 2
        assert [item["original_filename"] for item in detail_payload["attachments"]] == [
            "detail-list-part-1.pdf",
            "detail-list-part-2.pdf",
        ]
    finally:
        session.close()


def test_attachment_parse_failure_does_not_create_invoice_runtime_failure(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-fail.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={
            "created_by": "runtime-tester",
            "batch_no": "BATCH-RUNTIME-ATTACH-FAIL-001",
        },
        files=[
            (
                "files",
                (
                    "main-invoice.pdf",
                    (FIXTURE_DIR / "01-standard-electronic.pdf").read_bytes(),
                    "application/pdf",
                ),
            ),
            (
                "files",
                ("detail-list.pdf", b"%PDF-1.7\nbroken fixture", "application/pdf"),
            ),
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    final_progress = wait_for_batch_stage(client, batch_id, "completed")
    assert final_progress["total_files"] == 1
    assert final_progress["failed_files"] == 0
    assert final_progress["recent_failures"] == []

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-FAIL-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        attachment = session.scalar(
            select(AttachmentDocument).where(AttachmentDocument.batch_id == batch.id)
        )
        assert invoice is not None
        assert attachment is not None

        assert invoice.processing_status == "completed"
        assert invoice.system_decision == "suggested_pass"
        assert attachment.attachment_status == "parse_failed"
        assert attachment.matched_invoice_id is None
        assert attachment.match_reason is not None
    finally:
        session.close()


def test_attachment_match_stays_ambiguous_when_multiple_invoices_fit(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-ambiguous.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={
            "created_by": "runtime-tester",
            "batch_no": "BATCH-RUNTIME-ATTACH-AMB-001",
        },
        files=[
            (
                "files",
                (
                    "invoice-a.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="AMB-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="128.50",
                        line_text="Office Supplies",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "invoice-b.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="AMB-002",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="128.50",
                        line_text="Office Supplies",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "detail-list.pdf",
                    build_fixture_pdf_bytes(
                        [
                            "INVOICE_ASSISTANT_FIXTURE_START",
                            "parse_mode=text",
                            "invoice_date=2026-04-17",
                            "invoice_amount=128.50",
                            "buyer_name=Shanghai Example Co",
                            "buyer_tax_no=91310000X",
                            "seller_name=Acme Supplies Ltd",
                            "line_text=Office Supplies",
                            "overall_confidence=0.98",
                            "INVOICE_ASSISTANT_FIXTURE_END",
                        ]
                    ),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    final_progress = wait_for_batch_stage(client, batch_id, "completed")
    assert final_progress["total_files"] == 2
    assert final_progress["failed_files"] == 0

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-AMB-001")
        )
        assert batch is not None
        attachment = session.scalar(
            select(AttachmentDocument).where(AttachmentDocument.batch_id == batch.id)
        )
        assert attachment is not None

        assert attachment.attachment_status == "ambiguous"
        assert attachment.matched_invoice_id is None
    finally:
        session.close()


def test_review_keyword_invoice_without_attachment_gets_missing_attachment_reason(
    tmp_path,
):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-missing.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={
            "created_by": "runtime-tester",
            "batch_no": "BATCH-RUNTIME-ATTACH-MISSING-001",
        },
        files=[
            (
                "files",
                (
                    "main-invoice.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-MISSING-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="188.00",
                        line_text="DETAIL LIST ATTACHED",
                    ),
                    "application/pdf",
                ),
            )
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    wait_for_batch_stage(client, batch_id, "completed")

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-MISSING-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        assert invoice is not None
        invoice_id = invoice.id

        assert invoice.system_decision == "review_required"
        assert "attachment_missing" in json.loads(invoice.risk_flags or "[]")
    finally:
        session.close()

    detail_response = client.get(f"/api/invoices/{invoice_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["item"]
    assert detail_payload["display_status"] == DISPLAY_STATUS_REVIEW
    assert "缺少清单附件" in detail_payload["decision_reasons"]


def test_unmatched_attachment_reason_flows_to_invoice_detail_and_export(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-unmatched.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={
            "created_by": "runtime-tester",
            "batch_no": "BATCH-RUNTIME-ATTACH-UNMATCHED-001",
        },
        files=[
            (
                "files",
                (
                    "main-invoice.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-UNMATCHED-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="288.00",
                        line_text="DETAIL LIST ATTACHED",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "detail-list.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-OTHER-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="288.00",
                        line_text="Office Supplies",
                    ),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    wait_for_batch_stage(client, batch_id, "completed")

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-UNMATCHED-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        attachment = session.scalar(
            select(AttachmentDocument).where(AttachmentDocument.batch_id == batch.id)
        )
        assert invoice is not None
        assert attachment is not None

        assert invoice.system_decision == "review_required"
        assert attachment.attachment_status == "unmatched"
        assert "attachment_unmatched" in json.loads(invoice.risk_flags or "[]")

        detail_response = client.get(f"/api/invoices/{invoice.id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()["item"]
        assert "清单附件未匹配当前发票" in detail_payload["decision_reasons"]

        export_result = ExportService(
            session, storage_root=app.state.storage_root
        ).create_export(
            batch_id=batch.id,
            export_type="excel_manifest",
            created_by="runtime-tester",
        )
        with ZipFile(export_result.output_path) as workbook:
            sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "清单附件未匹配当前发票" in sheet_xml
    finally:
        session.close()


def test_low_confidence_attachment_reason_flows_to_invoice_detail_and_export(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime-attachment-low-confidence.db'}")
    session = app.state.session_factory()
    seed_active_rules(session)
    session.close()

    client = TestClient(app)
    response = client.post(
        "/api/batches",
        data={
            "created_by": "runtime-tester",
            "batch_no": "BATCH-RUNTIME-ATTACH-LOW-CONF-001",
        },
        files=[
            (
                "files",
                (
                    "main-invoice.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-LOW-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="388.00",
                        line_text="DETAIL LIST ATTACHED",
                    ),
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    "detail-list.pdf",
                    build_invoice_fixture_pdf(
                        invoice_number="ATT-LOW-001",
                        seller_name="Acme Supplies Ltd",
                        invoice_amount="388.00",
                        line_text="Office Supplies",
                        overall_confidence="0.60",
                    ),
                    "application/pdf",
                ),
            ),
        ],
    )

    assert response.status_code == 200
    batch_id = response.json()["item"]["id"]
    wait_for_batch_stage(client, batch_id, "completed")

    session = app.state.session_factory()
    try:
        batch = session.scalar(
            select(Batch).where(Batch.batch_no == "BATCH-RUNTIME-ATTACH-LOW-CONF-001")
        )
        assert batch is not None
        invoice = session.scalar(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        )
        attachment = session.scalar(
            select(AttachmentDocument).where(AttachmentDocument.batch_id == batch.id)
        )
        assert invoice is not None
        assert attachment is not None

        assert invoice.system_decision == "review_required"
        assert attachment.attachment_status == "matched"
        assert "attachment_low_confidence" in json.loads(invoice.risk_flags or "[]")

        detail_response = client.get(f"/api/invoices/{invoice.id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()["item"]
        assert "清单附件识别置信度不足" in detail_payload["decision_reasons"]

        export_result = ExportService(
            session, storage_root=app.state.storage_root
        ).create_export(
            batch_id=batch.id,
            export_type="excel_manifest",
            created_by="runtime-tester",
        )
        with ZipFile(export_result.output_path) as workbook:
            sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "清单附件识别置信度不足" in sheet_xml
    finally:
        session.close()
