from __future__ import annotations

from datetime import UTC, datetime
from logging import Logger

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_app_logger, log_event
from backend.app.db.models import Batch, InvoiceRecord, ProcessingAttempt, ProcessingJob


STAGE_TEXTS = {
    "queued": "等待处理",
    "recovering": "恢复处理中",
}
RECOVERABLE_JOB_STATUSES = {"queued", "running", "recovering"}
RECOVERABLE_ATTEMPT_STATUSES = {"queued", "running"}
TERMINAL_INVOICE_STATUSES = {"completed", "processing_failed"}


class RecoveryService:
    def __init__(
        self,
        *,
        session: Session,
        processing_runner,
        logger: Logger | None = None,
    ) -> None:
        self.session = session
        self.processing_runner = processing_runner
        self.logger = logger or get_app_logger("recovery")

    def recover_stale_jobs(self) -> list[str]:
        batches = self.session.scalars(
            select(Batch)
            .where(Batch.active_job_id.is_not(None))
            .order_by(Batch.created_at.asc())
        ).all()
        recovered_batch_ids: list[str] = []

        for batch in batches:
            job = (
                self.session.get(ProcessingJob, batch.active_job_id)
                if batch.active_job_id
                else None
            )
            if job is None or job.status not in RECOVERABLE_JOB_STATUSES:
                continue
            if self._batch_is_terminal(batch.id):
                continue

            self._mark_job_for_recovery(batch=batch, job=job)
            recovered_batch_ids.append(batch.id)

        self.session.commit()

        for batch_id in recovered_batch_ids:
            self.processing_runner.enqueue(batch_id)
            log_event(self.logger, "processing_job_recovered", batch_id=batch_id)

        return recovered_batch_ids

    def _mark_job_for_recovery(self, *, batch: Batch, job: ProcessingJob) -> None:
        now = datetime.now(UTC)
        stale_attempts = self.session.scalars(
            select(ProcessingAttempt).where(
                ProcessingAttempt.job_id == job.id,
                ProcessingAttempt.status.in_(RECOVERABLE_ATTEMPT_STATUSES),
            )
        ).all()

        stale_attempt_ids = {attempt.id for attempt in stale_attempts}
        for attempt in stale_attempts:
            attempt.status = "failed"
            attempt.retryable = True
            attempt.error_code = "stale_recovery"
            attempt.error_message = "Recovered after runtime restart."
            attempt.completed_at = now

        invoices = self.session.scalars(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
        ).all()
        for invoice in invoices:
            if (
                invoice.processing_status in TERMINAL_INVOICE_STATUSES
                and invoice.id not in {attempt.invoice_id for attempt in stale_attempts}
            ):
                continue
            if (
                stale_attempt_ids
                and invoice.last_attempt_id not in stale_attempt_ids
                and invoice.processing_status == "completed"
            ):
                continue
            if invoice.processing_status == "completed":
                continue
            invoice.processing_status = "queued"
            invoice.processing_stage = "queued"
            invoice.last_error_stage = invoice.last_error_stage or job.current_stage
            invoice.last_error_code = "stale_recovery"
            invoice.last_error_message = "Recovered after runtime restart."
            invoice.retryable = True

        job.status = "recovering"
        job.current_stage = "recovering"
        job.completed_at = now
        job.last_heartbeat_at = now

        batch.active_job_id = None
        batch.status = "processing"
        batch.last_recovered_at = now
        batch.last_stage_code = "queued"
        batch.last_stage_text = STAGE_TEXTS["queued"]

        self.session.flush()

    def _batch_is_terminal(self, batch_id: str) -> bool:
        invoices = self.session.scalars(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch_id)
        ).all()
        return bool(invoices) and all(
            invoice.processing_status in TERMINAL_INVOICE_STATUSES
            for invoice in invoices
        )
