import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from backend.app.db.models import Batch, InvoiceRecord, ProcessingAttempt, ProcessingJob
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
        processing_stage="ocr_processing",
        parse_source="ocr",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
        failure_reason="OCR failed",
        last_error_stage="ocr_processing",
        last_error_code="ocr_timeout",
        retryable=True,
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
    session.flush()

    failed_job = ProcessingJob(
        batch_id=batch.id,
        status="completed_with_failures",
        current_stage="failed",
        total_items=3,
        completed_items=1,
        failed_items=1,
    )
    session.add(failed_job)
    session.flush()

    failed_attempt = ProcessingAttempt(
        job_id=failed_job.id,
        invoice_id=failed_invoice.id,
        attempt_no=1,
        status="retryable_failed",
        stage="ocr_processing",
        parse_source="ocr",
        provider_name="rapidocr-onnxruntime",
        provider_version="1.3.24",
        error_code="ocr_timeout",
        error_message="OCR failed",
        retryable=True,
        diagnostic_json=json.dumps(
            {
                "provider_name": "rapidocr-onnxruntime",
                "provider_version": "1.3.24",
                "provider_error_code": "ocr_timeout",
                "stage": "ocr_processing",
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    session.add(failed_attempt)
    session.flush()
    failed_invoice.last_attempt_id = failed_attempt.id
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
            "failure_stage": "ocr_processing",
            "error_code": "ocr_timeout",
            "retryable": True,
            "parse_source": "ocr",
            "provider_diagnostic": {
                "provider_name": "rapidocr-onnxruntime",
                "provider_version": "1.3.24",
                "provider_error_code": "ocr_timeout",
                "stage": "ocr_processing",
            },
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


def test_progress_service_prefers_active_job_stage_for_processing_snapshot(tmp_path):
    session = build_session(tmp_path)

    batch = Batch(
        batch_no="BATCH-PROGRESS-002",
        created_by="tester",
        snapshot_json="{}",
        status="processing",
    )
    session.add(batch)
    session.flush()

    invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="processing.pdf",
        storage_path_original="storage/originals/BATCH-PROGRESS-002/processing.pdf",
        file_sha256="processing-sha",
        processing_status="processing",
        processing_stage="duplicate_check",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
    )
    session.add(invoice)
    session.flush()

    job = ProcessingJob(
        batch_id=batch.id,
        status="running",
        current_stage="duplicate_check",
        total_items=1,
        completed_items=0,
        failed_items=0,
        recovery_token="progress-runtime-002",
    )
    session.add(job)
    session.flush()

    attempt = ProcessingAttempt(
        job_id=job.id,
        invoice_id=invoice.id,
        attempt_no=1,
        status="running",
        stage="duplicate_check",
        input_sha256="processing-input-sha",
    )
    session.add(attempt)
    batch.active_job_id = job.id
    batch.last_stage_code = "duplicate_check"
    batch.last_stage_text = "重复票检测中"
    invoice.last_attempt_id = attempt.id
    session.commit()

    snapshot = ProgressService(session).refresh_batch(batch.id)

    assert snapshot.stage_code == "duplicate_check"
    assert snapshot.stage_text == "重复票检测中"
    assert snapshot.progress_percent == 0.0


def test_progress_service_limits_recent_failures_to_latest_three(tmp_path):
    session = build_session(tmp_path)

    batch = Batch(
        batch_no="BATCH-PROGRESS-003",
        created_by="tester",
        snapshot_json="{}",
        status="processing",
    )
    session.add(batch)
    session.flush()

    base_time = datetime(2026, 4, 18, 10, 0, tzinfo=UTC)
    expected_order: list[str] = []

    for index in range(5):
        invoice = InvoiceRecord(
            batch_id=batch.id,
            original_filename=f"failed-{index}.pdf",
            storage_path_original=f"storage/originals/BATCH-PROGRESS-003/failed-{index}.pdf",
            file_sha256=f"failed-sha-{index}",
            processing_status="processing_failed",
            processing_stage="failed",
            parse_source="ocr",
            review_status="not_reviewed",
            artifact_status="original_only",
            duplicate_flag=False,
            risk_flags="[]",
            failure_reason=f"OCR failed #{index}",
            last_error_stage="ocr_processing",
            last_error_code=f"ocr_timeout_{index}",
            retryable=True,
        )
        session.add(invoice)
        session.flush()

        attempt = ProcessingAttempt(
            job_id="job-recent-failures",
            invoice_id=invoice.id,
            attempt_no=1,
            status="retryable_failed",
            stage="ocr_processing",
            parse_source="ocr",
            provider_name="rapidocr-onnxruntime",
            provider_version="1.3.24",
            error_code=f"ocr_timeout_{index}",
            error_message=f"OCR failed #{index}",
            retryable=True,
            completed_at=base_time + timedelta(minutes=index),
            diagnostic_json=json.dumps(
                {
                    "provider_name": "rapidocr-onnxruntime",
                    "provider_version": "1.3.24",
                    "provider_error_code": f"ocr_timeout_{index}",
                    "stage": "ocr_processing",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        session.add(attempt)
        session.flush()
        invoice.last_attempt_id = attempt.id

        if index >= 2:
            expected_order.insert(0, invoice.original_filename)

    session.commit()

    snapshot = ProgressService(session).refresh_batch(batch.id)

    assert [item["original_filename"] for item in snapshot.recent_failures] == expected_order
    assert len(snapshot.recent_failures) == 3
