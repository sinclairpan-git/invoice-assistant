from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import InvoiceRecord, ReviewQueueItem
from backend.app.services.status_service import (
    BUSINESS_BUCKET_BATCH_DUPLICATE,
    BUSINESS_BUCKET_PENDING_REVIEW,
    derive_business_bucket,
    derive_stable_status,
)


REVIEW_QUEUE_REASON_LABELS = {
    "system_review_required": "系统要求人工确认",
    "duplicate_review": "本批次重复待判断",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ReviewQueueService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def sync_invoice(self, invoice: InvoiceRecord) -> ReviewQueueItem | None:
        should_open, queue_reason = self._resolve_queue_reason(invoice)
        item = self.session.scalar(
            select(ReviewQueueItem).where(ReviewQueueItem.invoice_id == invoice.id)
        )
        now = _utc_now()

        if not should_open or queue_reason is None:
            if item is not None and item.queue_status == "open":
                item.queue_status = "closed"
                item.closed_at = now
                item.closed_reason = "no_longer_required"
                item.updated_at = now
                item.version_no += 1
            return item

        if item is None:
            item = ReviewQueueItem(
                batch_id=invoice.batch_id,
                invoice_id=invoice.id,
                queue_status="open",
                queue_reason=queue_reason,
                version_no=1,
                opened_at=now,
                updated_at=now,
            )
            self.session.add(item)
            return item

        if item.queue_status != "open":
            item.queue_status = "open"
            item.opened_at = now
            item.closed_at = None
            item.closed_reason = None
            item.version_no += 1
        if item.queue_reason != queue_reason:
            item.queue_reason = queue_reason
            item.version_no += 1
        item.updated_at = now
        return item

    def sync_batch(self, batch_id: str) -> None:
        invoices = self.session.scalars(
            select(InvoiceRecord)
            .where(InvoiceRecord.batch_id == batch_id)
            .order_by(InvoiceRecord.original_filename.asc())
        ).all()
        for invoice in invoices:
            self.sync_invoice(invoice)

    def sync_all(self) -> None:
        invoices = self.session.scalars(
            select(InvoiceRecord).order_by(InvoiceRecord.batch_id, InvoiceRecord.original_filename)
        ).all()
        for invoice in invoices:
            self.sync_invoice(invoice)

    def list_open_items(self, *, batch_id: str | None = None) -> list[ReviewQueueItem]:
        if batch_id is None:
            self.sync_all()
        else:
            self.sync_batch(batch_id)
        self.session.flush()

        statement = (
            select(ReviewQueueItem)
            .where(ReviewQueueItem.queue_status == "open")
            .order_by(ReviewQueueItem.opened_at.asc(), ReviewQueueItem.id.asc())
        )
        if batch_id is not None:
            statement = statement.where(ReviewQueueItem.batch_id == batch_id)
        return self.session.scalars(statement).all()

    @staticmethod
    def _resolve_queue_reason(invoice: InvoiceRecord) -> tuple[bool, str | None]:
        stable_status = derive_stable_status(
            processing_status=invoice.processing_status,
            system_decision=invoice.system_decision,
            duplicate_flag=invoice.duplicate_flag,
            review_status=invoice.review_status,
            archive_status=invoice.archive_status,
            artifact_status=invoice.artifact_status,
        )
        business_bucket = derive_business_bucket(
            processing_status=stable_status.processing_status,
            system_decision=invoice.system_decision,
            duplicate_flag=invoice.duplicate_flag,
            review_status=stable_status.review_status,
        )
        if stable_status.processing_status != "completed":
            return False, None
        if stable_status.review_status in {"approved", "rejected"}:
            return False, None
        if business_bucket == BUSINESS_BUCKET_PENDING_REVIEW:
            return True, "system_review_required"
        if business_bucket == BUSINESS_BUCKET_BATCH_DUPLICATE:
            return True, "duplicate_review"
        return False, None
