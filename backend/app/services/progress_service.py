from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import UTC, datetime
from logging import Logger
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_app_logger, log_event
from backend.app.db.models import Batch, InvoiceRecord, ProcessingAttempt, ProcessingJob
from backend.app.services.status_service import summarize_suggested_pass

PROCESSING_FAILED_STATUSES = {"failed", "processing_failed"}
MAX_RECENT_FAILURES = 3
STAGE_TEXTS = {
    "queued": "等待处理",
    "recovering": "恢复处理中",
    "text_extraction": "文本抽取中",
    "ocr_processing": "OCR 识别中",
    "classification": "规则校验中",
    "duplicate_check": "重复票检测中",
    "finalization": "结果归档中",
    "completed": "批次处理完成",
    "failed": "批次处理失败",
}


@dataclass(frozen=True)
class BatchProgressSnapshot:
    batch_id: str
    batch_no: str
    stage_code: str
    stage_text: str
    progress_percent: float
    total_files: int
    completed_files: int
    processing_files: int
    failed_files: int
    suggested_pass_count: int
    suggested_pass_total_amount: Decimal
    recent_failures: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "batch_no": self.batch_no,
            "stage_code": self.stage_code,
            "stage_text": self.stage_text,
            "progress_percent": self.progress_percent,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "processing_files": self.processing_files,
            "failed_files": self.failed_files,
            "suggested_pass_count": self.suggested_pass_count,
            "suggested_pass_total_amount": f"{self.suggested_pass_total_amount:.2f}",
            "recent_failures": self.recent_failures,
        }


class ProgressService:
    def __init__(self, session: Session, *, logger: Logger | None = None) -> None:
        self.session = session
        self.logger = logger or get_app_logger("progress")

    def refresh_batch(
        self, batch_id: str, *, persist: bool = True
    ) -> BatchProgressSnapshot:
        batch = self.session.get(Batch, batch_id)
        if batch is None:
            raise LookupError(f"Batch {batch_id!r} not found.")

        invoices = self.session.scalars(
            select(InvoiceRecord)
            .where(InvoiceRecord.batch_id == batch_id)
            .order_by(InvoiceRecord.original_filename.asc())
        ).all()

        total_files = len(invoices)
        completed_files = sum(
            1 for invoice in invoices if invoice.processing_status == "completed"
        )
        failed_files = sum(
            1
            for invoice in invoices
            if invoice.processing_status in PROCESSING_FAILED_STATUSES
        )
        processing_files = max(total_files - completed_files - failed_files, 0)
        pass_summary = summarize_suggested_pass(invoices)

        batch.total_files = total_files
        batch.completed_files = completed_files
        batch.failed_files = failed_files
        batch.processing_files = processing_files
        batch.suggested_pass_count = pass_summary.count
        batch.suggested_pass_total_amount = pass_summary.total_amount
        batch.status = self._derive_batch_status(
            total_files=total_files,
            completed_files=completed_files,
            processing_files=processing_files,
            failed_files=failed_files,
        )

        if persist:
            self.session.commit()
            self.session.refresh(batch)

        snapshot = self._build_snapshot(batch, invoices)
        log_event(
            self.logger,
            "batch_progress_refreshed",
            batch_id=batch.id,
            batch_no=batch.batch_no,
            stage_code=snapshot.stage_code,
            progress_percent=snapshot.progress_percent,
            failed_files=snapshot.failed_files,
        )
        return snapshot

    @staticmethod
    def _derive_batch_status(
        *,
        total_files: int,
        completed_files: int,
        processing_files: int,
        failed_files: int,
    ) -> str:
        if total_files == 0:
            return "queued"
        if processing_files > 0:
            return "processing"
        if failed_files == total_files:
            return "failed"
        if completed_files + failed_files >= total_files:
            return "completed"
        return "queued"

    def _build_snapshot(
        self, batch: Batch, invoices: list[InvoiceRecord]
    ) -> BatchProgressSnapshot:
        if batch.total_files == 0:
            progress_percent = 0.0
        else:
            progress_percent = round(
                ((batch.completed_files + batch.failed_files) / batch.total_files)
                * 100,
                2,
            )

        active_job = (
            self.session.get(ProcessingJob, batch.active_job_id)
            if batch.active_job_id
            else None
        )
        if batch.status == "processing":
            if batch.last_stage_code:
                stage_code = batch.last_stage_code
                stage_text = batch.last_stage_text or STAGE_TEXTS.get(
                    stage_code, stage_code
                )
            elif active_job is not None and active_job.current_stage:
                stage_code = active_job.current_stage
                stage_text = STAGE_TEXTS.get(stage_code, stage_code)
            else:
                stage_code = "processing"
                stage_text = "解析与规则处理中"
        elif batch.status == "completed":
            stage_code = "completed"
            stage_text = "批次处理完成"
        elif batch.status == "failed":
            stage_code = "failed"
            stage_text = "批次处理失败"
        else:
            stage_code = "queued"
            stage_text = "等待处理"

        recent_failures = [
            self._serialize_recent_failure(invoice)
            for invoice in self._recent_failures(invoices)
        ]

        return BatchProgressSnapshot(
            batch_id=batch.id,
            batch_no=batch.batch_no,
            stage_code=stage_code,
            stage_text=stage_text,
            progress_percent=progress_percent,
            total_files=batch.total_files,
            completed_files=batch.completed_files,
            processing_files=batch.processing_files,
            failed_files=batch.failed_files,
            suggested_pass_count=batch.suggested_pass_count,
            suggested_pass_total_amount=batch.suggested_pass_total_amount,
            recent_failures=recent_failures,
        )

    def _serialize_recent_failure(self, invoice: InvoiceRecord) -> dict[str, object]:
        attempt = self._last_attempt(invoice)
        provider_diagnostic = (
            self._load_json(attempt.diagnostic_json, {}) if attempt is not None else {}
        )
        return {
            "invoice_id": invoice.id,
            "original_filename": invoice.original_filename,
            "failure_reason": invoice.failure_reason,
            "failure_stage": invoice.last_error_stage,
            "error_code": invoice.last_error_code,
            "retryable": invoice.retryable,
            "parse_source": invoice.parse_source,
            "provider_diagnostic": provider_diagnostic,
        }

    def _recent_failures(self, invoices: list[InvoiceRecord]) -> list[InvoiceRecord]:
        failed_invoices = [
            invoice
            for invoice in invoices
            if invoice.processing_status in PROCESSING_FAILED_STATUSES
        ]
        return sorted(failed_invoices, key=self._recent_failure_sort_key, reverse=True)[
            :MAX_RECENT_FAILURES
        ]

    def _recent_failure_sort_key(
        self, invoice: InvoiceRecord
    ) -> tuple[float, int, str]:
        attempt = self._last_attempt(invoice)
        failure_time = attempt.completed_at if attempt is not None else None
        if failure_time is None and attempt is not None:
            failure_time = attempt.started_at
        failure_timestamp = (
            failure_time.timestamp()
            if isinstance(failure_time, datetime)
            else datetime.min.replace(tzinfo=UTC).timestamp()
        )
        attempt_no = attempt.attempt_no if attempt is not None else -1
        return (failure_timestamp, attempt_no, invoice.original_filename)

    def _last_attempt(self, invoice: InvoiceRecord) -> ProcessingAttempt | None:
        return (
            self.session.get(ProcessingAttempt, invoice.last_attempt_id)
            if invoice.last_attempt_id
            else None
        )

    @staticmethod
    def _load_json(value: str | None, fallback: dict[str, object]) -> dict[str, object]:
        if not value:
            return fallback
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return fallback
        return payload if isinstance(payload, dict) else fallback
