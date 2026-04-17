from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from logging import Logger
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_app_logger, log_event
from backend.app.db.models import Batch, ExtractedField, FieldCheck, InvoiceRecord
from backend.app.services.naming_service import DEFAULT_NAMING_TEMPLATE, build_renamed_filename
from backend.app.services.parsing.evidence_models import UnifiedDocumentEvidence
from backend.app.services.parsing.providers import adapt_ocr_output, adapt_text_extraction
from backend.app.services.rules.buyer_validation import BuyerValidationResult, validate_buyer_fields
from backend.app.services.rules.duplicate_detector import detect_suspected_duplicate
from backend.app.services.rules.risk_classifier import classify_risk
from backend.app.services.status_service import derive_display_status


FIXTURE_START_MARKER = "INVOICE_ASSISTANT_FIXTURE_START"
FIXTURE_END_MARKER = "INVOICE_ASSISTANT_FIXTURE_END"
GENERIC_FIELD_PATTERNS = {
    "invoice_number": re.compile(r"(?:Invoice(?:\s+No|\s+Number)?|发票号码)[:：]?\s*([A-Z0-9-]+)", re.IGNORECASE),
    "invoice_code": re.compile(r"(?:Invoice\s+Code|发票代码)[:：]?\s*([A-Z0-9-]+)", re.IGNORECASE),
    "seller_name": re.compile(r"(?:Seller|销方名称)[:：]?\s*([^\r\n]+)", re.IGNORECASE),
    "buyer_name": re.compile(r"(?:Buyer|购方名称)[:：]?\s*([^\r\n]+)", re.IGNORECASE),
    "buyer_tax_no": re.compile(r"(?:Buyer\s+Tax(?:\s+No)?|购方税号)[:：]?\s*([A-Z0-9]+)", re.IGNORECASE),
    "invoice_date": re.compile(r"(?:Invoice\s+Date|Date|开票日期)[:：]?\s*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2})", re.IGNORECASE),
    "invoice_amount": re.compile(r"(?:Amount|价税合计|金额)[:：]?\s*([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE),
}
SUPPORTED_NAMING_KEYS = {
    "{date}": "{date}",
    "{amount}": "{amount}",
    "{invoice_number}": "{invoice_number}",
    "{number}": "{invoice_number}",
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
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch_id).order_by(InvoiceRecord.original_filename.asc())
        ).all()

        history: list[dict[str, Any]] = []
        for invoice in invoices:
            try:
                self._process_invoice(batch=batch, invoice=invoice, snapshot=snapshot, history=history)
                self.session.commit()
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
                self._mark_invoice_failed(invoice_id=invoice.id, reason=str(exc))

        self.session.refresh(batch)
        return batch

    def _process_invoice(
        self,
        *,
        batch: Batch,
        invoice: InvoiceRecord,
        snapshot: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> None:
        invoice.processing_status = "extracting"
        invoice.failure_reason = None
        invoice.duplicate_flag = False
        invoice.duplicate_group_key = None
        invoice.renamed_filename = None
        invoice.storage_path_renamed = None
        invoice.artifact_status = "original_only"
        invoice.evidence_items.clear()
        invoice.extracted_fields.clear()
        invoice.field_checks.clear()

        source_path = self._resolve_storage_path(invoice.storage_path_original)
        parsed = self._parse_document(source_path.read_bytes())
        evidence = parsed.evidence

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

        invoice.system_decision = duplicate_result.decision
        invoice.duplicate_flag = duplicate_result.duplicate_flag
        invoice.duplicate_group_key = duplicate_result.duplicate_group_key
        invoice.risk_flags = json.dumps(duplicate_result.risk_flags, ensure_ascii=False, sort_keys=True)
        invoice.processing_status = "completed"
        invoice.review_status = "not_reviewed"
        invoice.display_status = derive_display_status(
            processing_status=invoice.processing_status,
            system_decision=invoice.system_decision,
            duplicate_flag=invoice.duplicate_flag,
        )
        invoice.problem_count = self._compute_problem_count(
            risk_flags=duplicate_result.risk_flags,
            buyer_validation=buyer_validation,
        )

        self.session.add(evidence.to_record(invoice.id))
        for candidate in evidence.field_candidates:
            self.session.add(
                ExtractedField(
                    invoice_id=invoice.id,
                    field_name=candidate.field_name,
                    extracted_value=candidate.value,
                    normalized_value=candidate.normalized_value,
                    confidence=Decimal(str(candidate.confidence)).quantize(Decimal("0.0001")),
                    page_no=candidate.page_no,
                    source_fragment=candidate.source_fragment,
                    bbox_json=json.dumps(candidate.bbox_json, ensure_ascii=False) if candidate.bbox_json else None,
                )
            )

        for check in buyer_validation.checks:
            self.session.add(
                FieldCheck(
                    invoice_id=invoice.id,
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

    def _mark_invoice_failed(self, *, invoice_id: str, reason: str) -> None:
        invoice = self.session.get(InvoiceRecord, invoice_id)
        if invoice is None:
            return

        invoice.processing_status = "processing_failed"
        invoice.system_decision = None
        invoice.parse_source = None
        invoice.renamed_filename = None
        invoice.storage_path_renamed = None
        invoice.artifact_status = "original_only"
        invoice.duplicate_flag = False
        invoice.duplicate_group_key = None
        invoice.risk_flags = "[]"
        invoice.display_status = derive_display_status(
            processing_status=invoice.processing_status,
            system_decision=invoice.system_decision,
            duplicate_flag=invoice.duplicate_flag,
        )
        invoice.problem_count = 1
        invoice.failure_reason = reason
        invoice.evidence_items.clear()
        invoice.extracted_fields.clear()
        invoice.field_checks.clear()
        self.session.commit()

        log_event(
            self.logger,
            "invoice_processing_failed",
            invoice_id=invoice.id,
            original_filename=invoice.original_filename,
            reason=reason,
        )

    def _parse_document(self, content: bytes) -> ParsedDocument:
        raw_text = content.decode("utf-8", errors="ignore")
        metadata = self._extract_fixture_metadata(raw_text)
        if metadata:
            return ParsedDocument(evidence=self._build_fixture_evidence(metadata), metadata=metadata)

        return ParsedDocument(evidence=self._build_generic_evidence(raw_text), metadata={})

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

    def _build_fixture_evidence(self, metadata: dict[str, Any]) -> UnifiedDocumentEvidence:
        parse_mode = str(metadata.get("parse_mode") or "text").strip().lower()
        overall_confidence = self._coerce_float(metadata.get("overall_confidence"), default=0.98 if parse_mode == "text" else 0.82)
        confidence_flags = self._coerce_list(metadata.get("confidence_flag"))
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
            confidence = self._coerce_float(metadata.get(f"{field_name}_confidence"), default=overall_confidence)
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

        payload = {
            "provider_name": "fixture-ocr" if parse_mode == "ocr" else "fixture-text",
            "provider_version": "2026.04",
            "raw_text": "\n".join(raw_lines),
            "pages": [{"page_no": 1}],
            "text_blocks": [{"page_no": 1, "text": "\n".join(raw_lines)}],
            "table_lines": [
                {
                    "row_no": index,
                    "text": line_text,
                    "mixed_invoice": self._coerce_bool(metadata.get("mixed_invoice")),
                }
                for index, line_text in enumerate(line_texts, start=1)
            ],
            "field_candidates": field_candidates,
            "confidence_summary": {
                "overall": overall_confidence,
                "fields": confidence_fields,
                "flags": confidence_flags,
            },
        }
        if parse_mode == "ocr":
            return adapt_ocr_output(payload)
        return adapt_text_extraction(payload)

    def _build_generic_evidence(self, raw_text: str) -> UnifiedDocumentEvidence:
        normalized_text = "\n".join(line.strip() for line in raw_text.splitlines() if line.strip())
        if not normalized_text:
            raise ValueError("No usable text extracted from document.")

        field_candidates: list[dict[str, Any]] = []
        confidence_fields: dict[str, float] = {}
        for field_name, pattern in GENERIC_FIELD_PATTERNS.items():
            match = pattern.search(normalized_text)
            if not match:
                continue
            value = match.group(1).strip()
            field_candidates.append(
                {
                    "field_name": field_name,
                    "value": value,
                    "confidence": 0.72,
                    "page_no": 1,
                    "source_fragment": match.group(0).strip(),
                }
            )
            confidence_fields[field_name] = 0.72

        if not field_candidates:
            raise ValueError("Unable to extract invoice fields from document text.")

        payload = {
            "provider_name": "raw-text-scan",
            "provider_version": "2026.04",
            "raw_text": normalized_text,
            "pages": [{"page_no": 1}],
            "text_blocks": [{"page_no": 1, "text": normalized_text}],
            "table_lines": [{"row_no": index, "text": line} for index, line in enumerate(normalized_text.splitlines(), start=1)],
            "field_candidates": field_candidates,
            "confidence_summary": {
                "overall": 0.72,
                "fields": confidence_fields,
                "flags": ["low_confidence"],
            },
        }
        return adapt_text_extraction(payload)

    @staticmethod
    def _candidate_value(evidence: UnifiedDocumentEvidence, field_name: str) -> str | None:
        candidate = evidence.best_candidate(field_name)
        if candidate is None:
            return None
        value = candidate.value.strip()
        return value or None

    def _candidate_date(self, evidence: UnifiedDocumentEvidence, field_name: str) -> date | None:
        value = self._candidate_value(evidence, field_name)
        if not value:
            return None
        normalized = value.replace("/", "-")
        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            return None

    @staticmethod
    def _candidate_amount(evidence: UnifiedDocumentEvidence, field_name: str) -> Decimal | None:
        candidate = evidence.best_candidate(field_name)
        if candidate is None or not candidate.value.strip():
            return None
        try:
            return Decimal(candidate.value.strip()).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    @staticmethod
    def _compute_problem_count(*, risk_flags: list[str], buyer_validation: BuyerValidationResult) -> int:
        count = len(risk_flags)
        count += sum(1 for check in buyer_validation.checks if check.match_result != "matched")
        return count

    def _resolve_naming_template(self, snapshot: dict[str, Any]) -> str:
        naming_rules = self._snapshot_content(snapshot, "naming_rules")
        raw_pattern = str(naming_rules.get("pattern") or "").strip()
        if not raw_pattern:
            return DEFAULT_NAMING_TEMPLATE

        template = raw_pattern
        for source, target in SUPPORTED_NAMING_KEYS.items():
            template = template.replace(source, target)

        if "{invoice_number}" not in template or "{amount}" not in template or "{date}" not in template:
            return DEFAULT_NAMING_TEMPLATE
        if not template.endswith(".pdf"):
            template = f"{template}.pdf"
        return template

    def _write_renamed_copy(self, *, batch_no: str, source_path: Path, target_name: str) -> Path:
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
