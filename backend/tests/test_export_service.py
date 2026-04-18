import json
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select
import pytest

from backend.app.db.models import AttachmentDocument, AuditLog, Batch, ExportJob, InvoiceRecord
from backend.app.db.session import create_database_engine, create_session_factory, init_db
from backend.app.services.export_service import ExportService
from backend.app.services.status_service import DISPLAY_STATUS_DUPLICATE, DISPLAY_STATUS_PASS


def build_session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'export.db'}"
    engine = create_database_engine(database_url)
    init_db(engine)
    return create_session_factory(engine)()


def write_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.7\nfixture")


def test_export_service_generates_zip_and_excel_outputs_with_consistent_summary(tmp_path):
    session = build_session(tmp_path)

    pass_file = tmp_path / "pass.pdf"
    issue_file = tmp_path / "issue.pdf"
    write_pdf(pass_file)
    write_pdf(issue_file)

    batch = Batch(
        batch_no="BATCH-EXPORT-001",
        created_by="tester",
        snapshot_json="{}",
        status="completed",
        total_files=2,
        completed_files=2,
        processing_files=0,
        failed_files=0,
    )
    session.add(batch)
    session.flush()

    session.add_all(
        [
            InvoiceRecord(
                batch_id=batch.id,
                original_filename="pass.pdf",
                renamed_filename="20260417_100.00_PASS.pdf",
                storage_path_original=str(pass_file),
                storage_path_renamed=str(pass_file),
                file_sha256="pass-sha",
                invoice_number="PASS-001",
                invoice_amount=Decimal("100.00"),
                processing_status="completed",
                system_decision="suggested_pass",
                review_status="not_reviewed",
                artifact_status="renamed",
                duplicate_flag=False,
                display_status=DISPLAY_STATUS_PASS,
                risk_flags="[]",
            ),
            InvoiceRecord(
                batch_id=batch.id,
                original_filename="issue.pdf",
                storage_path_original=str(issue_file),
                file_sha256="issue-sha",
                invoice_number="ISSUE-001",
                invoice_amount=Decimal("88.00"),
                processing_status="completed",
                system_decision="review_required",
                review_status="not_reviewed",
                artifact_status="original_only",
                duplicate_flag=True,
                duplicate_group_key="dup-group-001",
                display_status=DISPLAY_STATUS_DUPLICATE,
                risk_flags='["suspected_duplicate"]',
                problem_count=1,
            ),
        ]
    )
    session.commit()

    service = ExportService(session, storage_root=tmp_path / "storage")

    pass_result = service.create_export(
        batch_id=batch.id,
        export_type="suggested_pass_zip",
        created_by="tester",
    )
    assert pass_result.summary == {"record_count": 1, "total_amount": "100.00"}
    with ZipFile(pass_result.output_path) as archive:
        assert archive.namelist() == ["20260417_100.00_PASS.pdf"]

    issue_result = service.create_export(
        batch_id=batch.id,
        export_type="issue_zip",
        created_by="tester",
    )
    assert issue_result.summary == {"record_count": 1, "total_amount": "88.00"}
    with ZipFile(issue_result.output_path) as archive:
        assert archive.namelist() == ["issue.pdf"]

    excel_result = service.create_export(
        batch_id=batch.id,
        export_type="excel_manifest",
        created_by="tester",
    )
    assert excel_result.summary == {
        "record_count": 2,
        "suggested_pass_count": 1,
        "suggested_pass_total_amount": "100.00",
    }
    with ZipFile(excel_result.output_path) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "BATCH-EXPORT-001" in sheet_xml
    assert "pass.pdf" in sheet_xml
    assert "issue.pdf" in sheet_xml
    assert "系统建议通过" in sheet_xml
    assert "疑似重复" in sheet_xml

    jobs = session.scalars(select(ExportJob).order_by(ExportJob.created_at.asc())).all()
    assert len(jobs) == 3
    assert [job.export_type for job in jobs] == ["suggested_pass_zip", "issue_zip", "excel_manifest"]

    session.refresh(batch)
    assert batch.export_manifest_path == excel_result.output_path


def test_export_service_cleans_partial_file_on_failure(tmp_path, monkeypatch):
    session = build_session(tmp_path)

    pass_file = tmp_path / "pass.pdf"
    write_pdf(pass_file)

    batch = Batch(
        batch_no="BATCH-EXPORT-FAIL",
        created_by="tester",
        snapshot_json="{}",
        status="completed",
        total_files=1,
        completed_files=1,
        processing_files=0,
        failed_files=0,
    )
    session.add(batch)
    session.flush()
    session.add(
        InvoiceRecord(
            batch_id=batch.id,
            original_filename="pass.pdf",
            storage_path_original=str(pass_file),
            file_sha256="pass-sha",
            processing_status="completed",
            system_decision="suggested_pass",
            review_status="not_reviewed",
            artifact_status="original_only",
            duplicate_flag=False,
            risk_flags="[]",
        )
    )
    session.commit()

    service = ExportService(session, storage_root=tmp_path / "storage")
    captured: dict[str, Path] = {}

    def broken_write_zip(output_file: Path, *, invoices):
        captured["path"] = output_file
        output_file.write_bytes(b"partial zip")
        raise RuntimeError("simulated export failure")

    monkeypatch.setattr(service, "_write_zip", broken_write_zip)

    with pytest.raises(RuntimeError, match="simulated export failure"):
        service.create_export(
            batch_id=batch.id,
            export_type="suggested_pass_zip",
            created_by="tester",
        )

    failed_job = session.scalars(select(ExportJob).where(ExportJob.batch_id == batch.id)).all()
    assert len(failed_job) == 1
    assert failed_job[0].status == "failed"
    assert failed_job[0].output_path is None
    assert captured["path"].exists() is False

    session.refresh(batch)
    assert batch.export_manifest_path is None


def test_export_service_blocks_non_terminal_batch_exports_and_records_denied_audit(tmp_path):
    session = build_session(tmp_path)

    pass_file = tmp_path / "pass.pdf"
    write_pdf(pass_file)

    batch = Batch(
        batch_no="BATCH-EXPORT-NONTERMINAL",
        created_by="tester",
        snapshot_json="{}",
        status="processing",
        total_files=1,
        completed_files=0,
        processing_files=1,
        failed_files=0,
    )
    session.add(batch)
    session.flush()
    session.add(
        InvoiceRecord(
            batch_id=batch.id,
            original_filename="pass.pdf",
            storage_path_original=str(pass_file),
            file_sha256="pass-sha",
            processing_status="processing",
            system_decision="suggested_pass",
            review_status="not_reviewed",
            artifact_status="original_only",
            duplicate_flag=False,
            risk_flags="[]",
        )
    )
    session.commit()

    service = ExportService(session, storage_root=tmp_path / "storage")

    with pytest.raises(ValueError, match="当前批次尚未处理完成"):
        service.create_export(
            batch_id=batch.id,
            export_type="excel_manifest",
            created_by="tester",
        )

    jobs = session.scalars(select(ExportJob).where(ExportJob.batch_id == batch.id)).all()
    assert jobs == []

    denied_audits = session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "export_job", AuditLog.entity_id == batch.id, AuditLog.action == "export_denied")
        .order_by(AuditLog.changed_at.asc())
    ).all()
    assert len(denied_audits) == 1
    assert denied_audits[0].changed_by == "tester"
    assert denied_audits[0].change_summary == "export_type=excel_manifest"
    assert denied_audits[0].change_reason == "batch_not_terminal"
    assert json.loads(denied_audits[0].payload_json) == {
        "batch_id": batch.id,
        "export_type": "excel_manifest",
        "gate": {
            "allowed": False,
            "reasons": ["batch_not_terminal"],
        },
    }


def test_export_service_blocks_pending_review_pass_export_and_success_manifest_includes_compliance_fields(tmp_path):
    session = build_session(tmp_path)

    pass_file = tmp_path / "pass.pdf"
    review_file = tmp_path / "review.pdf"
    write_pdf(pass_file)
    write_pdf(review_file)

    batch = Batch(
        batch_no="BATCH-EXPORT-COMPLIANCE",
        created_by="tester",
        snapshot_json="{}",
        status="completed",
        total_files=2,
        completed_files=2,
        processing_files=0,
        failed_files=0,
    )
    session.add(batch)
    session.flush()

    session.add_all(
        [
            InvoiceRecord(
                batch_id=batch.id,
                original_filename="pass.pdf",
                renamed_filename="20260417_100.00_PASS.pdf",
                storage_path_original=str(pass_file),
                storage_path_renamed=str(pass_file),
                file_sha256="pass-sha",
                invoice_number="PASS-001",
                invoice_amount=Decimal("100.00"),
                processing_status="completed",
                system_decision="suggested_pass",
                review_status="not_reviewed",
                artifact_status="renamed",
                duplicate_flag=False,
                display_status=DISPLAY_STATUS_PASS,
                risk_flags="[]",
            ),
            InvoiceRecord(
                batch_id=batch.id,
                original_filename="review.pdf",
                storage_path_original=str(review_file),
                file_sha256="review-sha",
                invoice_number="REVIEW-001",
                invoice_amount=Decimal("66.00"),
                processing_status="completed",
                system_decision="review_required",
                review_status="not_reviewed",
                artifact_status="original_only",
                duplicate_flag=False,
                risk_flags='["low_confidence"]',
                problem_count=1,
            ),
        ]
    )
    session.commit()

    service = ExportService(session, storage_root=tmp_path / "storage")

    with pytest.raises(ValueError, match="当前批次仍有待复核票据"):
        service.create_export(
            batch_id=batch.id,
            export_type="suggested_pass_zip",
            created_by="tester",
        )

    denied_audits = session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "export_job", AuditLog.entity_id == batch.id, AuditLog.action == "export_denied")
        .order_by(AuditLog.changed_at.asc())
    ).all()
    assert len(denied_audits) == 1
    assert denied_audits[0].change_reason == "pending_manual_review"
    assert json.loads(denied_audits[0].payload_json) == {
        "batch_id": batch.id,
        "export_type": "suggested_pass_zip",
        "gate": {
            "allowed": False,
            "reasons": ["pending_manual_review"],
        },
    }

    review_invoice = session.scalar(
        select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id, InvoiceRecord.original_filename == "review.pdf")
    )
    assert review_invoice is not None
    session.add(
        AttachmentDocument(
            batch_id=batch.id,
            original_filename="review-销货清单.pdf",
            storage_path_original=str(review_file),
            file_sha256="review-attachment-sha",
            attachment_status="consumed",
            matched_invoice_id=review_invoice.id,
            match_reason="Matched by invoice_number; reclassified the invoice using attachment line items.",
        )
    )
    review_invoice.review_status = "manually_approved"
    session.commit()

    pass_result = service.create_export(
        batch_id=batch.id,
        export_type="suggested_pass_zip",
        created_by="tester",
    )
    assert pass_result.summary == {"record_count": 2, "total_amount": "166.00"}
    with ZipFile(pass_result.output_path) as archive:
        assert set(archive.namelist()) == {"20260417_100.00_PASS.pdf", "review.pdf"}

    excel_result = service.create_export(
        batch_id=batch.id,
        export_type="excel_manifest",
        created_by="tester",
    )
    assert excel_result.summary == {
        "record_count": 2,
        "suggested_pass_count": 2,
        "suggested_pass_total_amount": "166.00",
    }
    with ZipFile(excel_result.output_path) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "基础合规" in sheet_xml
    assert "业务合规" in sheet_xml
    assert "最终结论" in sheet_xml
    assert "结论原因" in sheet_xml
    assert "建议动作" in sheet_xml
    assert "清单附件" in sheet_xml
    assert "附件识别" in sheet_xml
    assert "附件匹配依据" in sheet_xml
    assert "review-销货清单.pdf" in sheet_xml
    assert "已消费" in sheet_xml
    assert "Matched by invoice_number" in sheet_xml
    assert "人工确认通过" in sheet_xml
    assert "纳入建议通过归档" in sheet_xml

    completed_audits = session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "export_job", AuditLog.action == "export_completed")
        .order_by(AuditLog.changed_at.asc())
    ).all()
    assert len(completed_audits) == 2
    assert [audit.entity_id for audit in completed_audits] == [pass_result.job_id, excel_result.job_id]
    assert [audit.change_summary for audit in completed_audits] == [
        "export_type=suggested_pass_zip",
        "export_type=excel_manifest",
    ]
    assert [
        json.loads(audit.payload_json)["gate"] for audit in completed_audits
    ] == [
        {"allowed": True, "reasons": []},
        {"allowed": True, "reasons": []},
    ]
