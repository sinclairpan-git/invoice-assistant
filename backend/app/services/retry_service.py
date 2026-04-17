from __future__ import annotations

from logging import Logger

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_app_logger, log_event
from backend.app.db.models import Batch, InvoiceRecord


STAGE_TEXTS = {
    "queued": "等待处理",
}


class RetryService:
    def __init__(
        self,
        *,
        session: Session,
        processing_runner,
        logger: Logger | None = None,
    ) -> None:
        self.session = session
        self.processing_runner = processing_runner
        self.logger = logger or get_app_logger("retry")

    def retry_invoice(self, invoice_id: str) -> str:
        invoice = self.session.get(InvoiceRecord, invoice_id)
        if invoice is None:
            raise LookupError(f"Invoice {invoice_id!r} not found.")
        if invoice.processing_status != "processing_failed":
            raise ValueError(f"Invoice {invoice_id!r} is not in a retryable failed state.")

        self._prepare_invoice(invoice)
        batch = self.session.get(Batch, invoice.batch_id)
        if batch is None:
            raise LookupError(f"Batch for invoice {invoice_id!r} not found.")
        self._prepare_batch(batch)
        self.session.commit()
        self.processing_runner.enqueue(batch.id)
        log_event(self.logger, "invoice_retry_enqueued", batch_id=batch.id, invoice_id=invoice_id)
        return invoice_id

    def retry_batch_failures(self, batch_id: str) -> list[str]:
        batch = self.session.get(Batch, batch_id)
        if batch is None:
            raise LookupError(f"Batch {batch_id!r} not found.")

        failed_invoices = self.session.scalars(
            select(InvoiceRecord)
            .where(InvoiceRecord.batch_id == batch_id, InvoiceRecord.processing_status == "processing_failed")
            .order_by(InvoiceRecord.original_filename.asc())
        ).all()
        if not failed_invoices:
            return []

        for invoice in failed_invoices:
            self._prepare_invoice(invoice)
        self._prepare_batch(batch)
        self.session.commit()
        self.processing_runner.enqueue(batch.id)
        log_event(self.logger, "batch_retry_enqueued", batch_id=batch.id, invoice_count=len(failed_invoices))
        return [invoice.id for invoice in failed_invoices]

    @staticmethod
    def _prepare_invoice(invoice: InvoiceRecord) -> None:
        invoice.processing_status = "queued"
        invoice.processing_stage = "queued"
        invoice.failure_reason = None
        invoice.last_error_stage = None
        invoice.last_error_code = None
        invoice.last_error_message = None
        invoice.retryable = False

    @staticmethod
    def _prepare_batch(batch: Batch) -> None:
        batch.status = "processing"
        batch.last_stage_code = "queued"
        batch.last_stage_text = STAGE_TEXTS["queued"]
