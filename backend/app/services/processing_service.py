from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from logging import Logger
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_app_logger, log_event
from backend.app.db.models import (
    AttachmentDocument,
    Batch,
    ExtractedField,
    FieldCheck,
    InvoiceRecord,
    ProcessingAttempt,
    ProcessingJob,
)
from backend.app.services.naming_service import (
    DEFAULT_NAMING_TEMPLATE,
    build_renamed_filename,
)
from backend.app.services.parsing.evidence_models import (
    EvidenceAdapterError,
    StructuredParseError,
    UnifiedDocumentEvidence,
)
from backend.app.services.parsing.providers import (
    ProviderExtractionPayload,
    adapt_ocr_output,
    adapt_text_extraction,
    extract_local_ocr,
    extract_pdf_text,
)
from backend.app.services.rules.buyer_validation import (
    BuyerValidationResult,
    validate_buyer_fields,
)
from backend.app.services.review_queue_service import ReviewQueueService
from backend.app.services.rules.duplicate_detector import detect_suspected_duplicate
from backend.app.services.rules.risk_classifier import classify_risk
from backend.app.services.status_service import (
    derive_archive_status,
    derive_display_status,
    summarize_suggested_pass,
)


FIXTURE_START_MARKER = "INVOICE_ASSISTANT_FIXTURE_START"
FIXTURE_END_MARKER = "INVOICE_ASSISTANT_FIXTURE_END"
GENERIC_FIELD_PATTERNS = {
    "invoice_number": re.compile(
        r"(?:Invoice(?:\s*No|\s*Number)?|发票号码)[:：]?\s*([A-Z0-9-]+)", re.IGNORECASE
    ),
    "invoice_code": re.compile(
        r"(?:Invoice\s*Code|发票代码)[:：]?\s*([A-Z0-9-]+)", re.IGNORECASE
    ),
    "seller_name": re.compile(r"(?:Seller|销方名称)[:：]?\s*([^\r\n]+)", re.IGNORECASE),
    "buyer_name": re.compile(r"(?:Buyer|购方名称)[:：]?\s*([^\r\n]+)", re.IGNORECASE),
    "buyer_tax_no": re.compile(
        r"(?:Buyer\s*Tax(?:\s*No)?|购方税号)[:：]?\s*([A-Z0-9]+)", re.IGNORECASE
    ),
    "invoice_date": re.compile(
        r"(?:Invoice\s*Date|Date|开票日期)[:：]?\s*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2})",
        re.IGNORECASE,
    ),
    "invoice_amount": re.compile(
        r"(?:Amount|价税合计|金额)[:：]?\s*([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE
    ),
}
r"""
GENERIC_FIELD_PATTERNS = {
    "invoice_number": re.compile(
        r"(?:Invoice(?:\s*No|\s*Number)?|发票(?:号码|号)|鍙戠エ鍙风爜)[:：锛歖?\s*([A-Z0-9][A-Z0-9\s-]{5,})",
        re.IGNORECASE,
    ),
    "invoice_code": re.compile(
        r"(?:Invoice\s*Code|发票代码|鍙戠エ浠ｇ爜)[:：锛歖?\s*([A-Z0-9][A-Z0-9\s-]{5,})",
        re.IGNORECASE,
    ),
    "buyer_name": re.compile(
        r"(?:购买方信息|购买方|Buyer)[\s\S]{0,120}?(?:名称|Name)[:：锛歖?\s*([^\r\n]+)",
        re.IGNORECASE,
    ),
    "buyer_tax_no": re.compile(
        r"(?:购买方信息|购买方|Buyer)[\s\S]{0,220}?(?:统一社会信用代码\s*/?\s*纳税人识别号|统一社会信用代码|纳税人识别号|购方税号|Tax(?:\s*No)?)[:：锛歖?\s*([0-9A-Z][0-9A-Z\s]{5,})",
        re.IGNORECASE,
    ),
    "seller_name": re.compile(
        r"(?:销售方信息|销售方|Seller)[\s\S]{0,120}?(?:名称|Name|閿€鏂瑰悕绉?)[:：锛歖?\s*([^\r\n]+)",
        re.IGNORECASE,
    ),
    "invoice_date": re.compile(
        r"(?:Invoice\s*Date|Date|开票日期|寮€绁ㄦ棩鏈?)[:：锛歖?\s*([0-9]{4}\s*(?:[-/年])\s*[0-9]{1,2}\s*(?:[-/月])\s*[0-9]{1,2}\s*日?)",
        re.IGNORECASE,
    ),
    "invoice_amount": re.compile(
        r"(?:价税合计\s*(?:\(?\s*小写\s*\)?|（小写）)?|小写|Amount|浠风◣鍚堣|閲戦)[^0-9]{0,20}([0-9]+(?:\.[0-9]{1,2})?)",
        re.IGNORECASE,
    ),
}
"""
GENERIC_FIELD_PATTERNS = {
    "invoice_number": re.compile(
        "(?:Invoice(?:\\s*No|\\s*Number)?|\\u53d1\\u7968(?:\\u53f7\\u7801|\\u53f7))[:\\uff1a]?\\s*([A-Z0-9][A-Z0-9\\s-]{5,})",
        re.IGNORECASE,
    ),
    "invoice_code": re.compile(
        "(?:Invoice\\s*Code|\\u53d1\\u7968\\u4ee3\\u7801)[:\\uff1a]?\\s*([A-Z0-9][A-Z0-9\\s-]{5,})",
        re.IGNORECASE,
    ),
    "buyer_name": re.compile(
        "(?:\\u8d2d\\u4e70\\u65b9\\u4fe1\\u606f|\\u8d2d\\u4e70\\u65b9|Buyer)[\\s\\S]{0,120}?(?:\\u540d\\u79f0|Name)[:\\uff1a]?\\s*([^\\r\\n]+)",
        re.IGNORECASE,
    ),
    "buyer_tax_no": re.compile(
        "(?:\\u8d2d\\u4e70\\u65b9\\u4fe1\\u606f|\\u8d2d\\u4e70\\u65b9|Buyer)[\\s\\S]{0,220}?(?:\\u7edf\\u4e00\\u793e\\u4f1a\\u4fe1\\u7528\\u4ee3\\u7801\\s*/?\\s*\\u7eb3\\u7a0e\\u4eba\\u8bc6\\u522b\\u53f7|\\u7edf\\u4e00\\u793e\\u4f1a\\u4fe1\\u7528\\u4ee3\\u7801|\\u7eb3\\u7a0e\\u4eba\\u8bc6\\u522b\\u53f7|\\u8d2d\\u65b9\\u7a0e\\u53f7|Tax(?:\\s*No)?)[:\\uff1a]?\\s*([0-9A-Z][0-9A-Z\\s]{5,})",
        re.IGNORECASE,
    ),
    "seller_name": re.compile(
        "(?:\\u9500\\u552e\\u65b9\\u4fe1\\u606f|\\u9500\\u552e\\u65b9|Seller)[\\s\\S]{0,120}?(?:\\u540d\\u79f0|Name)[:\\uff1a]?\\s*([^\\r\\n]+)",
        re.IGNORECASE,
    ),
    "invoice_date": re.compile(
        "(?:Invoice\\s*Date|Date|\\u5f00\\u7968\\u65e5\\u671f)[:\\uff1a]?\\s*([0-9]{4}\\s*(?:[-/\\u5e74])\\s*[0-9]{1,2}\\s*(?:[-/\\u6708])\\s*[0-9]{1,2}\\s*\\u65e5?)",
        re.IGNORECASE,
    ),
    "invoice_amount": re.compile(
        "(?:\\u4ef7\\u7a0e\\u5408\\u8ba1\\s*(?:\\(?\\s*\\u5c0f\\u5199\\s*\\)?|\\uff08\\u5c0f\\u5199\\uff09)?|\\u5c0f\\u5199|Amount)(?:(?!\\u53d1\\u7968(?:\\u53f7\\u7801|\\u53f7)|Invoice(?:\\s*No|\\s*Number)?)[^0-9]){0,80}[\\u00a5\\uffe5]?\\s*([0-9]{1,12}(?:\\.[0-9]{1,2})?)(?![0-9])",
        re.IGNORECASE,
    ),
}
SUPPORTED_NAMING_KEYS = {
    "{date}": "{date}",
    "{amount}": "{amount}",
    "{invoice_number}": "{invoice_number}",
    "{number}": "{invoice_number}",
}
STAGE_TEXTS = {
    "queued": "等待处理",
    "text_extraction": "文本抽取中",
    "ocr_processing": "OCR 识别中",
    "classification": "规则校验中",
    "duplicate_check": "重复票检测中",
    "finalization": "结果归档中",
    "attachment_matching": "清单匹配中",
    "completed": "批次处理完成",
    "failed": "批次处理失败",
}
TERMINAL_INVOICE_STATUSES = {"completed", "processing_failed"}
RETRYABLE_ERROR_CODES = {
    "pdf_text_extraction_failed",
    "ocr_pdf_render_failed",
    "ocr_no_invoice_fields",
}


@dataclass(frozen=True)
class ParsedDocument:
    evidence: UnifiedDocumentEvidence
    metadata: dict[str, Any]


class ProcessingService:
    def __init__(
        self,
        session: Session,
        *,
        storage_root: Path | str,
        logger: Logger | None = None,
    ) -> None:
        self.session = session
        self.storage_root = Path(storage_root)
        self.logger = logger or get_app_logger("processing")

    def process_batch(self, batch_id: str) -> Batch:
        batch = self.session.get(Batch, batch_id)
        if batch is None:
            raise LookupError(f"Batch {batch_id!r} not found.")

        snapshot = self._load_snapshot(batch.snapshot_json)
        invoices = self.session.scalars(
            select(InvoiceRecord)
            .where(InvoiceRecord.batch_id == batch_id)
            .order_by(InvoiceRecord.original_filename.asc())
        ).all()
        job = self._ensure_job(batch=batch, total_items=len(invoices))
        history = self._build_history_from_completed_invoices(invoices)
        parsed_invoice_evidence: dict[str, UnifiedDocumentEvidence] = {}

        for invoice in invoices:
            if (
                invoice.processing_status in TERMINAL_INVOICE_STATUSES
                and invoice.last_attempt_id
            ):
                continue

            attempt = self._start_attempt(batch=batch, invoice=invoice, job=job)
            try:
                evidence = self._process_invoice(
                    batch=batch,
                    invoice=invoice,
                    snapshot=snapshot,
                    history=history,
                    attempt=attempt,
                )
                self._mark_attempt_succeeded(
                    batch=batch, invoice=invoice, job=job, attempt=attempt
                )
                self.session.commit()
                parsed_invoice_evidence[invoice.id] = evidence
                history.append(
                    {
                        "invoice_number": invoice.invoice_number,
                        "invoice_code": invoice.invoice_code,
                        "seller_name": invoice.seller_name,
                        "invoice_date": invoice.invoice_date,
                        "invoice_amount": invoice.invoice_amount,
                        "system_decision": invoice.system_decision,
                        "risk_flags": json.loads(invoice.risk_flags or "[]"),
                    }
                )
                log_event(
                    self.logger,
                    "invoice_processed",
                    batch_id=batch.id,
                    invoice_id=invoice.id,
                    original_filename=invoice.original_filename,
                    parse_source=invoice.parse_source,
                    decision=invoice.system_decision,
                    duplicate_flag=invoice.duplicate_flag,
                )
            except Exception as exc:
                self.session.rollback()
                self._mark_invoice_failed(
                    invoice_id=invoice.id,
                    attempt_id=attempt.id,
                    job_id=job.id,
                    reason=str(exc),
                )

        self._match_attachments_and_reclassify(
            batch=batch,
            invoices=invoices,
            snapshot=snapshot,
            parsed_invoice_evidence=parsed_invoice_evidence,
        )
        self._finalize_job(batch_id=batch_id, job_id=job.id)
        self.session.refresh(batch)
        return batch

    def _process_invoice(
        self,
        *,
        batch: Batch,
        invoice: InvoiceRecord,
        snapshot: dict[str, Any],
        history: list[dict[str, Any]],
        attempt: ProcessingAttempt,
    ) -> UnifiedDocumentEvidence:
        self._advance_stage(
            batch=batch, invoice=invoice, attempt=attempt, stage_code="text_extraction"
        )
        source_path = self._resolve_storage_path(invoice.storage_path_original)
        parsed = self._parse_document(source_path.read_bytes())
        evidence = parsed.evidence
        attempt.parse_source = evidence.source_type
        attempt.provider_name = evidence.provider_name
        attempt.provider_version = evidence.provider_version
        attempt.diagnostic_json = json.dumps(
            {
                "provider_name": evidence.provider_name,
                "provider_version": evidence.provider_version,
                "provider_error_code": evidence.provider_error_code,
                "confidence_summary": evidence.confidence_summary.model_dump(
                    mode="json"
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self._advance_stage(
            batch=batch, invoice=invoice, attempt=attempt, stage_code="classification"
        )
        buyer_validation = validate_buyer_fields(
            evidence=evidence,
            tax_profile=self._snapshot_content(snapshot, "tax_profile"),
        )
        risk_result = classify_risk(
            evidence=evidence,
            business_rules=self._snapshot_content(snapshot, "business_rules"),
            buyer_validation=buyer_validation,
        )

        invoice.invoice_code = self._candidate_value(evidence, "invoice_code")
        invoice.invoice_number = self._candidate_value(evidence, "invoice_number")
        invoice.seller_name = self._candidate_value(evidence, "seller_name")
        invoice.buyer_name = self._candidate_value(evidence, "buyer_name")
        invoice.buyer_tax_no = self._candidate_value(evidence, "buyer_tax_no")
        invoice.invoice_date = self._candidate_date(evidence, "invoice_date")
        invoice.invoice_amount = self._candidate_amount(evidence, "invoice_amount")
        invoice.parse_source = evidence.source_type

        self._advance_stage(
            batch=batch, invoice=invoice, attempt=attempt, stage_code="duplicate_check"
        )
        duplicate_result = detect_suspected_duplicate(
            invoice_data={
                "invoice_number": invoice.invoice_number,
                "invoice_code": invoice.invoice_code,
                "seller_name": invoice.seller_name,
                "invoice_date": invoice.invoice_date,
                "invoice_amount": invoice.invoice_amount,
                "system_decision": risk_result.decision,
                "risk_flags": risk_result.risk_flags,
            },
            history=history,
        )

        self._advance_stage(
            batch=batch, invoice=invoice, attempt=attempt, stage_code="finalization"
        )
        invoice.system_decision = duplicate_result.decision
        invoice.duplicate_flag = duplicate_result.duplicate_flag
        invoice.duplicate_group_key = duplicate_result.duplicate_group_key
        invoice.risk_flags = json.dumps(
            duplicate_result.risk_flags, ensure_ascii=False, sort_keys=True
        )
        invoice.processing_status = "completed"
        invoice.processing_stage = "completed"
        invoice.review_status = "not_reviewed"
        self._refresh_invoice_user_state(invoice)
        invoice.problem_count = self._compute_problem_count(
            risk_flags=duplicate_result.risk_flags,
            buyer_validation=buyer_validation,
        )

        evidence_record = evidence.to_record(invoice.id)
        evidence_record.attempt_id = attempt.id
        self.session.add(evidence_record)
        for candidate in evidence.field_candidates:
            self.session.add(
                ExtractedField(
                    invoice_id=invoice.id,
                    attempt_id=attempt.id,
                    field_name=candidate.field_name,
                    extracted_value=candidate.value,
                    normalized_value=candidate.normalized_value,
                    confidence=Decimal(str(candidate.confidence)).quantize(
                        Decimal("0.0001")
                    ),
                    page_no=candidate.page_no,
                    source_fragment=candidate.source_fragment,
                    bbox_json=json.dumps(candidate.bbox_json, ensure_ascii=False)
                    if candidate.bbox_json
                    else None,
                )
            )

        for check in buyer_validation.checks:
            self.session.add(
                FieldCheck(
                    invoice_id=invoice.id,
                    attempt_id=attempt.id,
                    field_name=check.field_name,
                    expected_value=check.expected_value,
                    actual_value=check.actual_value,
                    match_result=check.match_result,
                    reason=check.reason,
                )
            )

        if invoice.duplicate_flag and invoice.duplicate_group_key:
            self.session.add(
                FieldCheck(
                    invoice_id=invoice.id,
                    attempt_id=attempt.id,
                    field_name="duplicate_group_key",
                    expected_value=invoice.duplicate_group_key,
                    actual_value=invoice.duplicate_group_key,
                    match_result="matched",
                    reason="Matched an earlier invoice with the same duplicate fingerprint.",
                )
            )

        if invoice.system_decision == "suggested_pass" and not invoice.duplicate_flag:
            naming_result = build_renamed_filename(
                invoice_date=invoice.invoice_date,
                invoice_amount=invoice.invoice_amount,
                invoice_number=invoice.invoice_number,
                template=self._resolve_naming_template(snapshot),
            )
            if naming_result.renamed_filename:
                renamed_path = self._write_renamed_copy(
                    batch_no=batch.batch_no,
                    source_path=source_path,
                    target_name=naming_result.renamed_filename,
                )
                invoice.renamed_filename = renamed_path.name
                invoice.storage_path_renamed = self._relative_storage_path(renamed_path)
                invoice.artifact_status = "renamed"

        self.session.flush()
        return evidence

    def _mark_invoice_failed(
        self, *, invoice_id: str, attempt_id: str, job_id: str, reason: str
    ) -> None:
        invoice = self.session.get(InvoiceRecord, invoice_id)
        attempt = self.session.get(ProcessingAttempt, attempt_id)
        job = self.session.get(ProcessingJob, job_id)
        if invoice is None:
            return

        invoice.processing_status = "processing_failed"
        invoice.processing_stage = "failed"
        invoice.system_decision = None
        invoice.parse_source = None
        invoice.renamed_filename = None
        invoice.storage_path_renamed = None
        invoice.artifact_status = "original_only"
        invoice.duplicate_flag = False
        invoice.duplicate_group_key = None
        invoice.risk_flags = "[]"
        invoice.last_attempt_id = attempt_id
        invoice.last_error_stage = attempt.stage if attempt is not None else "failed"
        invoice.last_error_code = self._extract_error_code(reason)
        invoice.last_error_message = reason
        invoice.retryable = self._is_retryable_error(invoice.last_error_code)
        invoice.archive_status = "not_ready"
        self._refresh_invoice_user_state(invoice)
        invoice.problem_count = 1
        invoice.failure_reason = reason
        invoice.evidence_items.clear()
        invoice.extracted_fields.clear()
        invoice.field_checks.clear()
        if attempt is not None:
            attempt.status = "retryable_failed" if invoice.retryable else "failed"
            attempt.error_code = invoice.last_error_code
            attempt.error_message = reason
            attempt.retryable = invoice.retryable
            attempt.completed_at = datetime.now(UTC)
            attempt.diagnostic_json = json.dumps(
                {
                    "error_code": invoice.last_error_code,
                    "error_message": reason,
                    "stage": attempt.stage,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        if job is not None:
            job.current_stage = "failed"
            job.last_heartbeat_at = datetime.now(UTC)
        self.session.commit()

        log_event(
            self.logger,
            "invoice_processing_failed",
            invoice_id=invoice.id,
            original_filename=invoice.original_filename,
            reason=reason,
        )

    def _ensure_job(self, *, batch: Batch, total_items: int) -> ProcessingJob:
        existing_job = self._current_job(batch)
        if existing_job is not None and existing_job.status in {"queued", "running"}:
            return existing_job
        if existing_job is not None and existing_job.status in {
            "completed",
            "completed_with_failures",
        }:
            invoices = self.session.scalars(
                select(InvoiceRecord).where(InvoiceRecord.batch_id == batch.id)
            ).all()
            if invoices and all(
                invoice.processing_status in TERMINAL_INVOICE_STATUSES
                for invoice in invoices
            ):
                return existing_job

        job = ProcessingJob(
            batch_id=batch.id,
            status="running",
            current_stage="queued",
            total_items=total_items,
            completed_items=0,
            failed_items=0,
            started_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
            recovery_token=f"{batch.batch_no}-{datetime.now(UTC).timestamp()}",
        )
        self.session.add(job)
        self.session.flush()
        batch.active_job_id = job.id
        batch.status = "processing"
        batch.last_stage_code = "queued"
        batch.last_stage_text = STAGE_TEXTS["queued"]
        self.session.commit()
        self.session.refresh(job)
        self.session.refresh(batch)
        return job

    def _start_attempt(
        self, *, batch: Batch, invoice: InvoiceRecord, job: ProcessingJob
    ) -> ProcessingAttempt:
        attempt_no = (
            self.session.query(ProcessingAttempt)
            .where(ProcessingAttempt.invoice_id == invoice.id)
            .count()
            + 1
        )
        attempt = ProcessingAttempt(
            job_id=job.id,
            invoice_id=invoice.id,
            attempt_no=attempt_no,
            status="running",
            stage="queued",
            retryable=False,
            input_sha256=invoice.file_sha256,
            started_at=datetime.now(UTC),
        )
        self.session.add(attempt)
        self.session.flush()

        invoice.processing_status = "processing"
        invoice.processing_stage = "queued"
        invoice.failure_reason = None
        invoice.duplicate_flag = False
        invoice.duplicate_group_key = None
        invoice.renamed_filename = None
        invoice.storage_path_renamed = None
        invoice.artifact_status = "original_only"
        invoice.archive_status = "not_ready"
        invoice.last_attempt_id = attempt.id
        invoice.last_error_stage = None
        invoice.last_error_code = None
        invoice.last_error_message = None
        invoice.retryable = False
        invoice.retry_count = max(attempt_no - 1, 0)
        invoice.evidence_items.clear()
        invoice.extracted_fields.clear()
        invoice.field_checks.clear()
        self._refresh_invoice_user_state(invoice)

        batch.active_job_id = job.id
        batch.status = "processing"
        self.session.commit()
        self.session.refresh(attempt)
        self.session.refresh(invoice)
        self.session.refresh(batch)
        return attempt

    def _mark_attempt_succeeded(
        self,
        *,
        batch: Batch,
        invoice: InvoiceRecord,
        job: ProcessingJob,
        attempt: ProcessingAttempt,
    ) -> None:
        attempt.status = "succeeded"
        attempt.stage = "completed"
        attempt.retryable = False
        attempt.completed_at = datetime.now(UTC)
        job.last_heartbeat_at = datetime.now(UTC)
        self._refresh_job_counters(job=job)

    def _match_attachments_and_reclassify(
        self,
        *,
        batch: Batch,
        invoices: list[InvoiceRecord],
        snapshot: dict[str, Any],
        parsed_invoice_evidence: dict[str, UnifiedDocumentEvidence],
    ) -> None:
        attachments = self.session.scalars(
            select(AttachmentDocument)
            .where(AttachmentDocument.batch_id == batch.id)
            .order_by(AttachmentDocument.original_filename.asc())
        ).all()
        completed_invoices = [
            invoice for invoice in invoices if invoice.processing_status == "completed"
        ]
        invoice_by_id = {invoice.id: invoice for invoice in completed_invoices}
        attachment_by_id = {attachment.id: attachment for attachment in attachments}
        attachment_evidence: dict[str, UnifiedDocumentEvidence] = {}
        invoice_to_attachment_ids: dict[str, list[str]] = {}
        business_rules = self._snapshot_content(snapshot, "business_rules")
        tax_profile = self._snapshot_content(snapshot, "tax_profile")
        buyer_validation_cache: dict[str, BuyerValidationResult] = {}

        if attachments:
            self._advance_batch_stage(batch=batch, stage_code="attachment_matching")

            for attachment in attachments:
                attachment.matched_invoice_id = None
                source_path = self._resolve_storage_path(attachment.storage_path_original)
                try:
                    evidence = self._parse_document(source_path.read_bytes()).evidence
                except Exception as exc:
                    attachment.attachment_status = "parse_failed"
                    attachment.match_reason = str(exc)
                    continue

                attachment_evidence[attachment.id] = evidence
                matches = self._find_attachment_matches(
                    evidence=evidence, invoices=completed_invoices
                )
                if not matches:
                    attachment.attachment_status = "unmatched"
                    attachment.match_reason = (
                        "No same-batch invoice matched the attachment summary."
                    )
                    continue
                if len(matches) > 1:
                    attachment.attachment_status = "ambiguous"
                    attachment.match_reason = self._format_ambiguous_attachment_reason(
                        matches
                    )
                    continue

                invoice_id, reason = matches[0]
                attachment.attachment_status = "matched"
                attachment.matched_invoice_id = invoice_id
                attachment.match_reason = reason
                invoice_to_attachment_ids.setdefault(invoice_id, []).append(attachment.id)

            for invoice_id, attachment_ids in invoice_to_attachment_ids.items():
                invoice = invoice_by_id.get(invoice_id)
                current_attachment_evidence = self._merge_attachment_evidence(
                    [
                        attachment_evidence[attachment_id]
                        for attachment_id in attachment_ids
                        if attachment_id in attachment_evidence
                    ]
                )
                if (
                    invoice is None
                    or current_attachment_evidence is None
                    or invoice.processing_status != "completed"
                    or invoice.system_decision != "review_required"
                ):
                    continue

                main_evidence = parsed_invoice_evidence.get(
                    invoice_id
                ) or self._parse_invoice_evidence(invoice)
                parsed_invoice_evidence.setdefault(invoice_id, main_evidence)
                buyer_validation = buyer_validation_cache.get(invoice_id)
                if buyer_validation is None:
                    buyer_validation = validate_buyer_fields(
                        evidence=main_evidence,
                        tax_profile=tax_profile,
                    )
                    buyer_validation_cache[invoice_id] = buyer_validation
                risk_result = classify_risk(
                    evidence=main_evidence,
                    attachment_evidence=current_attachment_evidence,
                    business_rules=business_rules,
                    buyer_validation=buyer_validation,
                )
                current_risk_flags = json.loads(invoice.risk_flags or "[]")
                if (
                    risk_result.decision == invoice.system_decision
                    and risk_result.risk_flags == current_risk_flags
                ):
                    continue

                duplicate_result = detect_suspected_duplicate(
                    invoice_data={
                        "invoice_number": invoice.invoice_number,
                        "invoice_code": invoice.invoice_code,
                        "seller_name": invoice.seller_name,
                        "invoice_date": invoice.invoice_date,
                        "invoice_amount": invoice.invoice_amount,
                        "system_decision": risk_result.decision,
                        "risk_flags": risk_result.risk_flags,
                    },
                    history=self._build_history_excluding_invoice(
                        invoices=invoices, invoice_id=invoice.id
                    ),
                )

                invoice.system_decision = duplicate_result.decision
                invoice.duplicate_flag = duplicate_result.duplicate_flag
                invoice.duplicate_group_key = duplicate_result.duplicate_group_key
                invoice.risk_flags = json.dumps(
                    duplicate_result.risk_flags, ensure_ascii=False, sort_keys=True
                )
                self._refresh_invoice_user_state(invoice)
                invoice.problem_count = self._compute_problem_count(
                    risk_flags=duplicate_result.risk_flags,
                    buyer_validation=buyer_validation,
                )
                for attachment_id in attachment_ids:
                    attachment = attachment_by_id[attachment_id]
                    attachment.attachment_status = "consumed"
                    attachment.match_reason = (
                        f"{attachment.match_reason}; reclassified the invoice using "
                        "attachment line items."
                    )

        for invoice in completed_invoices:
            if invoice.processing_status != "completed":
                continue
            main_evidence = parsed_invoice_evidence.get(
                invoice.id
            ) or self._parse_invoice_evidence(invoice)
            parsed_invoice_evidence.setdefault(invoice.id, main_evidence)
            if not self._invoice_requires_attachment_evidence(
                evidence=main_evidence,
                business_rules=business_rules,
            ):
                continue
            if invoice.system_decision != "review_required":
                continue

            attachment_review_flags = self._attachment_review_flags_for_invoice(
                invoice_id=invoice.id,
                attachments=attachments,
                invoice_to_attachment_ids=invoice_to_attachment_ids,
                attachment_evidence=attachment_evidence,
                attachment_by_id=attachment_by_id,
                business_rules=business_rules,
            )
            if not attachment_review_flags:
                continue

            buyer_validation = buyer_validation_cache.get(invoice.id)
            if buyer_validation is None:
                buyer_validation = validate_buyer_fields(
                    evidence=main_evidence,
                    tax_profile=tax_profile,
                )
                buyer_validation_cache[invoice.id] = buyer_validation
            self._merge_invoice_risk_flags(
                invoice=invoice,
                buyer_validation=buyer_validation,
                extra_risk_flags=attachment_review_flags,
            )

        self.session.flush()

    def _merge_attachment_evidence(
        self, evidences: list[UnifiedDocumentEvidence]
    ) -> UnifiedDocumentEvidence | None:
        if not evidences:
            return None
        if len(evidences) == 1:
            return evidences[0]

        merged = evidences[0].model_copy(deep=True)
        merged.raw_text = "\n".join(
            raw_text.strip()
            for raw_text in (evidence.raw_text or "" for evidence in evidences)
            if raw_text.strip()
        )
        merged.pages = [
            dict(page)
            for evidence in evidences
            for page in evidence.pages
        ]
        merged.text_blocks = [
            block.model_copy(deep=True)
            for evidence in evidences
            for block in evidence.text_blocks
        ]
        merged.table_lines = [
            dict(line)
            for evidence in evidences
            for line in evidence.table_lines
        ]
        merged.field_candidates = [
            candidate.model_copy(deep=True)
            for evidence in evidences
            for candidate in evidence.field_candidates
        ]
        merged.confidence_summary.overall = min(
            evidence.confidence_summary.overall for evidence in evidences
        )
        merged.confidence_summary.fields = {
            field_name: max(
                candidate.confidence
                for evidence in evidences
                for candidate in evidence.field_candidates
                if candidate.field_name == field_name
            )
            for field_name in {
                candidate.field_name
                for evidence in evidences
                for candidate in evidence.field_candidates
            }
        }
        merged.confidence_summary.flags = list(
            dict.fromkeys(
                flag
                for evidence in evidences
                for flag in evidence.confidence_summary.flags
            )
        )
        if any(evidence.source_type == "ocr" for evidence in evidences):
            merged.source_type = "ocr"
        provider_names = {evidence.provider_name for evidence in evidences}
        if len(provider_names) > 1:
            merged.provider_name = "aggregated"
        provider_versions = {evidence.provider_version for evidence in evidences}
        if len(provider_versions) > 1:
            merged.provider_version = "multiple"
        return merged

    def _attachment_review_flags_for_invoice(
        self,
        *,
        invoice_id: str,
        attachments: list[AttachmentDocument],
        invoice_to_attachment_ids: dict[str, list[str]],
        attachment_evidence: dict[str, UnifiedDocumentEvidence],
        attachment_by_id: dict[str, AttachmentDocument],
        business_rules: dict[str, Any],
    ) -> list[str]:
        attachment_ids = invoice_to_attachment_ids.get(invoice_id, [])
        if not attachment_ids:
            if not attachments:
                return ["attachment_missing"]
            if any(
                attachment.attachment_status == "parse_failed"
                for attachment in attachments
            ):
                return ["attachment_parse_failed"]
            if any(
                attachment.attachment_status in {"unmatched", "ambiguous"}
                for attachment in attachments
            ):
                return ["attachment_unmatched"]
            return ["attachment_missing"]

        merged_attachment_evidence = self._merge_attachment_evidence(
            [
                attachment_evidence[attachment_id]
                for attachment_id in attachment_ids
                if attachment_id in attachment_evidence
            ]
        )
        if merged_attachment_evidence is None:
            if any(
                attachment_by_id[attachment_id].attachment_status == "parse_failed"
                for attachment_id in attachment_ids
                if attachment_id in attachment_by_id
            ):
                return ["attachment_parse_failed"]
            return ["attachment_missing"]

        minimum_confidence = float(business_rules.get("minimum_confidence", 0.75))
        if merged_attachment_evidence.confidence_summary.overall < minimum_confidence:
            return ["attachment_low_confidence"]
        if any(
            flag in {"low_confidence", "ocr_low_confidence"}
            for flag in merged_attachment_evidence.confidence_summary.flags
        ):
            return ["attachment_low_confidence"]
        return []

    def _invoice_requires_attachment_evidence(
        self,
        *,
        evidence: UnifiedDocumentEvidence,
        business_rules: dict[str, Any],
    ) -> bool:
        review_keywords = {
            self._normalize_rule_text(str(keyword))
            for keyword in business_rules.get("review_keywords", [])
            if str(keyword).strip()
        }
        if not review_keywords:
            review_keywords = {"详见清单", "详见销货清单", "混合票", "混合项目"}

        line_texts = [
            self._normalize_rule_text(str(line.get("text") or ""))
            for line in evidence.table_lines
        ]
        return any(
            keyword and keyword in line_text
            for keyword in review_keywords
            for line_text in line_texts
        )

    def _merge_invoice_risk_flags(
        self,
        *,
        invoice: InvoiceRecord,
        buyer_validation: BuyerValidationResult,
        extra_risk_flags: list[str],
    ) -> None:
        current_risk_flags = json.loads(invoice.risk_flags or "[]")
        merged_risk_flags = list(
            dict.fromkeys([*current_risk_flags, *extra_risk_flags])
        )
        if merged_risk_flags == current_risk_flags:
            return

        invoice.risk_flags = json.dumps(
            merged_risk_flags, ensure_ascii=False, sort_keys=True
        )
        self._refresh_invoice_user_state(invoice)
        invoice.problem_count = self._compute_problem_count(
            risk_flags=merged_risk_flags,
            buyer_validation=buyer_validation,
        )

    def _find_attachment_matches(
        self,
        *,
        evidence: UnifiedDocumentEvidence,
        invoices: list[InvoiceRecord],
    ) -> list[tuple[str, str]]:
        matches: list[tuple[str, str]] = []
        attachment_invoice_number = self._candidate_value(evidence, "invoice_number")
        attachment_invoice_code = self._candidate_value(evidence, "invoice_code")
        attachment_seller_name = self._candidate_value(evidence, "seller_name")
        attachment_invoice_amount = self._candidate_amount(evidence, "invoice_amount")

        for invoice in invoices:
            matched_keys: list[str] = []

            if attachment_invoice_number and invoice.invoice_number:
                if attachment_invoice_number != invoice.invoice_number:
                    continue
                matched_keys.append("invoice_number")

            if attachment_invoice_code and invoice.invoice_code:
                if attachment_invoice_code != invoice.invoice_code:
                    continue
                matched_keys.append("invoice_code")

            if attachment_seller_name and invoice.seller_name:
                if attachment_seller_name != invoice.seller_name:
                    continue
                matched_keys.append("seller_name")

            if (
                attachment_invoice_amount is not None
                and invoice.invoice_amount is not None
            ):
                if attachment_invoice_amount != invoice.invoice_amount:
                    continue
                matched_keys.append("invoice_amount")

            if not matched_keys:
                continue

            matches.append(
                (invoice.id, self._format_attachment_match_reason(matched_keys))
            )

        return matches

    @staticmethod
    def _format_attachment_match_reason(matched_keys: list[str]) -> str:
        joined = ", ".join(matched_keys)
        return f"Matched attachment to invoice using {joined}."

    def _format_ambiguous_attachment_reason(
        self, matches: list[tuple[str, str]]
    ) -> str:
        invoice_ids = ", ".join(match[0] for match in matches)
        return f"Multiple invoices matched the attachment summary: {invoice_ids}."

    def _parse_invoice_evidence(
        self, invoice: InvoiceRecord
    ) -> UnifiedDocumentEvidence:
        source_path = self._resolve_storage_path(invoice.storage_path_original)
        return self._parse_document(source_path.read_bytes()).evidence

    @staticmethod
    def _build_history_excluding_invoice(
        *,
        invoices: list[InvoiceRecord],
        invoice_id: str,
    ) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for invoice in invoices:
            if invoice.id == invoice_id or invoice.processing_status != "completed":
                continue
            history.append(
                {
                    "invoice_number": invoice.invoice_number,
                    "invoice_code": invoice.invoice_code,
                    "seller_name": invoice.seller_name,
                    "invoice_date": invoice.invoice_date,
                    "invoice_amount": invoice.invoice_amount,
                    "system_decision": invoice.system_decision,
                    "risk_flags": json.loads(invoice.risk_flags or "[]"),
                }
            )
        return history

    def _advance_batch_stage(self, *, batch: Batch, stage_code: str) -> None:
        batch.last_stage_code = stage_code
        batch.last_stage_text = STAGE_TEXTS.get(stage_code, stage_code)
        current_job = self._current_job(batch)
        if current_job is not None:
            current_job.status = "running"
            current_job.current_stage = stage_code
            current_job.last_heartbeat_at = datetime.now(UTC)
        self.session.flush()

    def _advance_stage(
        self,
        *,
        batch: Batch,
        invoice: InvoiceRecord,
        attempt: ProcessingAttempt,
        stage_code: str,
    ) -> None:
        attempt.stage = stage_code
        invoice.processing_status = "processing"
        invoice.processing_stage = stage_code
        self._advance_batch_stage(batch=batch, stage_code=stage_code)
        self.session.flush()

    def _refresh_job_counters(self, *, job: ProcessingJob) -> None:
        attempts = self.session.scalars(
            select(ProcessingAttempt).where(ProcessingAttempt.job_id == job.id)
        ).all()
        job.total_items = len(attempts) or job.total_items
        job.completed_items = sum(
            1 for attempt in attempts if attempt.status == "succeeded"
        )
        job.failed_items = sum(
            1
            for attempt in attempts
            if attempt.status in {"failed", "retryable_failed"}
        )

    def _finalize_job(self, *, batch_id: str, job_id: str) -> None:
        batch = self.session.get(Batch, batch_id)
        job = self.session.get(ProcessingJob, job_id)
        if batch is None or job is None:
            return
        invoices = self.session.scalars(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch_id)
        ).all()
        pass_summary = summarize_suggested_pass(invoices)
        review_queue_service = ReviewQueueService(self.session)
        for invoice in invoices:
            review_queue_service.sync_invoice(invoice)
        self._refresh_job_counters(job=job)
        job.current_stage = "completed" if job.failed_items == 0 else "failed"
        job.status = "completed" if job.failed_items == 0 else "completed_with_failures"
        job.completed_at = datetime.now(UTC)
        job.last_heartbeat_at = datetime.now(UTC)
        batch.last_stage_code = "completed" if job.failed_items == 0 else "failed"
        batch.last_stage_text = STAGE_TEXTS[batch.last_stage_code]
        batch.total_files = len(invoices)
        batch.completed_files = sum(
            1 for invoice in invoices if invoice.processing_status == "completed"
        )
        batch.failed_files = sum(
            1
            for invoice in invoices
            if invoice.processing_status == "processing_failed"
        )
        batch.processing_files = max(
            batch.total_files - batch.completed_files - batch.failed_files, 0
        )
        batch.suggested_pass_count = pass_summary.count
        batch.suggested_pass_total_amount = pass_summary.total_amount
        batch.status = (
            "completed"
            if batch.failed_files == 0
            else "processing"
            if batch.processing_files
            else "completed"
        )
        self.session.commit()

    def _refresh_invoice_user_state(self, invoice: InvoiceRecord) -> None:
        invoice.archive_status = derive_archive_status(
            processing_status=invoice.processing_status,
            system_decision=invoice.system_decision,
            duplicate_flag=invoice.duplicate_flag,
            review_status=invoice.review_status,
            archive_status=invoice.archive_status,
            artifact_status=invoice.artifact_status,
        )
        invoice.display_status = derive_display_status(
            processing_status=invoice.processing_status,
            system_decision=invoice.system_decision,
            duplicate_flag=invoice.duplicate_flag,
            review_status=invoice.review_status,
        )
        ReviewQueueService(self.session).sync_invoice(invoice)

    @staticmethod
    def _current_job(batch: Batch) -> ProcessingJob | None:
        for job in batch.processing_jobs:
            if job.id == batch.active_job_id:
                return job
        return None

    @staticmethod
    def _build_history_from_completed_invoices(
        invoices: list[InvoiceRecord],
    ) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for invoice in invoices:
            if invoice.processing_status != "completed":
                continue
            history.append(
                {
                    "invoice_number": invoice.invoice_number,
                    "invoice_code": invoice.invoice_code,
                    "seller_name": invoice.seller_name,
                    "invoice_date": invoice.invoice_date,
                    "invoice_amount": invoice.invoice_amount,
                    "system_decision": invoice.system_decision,
                    "risk_flags": json.loads(invoice.risk_flags or "[]"),
                }
            )
        return history

    @staticmethod
    def _extract_error_code(reason: str) -> str:
        match = re.search(r"([a-z_]+)", reason)
        if match is None:
            return "processing_error"
        return match.group(1)

    @staticmethod
    def _is_retryable_error(error_code: str | None) -> bool:
        if error_code is None:
            return False
        return error_code in RETRYABLE_ERROR_CODES

    def _parse_document(self, content: bytes) -> ParsedDocument:
        text_error: StructuredParseError | None = None
        text_extraction: ProviderExtractionPayload | None = None
        metadata: dict[str, Any] = {}

        try:
            text_extraction = extract_pdf_text(content)
            metadata = self._extract_fixture_metadata(text_extraction.raw_text)
            parse_mode = str(metadata.get("parse_mode") or "text").strip().lower()

            if metadata and parse_mode != "ocr":
                return ParsedDocument(
                    evidence=self._build_fixture_evidence(
                        metadata, extraction=text_extraction
                    ),
                    metadata=metadata,
                )

            if parse_mode != "ocr":
                generic_evidence = self._try_build_generic_evidence(text_extraction)
                if generic_evidence is not None:
                    return ParsedDocument(evidence=generic_evidence, metadata={})
        except EvidenceAdapterError as exc:
            text_error = exc.error

        try:
            ocr_extraction = extract_local_ocr(content)
        except EvidenceAdapterError as exc:
            raise ValueError(self._format_parse_failure(exc.error, text_error)) from exc

        ocr_metadata = metadata or self._extract_fixture_metadata(
            ocr_extraction.raw_text
        )
        if ocr_metadata:
            return ParsedDocument(
                evidence=self._build_fixture_evidence(
                    ocr_metadata, extraction=ocr_extraction
                ),
                metadata=ocr_metadata,
            )

        generic_evidence = self._try_build_generic_evidence(ocr_extraction)
        if generic_evidence is not None:
            return ParsedDocument(evidence=generic_evidence, metadata={})

        raise ValueError(
            "ocr_no_invoice_fields: Local OCR did not produce recognizable invoice fields."
        )

    @staticmethod
    def _extract_fixture_metadata(raw_text: str) -> dict[str, Any]:
        pattern = re.compile(
            rf"{FIXTURE_START_MARKER}\s*(.*?)\s*{FIXTURE_END_MARKER}",
            re.DOTALL,
        )
        match = pattern.search(raw_text)
        if not match:
            return {}

        metadata: dict[str, Any] = {}
        for line in match.group(1).splitlines():
            stripped = line.strip()
            if not stripped or stripped == "T*":
                continue
            text_match = re.search(r"\((.*?)\)\s*Tj$", stripped)
            if text_match:
                stripped = text_match.group(1).strip()
            if not stripped or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            existing = metadata.get(key)
            if existing is None:
                metadata[key] = value
            elif isinstance(existing, list):
                existing.append(value)
            else:
                metadata[key] = [existing, value]
        return metadata

    def _build_fixture_evidence(
        self,
        metadata: dict[str, Any],
        *,
        extraction: ProviderExtractionPayload,
    ) -> UnifiedDocumentEvidence:
        overall_confidence = self._coerce_float(
            metadata.get("overall_confidence"),
            default=extraction.base_confidence,
        )
        confidence_flags = list(
            dict.fromkeys(
                [
                    *self._coerce_list(metadata.get("confidence_flag")),
                    *extraction.confidence_flags,
                ]
            )
        )
        line_texts = self._coerce_list(metadata.get("line_text"))

        field_candidates: list[dict[str, Any]] = []
        confidence_fields: dict[str, float] = {}
        raw_lines = []
        for field_name in (
            "invoice_code",
            "invoice_number",
            "seller_name",
            "buyer_name",
            "buyer_tax_no",
            "invoice_date",
            "invoice_amount",
        ):
            value = metadata.get(field_name)
            if value in (None, ""):
                continue
            confidence = self._coerce_float(
                metadata.get(f"{field_name}_confidence"), default=overall_confidence
            )
            confidence_fields[field_name] = confidence
            raw_lines.append(f"{field_name}: {value}")
            field_candidates.append(
                {
                    "field_name": field_name,
                    "value": str(value),
                    "confidence": confidence,
                    "page_no": 1,
                    "source_fragment": f"{field_name}: {value}",
                }
            )

        for line_text in line_texts:
            raw_lines.append(f"line_text: {line_text}")

        table_lines = extraction.table_lines
        if line_texts:
            table_lines = [
                {
                    "row_no": index,
                    "text": line_text,
                    "mixed_invoice": self._coerce_bool(metadata.get("mixed_invoice")),
                }
                for index, line_text in enumerate(line_texts, start=1)
            ]

        raw_text = extraction.raw_text.strip() or "\n".join(raw_lines).strip()
        text_blocks = extraction.text_blocks or (
            [{"page_no": 1, "text": raw_text}] if raw_text else []
        )
        payload = {
            "provider_name": extraction.provider_name,
            "provider_version": extraction.provider_version,
            "provider_error_code": extraction.provider_error_code,
            "raw_text": raw_text,
            "pages": extraction.pages or [{"page_no": 1}],
            "text_blocks": text_blocks,
            "table_lines": table_lines,
            "field_candidates": field_candidates,
            "confidence_summary": {
                "overall": overall_confidence,
                "fields": confidence_fields,
                "flags": confidence_flags,
            },
        }
        if extraction.source_type == "ocr":
            return adapt_ocr_output(payload)
        return adapt_text_extraction(payload)

    def _build_generic_evidence(
        self, extraction: ProviderExtractionPayload
    ) -> UnifiedDocumentEvidence:
        normalized_text = "\n".join(
            line.strip() for line in extraction.raw_text.splitlines() if line.strip()
        )
        if not normalized_text:
            raise ValueError("No usable text extracted from document.")

        field_candidates: list[dict[str, Any]] = []
        confidence_fields: dict[str, float] = {}
        for field_name, pattern in GENERIC_FIELD_PATTERNS.items():
            match = pattern.search(normalized_text)
            if not match:
                continue
            value = match.group(1).strip()
            normalized_value = self._normalize_candidate_value(field_name, value)
            field_candidates.append(
                {
                    "field_name": field_name,
                    "value": value,
                    "normalized_value": normalized_value,
                    "confidence": extraction.base_confidence,
                    "page_no": 1,
                    "source_fragment": match.group(0).strip(),
                }
            )
            confidence_fields[field_name] = extraction.base_confidence

        self._append_e_invoice_sequence_candidates(
            normalized_text=normalized_text,
            field_candidates=field_candidates,
            confidence_fields=confidence_fields,
            confidence=extraction.base_confidence,
        )

        if not field_candidates:
            raise ValueError("Unable to extract invoice fields from document text.")

        confidence_flags = list(dict.fromkeys(extraction.confidence_flags))
        if (
            extraction.base_confidence < 0.75
            and "low_confidence" not in confidence_flags
        ):
            confidence_flags.append("low_confidence")

        payload = {
            "provider_name": extraction.provider_name,
            "provider_version": extraction.provider_version,
            "provider_error_code": extraction.provider_error_code,
            "raw_text": normalized_text,
            "pages": extraction.pages or [{"page_no": 1}],
            "text_blocks": extraction.text_blocks
            or [{"page_no": 1, "text": normalized_text}],
            "table_lines": extraction.table_lines
            or [
                {"row_no": index, "text": line}
                for index, line in enumerate(normalized_text.splitlines(), start=1)
            ],
            "field_candidates": field_candidates,
            "confidence_summary": {
                "overall": extraction.base_confidence,
                "fields": confidence_fields,
                "flags": confidence_flags,
            },
        }
        if extraction.source_type == "ocr":
            return adapt_ocr_output(payload)
        return adapt_text_extraction(payload)

    def _append_e_invoice_sequence_candidates(
        self,
        *,
        normalized_text: str,
        field_candidates: list[dict[str, Any]],
        confidence_fields: dict[str, float],
        confidence: float,
    ) -> None:
        existing_fields = {
            str(candidate.get("field_name") or "") for candidate in field_candidates
        }

        sequence_match = re.search(
            (
                "(?P<invoice_number>[0-9]{16,24})\\s+"
                "(?P<invoice_date>[0-9]{4}\\s*\\u5e74\\s*[0-9]{1,2}\\s*\\u6708\\s*[0-9]{1,2}\\s*\\u65e5)\\s+"
                "(?P<buyer_name>[\\u4e00-\\u9fffA-Za-z0-9\\uff08\\uff09()\\u00b7]+?(?:\\u516c\\u53f8|\\u5355\\u4f4d|\\u4e2d\\u5fc3|\\u5382|\\u5e97))\\s+"
                "(?P<buyer_tax_no>[0-9A-Z]{15,20})\\s+"
                "(?P<seller_name>[\\u4e00-\\u9fffA-Za-z0-9\\uff08\\uff09()\\u00b7]+?(?:\\u516c\\u53f8|\\u5355\\u4f4d|\\u4e2d\\u5fc3|\\u5382|\\u5e97))\\s+"
                "(?P<seller_tax_no>[0-9A-Z]{15,20})"
            ),
            normalized_text,
            re.IGNORECASE,
        )
        if sequence_match:
            for field_name in (
                "invoice_number",
                "invoice_date",
                "buyer_name",
                "buyer_tax_no",
                "seller_name",
            ):
                if field_name in existing_fields:
                    continue
                value = sequence_match.group(field_name).strip()
                self._append_generic_candidate(
                    field_candidates=field_candidates,
                    confidence_fields=confidence_fields,
                    field_name=field_name,
                    value=value,
                    confidence=confidence,
                    source_fragment=sequence_match.group(0).strip(),
                )
                existing_fields.add(field_name)

        if "invoice_amount" not in existing_fields:
            amount_candidate = self._find_total_amount_candidate(normalized_text)
            if amount_candidate is not None:
                amount_value, amount_fragment = amount_candidate
                self._append_generic_candidate(
                    field_candidates=field_candidates,
                    confidence_fields=confidence_fields,
                    field_name="invoice_amount",
                    value=amount_value,
                    confidence=confidence,
                    source_fragment=amount_fragment,
                )

    @staticmethod
    def _find_total_amount_candidate(normalized_text: str) -> tuple[str, str] | None:
        anchor_match = re.search(
            "(?:\\u4ef7\\u7a0e\\u5408\\u8ba1|\\u5c0f\\s*\\u5199|Amount)",
            normalized_text,
            re.IGNORECASE,
        )
        if anchor_match is None:
            return None

        window = normalized_text[anchor_match.start() : anchor_match.start() + 700]
        money_matches = list(
            re.finditer(
                "([\\u00a5\\uffe5]\\s*([0-9]{1,12}(?:\\.[0-9]{1,2})?)(?![0-9]))",
                window,
                re.IGNORECASE,
            )
        )
        if not money_matches:
            return None

        candidates: list[tuple[Decimal, str, str]] = []
        for match in money_matches:
            value = match.group(2).strip()
            try:
                amount = Decimal(value)
            except InvalidOperation:
                continue
            if amount <= 0:
                continue
            candidates.append((amount, value, match.group(1).strip()))

        if not candidates:
            return None
        _, value, fragment = max(candidates, key=lambda item: item[0])
        return value, fragment

    def _append_generic_candidate(
        self,
        *,
        field_candidates: list[dict[str, Any]],
        confidence_fields: dict[str, float],
        field_name: str,
        value: str,
        confidence: float,
        source_fragment: str,
    ) -> None:
        field_candidates.append(
            {
                "field_name": field_name,
                "value": value,
                "normalized_value": self._normalize_candidate_value(field_name, value),
                "confidence": confidence,
                "page_no": 1,
                "source_fragment": source_fragment,
            }
        )
        confidence_fields[field_name] = confidence

    def _try_build_generic_evidence(
        self, extraction: ProviderExtractionPayload
    ) -> UnifiedDocumentEvidence | None:
        try:
            return self._build_generic_evidence(extraction)
        except (EvidenceAdapterError, ValueError):
            return None

    @staticmethod
    def _format_parse_failure(
        error: StructuredParseError, text_error: StructuredParseError | None = None
    ) -> str:
        message = f"{error.code}: {error.message}"
        if text_error is not None:
            message = f"{message} (text provider error: {text_error.code})"
        return message

    @staticmethod
    def _candidate_value(
        evidence: UnifiedDocumentEvidence, field_name: str
    ) -> str | None:
        candidate = evidence.best_candidate(field_name)
        if candidate is None:
            return None
        value = (candidate.normalized_value or candidate.value).strip()
        return value or None

    def _candidate_date(
        self, evidence: UnifiedDocumentEvidence, field_name: str
    ) -> date | None:
        value = self._candidate_value(evidence, field_name)
        if not value:
            return None
        normalized = (
            value.replace("年", "-")
            .replace("月", "-")
            .replace("日", "")
            .replace("/", "-")
        )
        normalized = re.sub(r"\s+", "", normalized)
        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            return None

    @staticmethod
    def _candidate_amount(
        evidence: UnifiedDocumentEvidence, field_name: str
    ) -> Decimal | None:
        candidate = evidence.best_candidate(field_name)
        if candidate is None or not candidate.value.strip():
            return None
        raw_value = candidate.normalized_value or candidate.value
        try:
            return Decimal(raw_value.strip()).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    @staticmethod
    def _normalize_candidate_value(field_name: str, value: str) -> str:
        stripped = value.strip()
        if field_name in {"buyer_tax_no", "invoice_number", "invoice_code"}:
            return "".join(stripped.split()).upper()
        if field_name in {"buyer_name", "seller_name"}:
            return "".join(stripped.split())
        if field_name == "invoice_date":
            return (
                stripped.replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .replace("/", "-")
            )
        if field_name == "invoice_amount":
            match = re.search(r"[0-9]+(?:\.[0-9]{1,2})?", stripped)
            return match.group(0) if match else stripped
        return stripped

    @staticmethod
    def _compute_problem_count(
        *, risk_flags: list[str], buyer_validation: BuyerValidationResult
    ) -> int:
        count = len(risk_flags)
        count += sum(
            1 for check in buyer_validation.checks if check.match_result != "matched"
        )
        return count

    def _resolve_naming_template(self, snapshot: dict[str, Any]) -> str:
        naming_rules = self._snapshot_content(snapshot, "naming_rules")
        raw_pattern = str(naming_rules.get("pattern") or "").strip()
        if not raw_pattern:
            return DEFAULT_NAMING_TEMPLATE

        template = raw_pattern
        for source, target in SUPPORTED_NAMING_KEYS.items():
            template = template.replace(source, target)

        if (
            "{invoice_number}" not in template
            or "{amount}" not in template
            or "{date}" not in template
        ):
            return DEFAULT_NAMING_TEMPLATE
        if not template.endswith(".pdf"):
            template = f"{template}.pdf"
        return template

    def _write_renamed_copy(
        self, *, batch_no: str, source_path: Path, target_name: str
    ) -> Path:
        renamed_dir = self.storage_root / "renamed" / batch_no
        renamed_dir.mkdir(parents=True, exist_ok=True)

        target_path = renamed_dir / target_name
        if not target_path.exists():
            target_path.write_bytes(source_path.read_bytes())
            return target_path

        stem = target_path.stem
        suffix = target_path.suffix
        counter = 2
        while True:
            candidate = renamed_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                candidate.write_bytes(source_path.read_bytes())
                return candidate
            counter += 1

    def _resolve_storage_path(self, relative_or_absolute_path: str) -> Path:
        candidate = Path(relative_or_absolute_path)
        if candidate.is_absolute():
            return candidate
        return (self.storage_root.parent / candidate).resolve()

    def _relative_storage_path(self, absolute_path: Path) -> str:
        return absolute_path.relative_to(self.storage_root.parent).as_posix()

    @staticmethod
    def _load_snapshot(snapshot_json: str) -> dict[str, Any]:
        if not snapshot_json:
            return {}
        try:
            payload = json.loads(snapshot_json)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _snapshot_content(snapshot: dict[str, Any], kind: str) -> dict[str, Any]:
        version = snapshot.get(kind)
        if not isinstance(version, dict):
            return {}
        content = version.get("content")
        return content if isinstance(content, dict) else {}

    @staticmethod
    def _coerce_float(raw_value: Any, *, default: float) -> float:
        if raw_value in (None, ""):
            return default
        try:
            return float(str(raw_value).strip())
        except ValueError:
            return default

    @staticmethod
    def _coerce_list(raw_value: Any) -> list[str]:
        if raw_value in (None, ""):
            return []
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        text = str(raw_value).strip()
        if not text:
            return []
        return [segment.strip() for segment in text.split("|") if segment.strip()]

    @staticmethod
    def _coerce_bool(raw_value: Any) -> bool:
        return str(raw_value or "").strip().lower() in {"1", "true", "yes", "y"}

    @staticmethod
    def _normalize_rule_text(value: str) -> str:
        return "".join(value.split()).strip()
