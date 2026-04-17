from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy import select
from starlette.testclient import TestClient

from backend.app.db.models import Batch, InvoiceRecord, ProcessingAttempt, ProcessingJob
from backend.app.main import create_app
from backend.app.services.batch_service import BatchService, IncomingFile
from backend.app.services.config_service import ConfigService
from backend.app.services.processing_service import ProcessingService
from backend.app.services.progress_service import ProgressService
from backend.app.services.recovery_service import RecoveryService
from backend.app.services.retry_service import RetryService
from backend.app.services.storage_service import StorageService


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "invoices"


def seed_active_rules(session) -> None:
    service = ConfigService(session)
    service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000X"},
        changed_by="fin-admin",
        change_summary="seed tax profile",
        change_reason="recovery fixture",
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
        change_reason="recovery fixture",
    )
    service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="seed naming rules",
        change_reason="recovery fixture",
    )


def wait_for_batch_state(
    session_factory,
    batch_id: str,
    expected_status: str,
    *,
    timeout: float = 5.0,
) -> Batch:
    deadline = time.monotonic() + timeout
    last_batch: Batch | None = None
    while time.monotonic() < deadline:
        session = session_factory()
        try:
            ProgressService(session).refresh_batch(batch_id)
            batch = session.get(Batch, batch_id)
            assert batch is not None
            session.refresh(batch)
            if batch.status == expected_status:
                return batch
            last_batch = batch
        finally:
            session.close()
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for batch {batch_id!r} to become {expected_status!r}: {last_batch!r}")


def test_recovery_service_requeues_stale_running_jobs_on_startup(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'processing-recovery.db'}")
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
                content=(FIXTURE_DIR / "01-standard-electronic.pdf").read_bytes(),
            )
        ],
        created_by="tester",
        batch_no="BATCH-RECOVERY-001",
    )
    invoice = session.scalar(select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id))
    assert invoice is not None
    batch_id = batch.id
    invoice_id = invoice.id

    stale_job = ProcessingJob(
        batch_id=batch.id,
        status="running",
        current_stage="text_extraction",
        total_items=1,
        completed_items=0,
        failed_items=0,
        recovery_token="recovery-startup-001",
    )
    session.add(stale_job)
    session.flush()

    stale_attempt = ProcessingAttempt(
        job_id=stale_job.id,
        invoice_id=invoice.id,
        attempt_no=1,
        status="running",
        stage="text_extraction",
        input_sha256=invoice.file_sha256,
    )
    session.add(stale_attempt)
    session.flush()
    batch.active_job_id = stale_job.id
    batch.status = "processing"
    batch.last_stage_code = "text_extraction"
    batch.last_stage_text = "文本抽取中"
    invoice.processing_status = "processing"
    invoice.processing_stage = "text_extraction"
    invoice.last_attempt_id = stale_attempt.id
    session.commit()
    session.close()

    with TestClient(app):
        recovered = wait_for_batch_state(app.state.session_factory, batch_id, "completed")

    session = app.state.session_factory()
    try:
        refreshed_batch = session.get(Batch, batch_id)
        refreshed_invoice = session.get(InvoiceRecord, invoice_id)
        assert refreshed_batch is not None
        assert refreshed_invoice is not None
        assert recovered.last_recovered_at is not None
        assert refreshed_batch.last_recovered_at is not None
        assert refreshed_invoice.processing_status == "completed"
        assert refreshed_invoice.retry_count == 1
        attempts = session.query(ProcessingAttempt).where(ProcessingAttempt.invoice_id == invoice_id).all()
        assert len(attempts) == 2
        assert any(attempt.status == "succeeded" for attempt in attempts)
    finally:
        session.close()


def test_retry_service_retries_only_failed_invoices_without_touching_completed_results(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'processing-retry.db'}")
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
                content=(FIXTURE_DIR / "01-standard-electronic.pdf").read_bytes(),
            ),
            IncomingFile(
                filename="broken.pdf",
                content=b"%PDF-1.7\nbroken fixture",
            ),
        ],
        created_by="tester",
        batch_no="BATCH-RETRY-001",
    )
    ProcessingService(session=session, storage_root=app.state.storage_root).process_batch(batch.id)

    completed_invoice = session.scalar(
        select(InvoiceRecord)
        .where(InvoiceRecord.batch_id == batch.id, InvoiceRecord.processing_status == "completed")
        .order_by(InvoiceRecord.original_filename.asc())
    )
    failed_invoice = session.scalar(
        select(InvoiceRecord)
        .where(InvoiceRecord.batch_id == batch.id, InvoiceRecord.processing_status == "processing_failed")
        .order_by(InvoiceRecord.original_filename.asc())
    )
    assert completed_invoice is not None
    assert failed_invoice is not None
    completed_attempt_id = completed_invoice.last_attempt_id

    session.close()

    retry_session = app.state.session_factory()
    try:
        retried_ids = RetryService(
            session=retry_session,
            processing_runner=app.state.processing_runner,
        ).retry_batch_failures(batch.id)
        assert retried_ids == [failed_invoice.id]
    finally:
        retry_session.close()

    wait_for_batch_state(app.state.session_factory, batch.id, "completed")

    verify_session = app.state.session_factory()
    try:
        refreshed_completed = verify_session.get(InvoiceRecord, completed_invoice.id)
        refreshed_failed = verify_session.get(InvoiceRecord, failed_invoice.id)
        assert refreshed_completed is not None
        assert refreshed_failed is not None

        assert refreshed_completed.last_attempt_id == completed_attempt_id
        assert refreshed_completed.retry_count == 0

        assert refreshed_failed.processing_status == "processing_failed"
        assert refreshed_failed.retry_count == 1
        attempts = verify_session.query(ProcessingAttempt).where(ProcessingAttempt.invoice_id == failed_invoice.id).all()
        assert len(attempts) == 2
        assert attempts[-1].attempt_no == 2
    finally:
        verify_session.close()


def test_recovery_service_marks_stale_attempts_before_requeue(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'processing-recovery-service.db'}")
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
                content=(FIXTURE_DIR / "01-standard-electronic.pdf").read_bytes(),
            )
        ],
        created_by="tester",
        batch_no="BATCH-RECOVERY-002",
    )
    invoice = session.scalar(select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id))
    assert invoice is not None
    batch_id = batch.id
    stale_attempt_id = None

    stale_job = ProcessingJob(
        batch_id=batch.id,
        status="running",
        current_stage="classification",
        total_items=1,
        completed_items=0,
        failed_items=0,
        recovery_token="recovery-service-002",
    )
    session.add(stale_job)
    session.flush()
    stale_attempt = ProcessingAttempt(
        job_id=stale_job.id,
        invoice_id=invoice.id,
        attempt_no=1,
        status="running",
        stage="classification",
        input_sha256=invoice.file_sha256,
    )
    session.add(stale_attempt)
    session.flush()
    stale_attempt_id = stale_attempt.id
    batch.active_job_id = stale_job.id
    batch.status = "processing"
    invoice.processing_status = "processing"
    invoice.processing_stage = "classification"
    invoice.last_attempt_id = stale_attempt.id
    session.commit()

    recovered_ids = RecoveryService(
        session=session,
        processing_runner=app.state.processing_runner,
    ).recover_stale_jobs()
    assert recovered_ids == [batch_id]
    session.close()

    wait_for_batch_state(app.state.session_factory, batch_id, "completed")

    verify_session = app.state.session_factory()
    try:
        recovered_attempt = verify_session.get(ProcessingAttempt, stale_attempt_id)
        assert recovered_attempt is not None
        assert recovered_attempt.status == "failed"
        assert recovered_attempt.error_code == "stale_recovery"
    finally:
        verify_session.close()
