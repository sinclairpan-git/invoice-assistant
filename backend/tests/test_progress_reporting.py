import logging
from decimal import Decimal

from backend.app.db.models import Batch, InvoiceRecord
from backend.app.db.session import create_database_engine, create_session_factory, init_db
from backend.app.services.progress_service import ProgressService


def build_session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'progress.db'}"
    engine = create_database_engine(database_url)
    init_db(engine)
    return create_session_factory(engine)()


def test_progress_service_refreshes_batch_snapshot_and_logs_events(tmp_path, caplog):
    session = build_session(tmp_path)

    batch = Batch(batch_no="BATCH-PROGRESS-001", created_by="tester", snapshot_json="{}")
    session.add(batch)
    session.flush()

    completed_invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="completed.pdf",
        storage_path_original="storage/originals/BATCH-PROGRESS-001/completed.pdf",
        file_sha256="completed-sha",
        invoice_amount=Decimal("50.00"),
        processing_status="completed",
        system_decision="suggested_pass",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
    )
    failed_invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="failed.pdf",
        storage_path_original="storage/originals/BATCH-PROGRESS-001/failed.pdf",
        file_sha256="failed-sha",
        processing_status="failed",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
        failure_reason="OCR failed",
    )
    processing_invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="processing.pdf",
        storage_path_original="storage/originals/BATCH-PROGRESS-001/processing.pdf",
        file_sha256="processing-sha",
        processing_status="extracting",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
    )

    session.add_all(
        [
            completed_invoice,
            failed_invoice,
            processing_invoice,
        ]
    )
    session.commit()

    with caplog.at_level(logging.INFO, logger="invoice_assistant.progress"):
        snapshot = ProgressService(session).refresh_batch(batch.id)

    session.refresh(batch)

    assert snapshot.batch_no == "BATCH-PROGRESS-001"
    assert snapshot.stage_code == "processing"
    assert snapshot.stage_text == "解析与规则处理中"
    assert snapshot.progress_percent == 66.67
    assert snapshot.total_files == 3
    assert snapshot.completed_files == 1
    assert snapshot.failed_files == 1
    assert snapshot.processing_files == 1
    assert snapshot.suggested_pass_count == 1
    assert snapshot.suggested_pass_total_amount == Decimal("50.00")
    assert snapshot.recent_failures == [
        {
            "invoice_id": failed_invoice.id,
            "original_filename": "failed.pdf",
            "failure_reason": "OCR failed",
        }
    ]

    assert batch.status == "processing"
    assert batch.completed_files == 1
    assert batch.failed_files == 1
    assert batch.processing_files == 1
    assert batch.suggested_pass_total_amount == Decimal("50.00")

    assert any(
        record.name == "invoice_assistant.progress" and "batch_progress_refreshed" in record.message
        for record in caplog.records
    )
