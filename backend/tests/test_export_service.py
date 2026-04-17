from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select
import pytest

from backend.app.db.models import Batch, ExportJob, InvoiceRecord
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

    batch = Batch(batch_no="BATCH-EXPORT-001", created_by="tester", snapshot_json="{}")
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

    batch = Batch(batch_no="BATCH-EXPORT-FAIL", created_by="tester", snapshot_json="{}")
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

