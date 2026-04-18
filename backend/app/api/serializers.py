from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from backend.app.db.models import Batch, DocumentEvidence, ExportJob, ExtractedField, FieldCheck, InvoiceRecord, ReviewAction, RuleVersion
from backend.app.services.compliance_service import serialize_invoice_compliance
from backend.app.services.progress_service import BatchProgressSnapshot
from backend.app.services.status_service import derive_display_status


def _json_load(value: str, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _serialize_scalar(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def serialize_batch(
    batch: Batch,
    *,
    progress: BatchProgressSnapshot | None = None,
    include_snapshot: bool = False,
    include_exports: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": batch.id,
        "batch_no": batch.batch_no,
        "created_at": _serialize_scalar(batch.created_at),
        "created_by": batch.created_by,
        "status": batch.status,
        "total_files": batch.total_files,
        "completed_files": batch.completed_files,
        "processing_files": batch.processing_files,
        "failed_files": batch.failed_files,
        "suggested_pass_count": batch.suggested_pass_count,
        "suggested_pass_total_amount": _serialize_scalar(batch.suggested_pass_total_amount),
        "export_manifest_path": batch.export_manifest_path,
    }
    if progress is not None:
        payload["progress"] = progress.to_dict()
    if include_snapshot:
        payload["snapshot"] = _json_load(batch.snapshot_json, {})
    if include_exports:
        payload["export_jobs"] = [serialize_export_job(job) for job in sorted(batch.export_jobs, key=lambda item: item.created_at)]
    return payload


def serialize_export_job(job: ExportJob) -> dict[str, object]:
    return {
        "id": job.id,
        "export_type": job.export_type,
        "status": job.status,
        "output_path": job.output_path,
        "created_by": job.created_by,
        "created_at": _serialize_scalar(job.created_at),
        "summary": _json_load(job.summary_json, {}),
    }


def serialize_invoice_summary(invoice: InvoiceRecord) -> dict[str, object]:
    display_status = derive_display_status(
        processing_status=invoice.processing_status,
        system_decision=invoice.system_decision,
        duplicate_flag=invoice.duplicate_flag,
    )
    payload = {
        "id": invoice.id,
        "batch_id": invoice.batch_id,
        "original_filename": invoice.original_filename,
        "renamed_filename": invoice.renamed_filename,
        "storage_path_original": invoice.storage_path_original,
        "storage_path_renamed": invoice.storage_path_renamed,
        "invoice_code": invoice.invoice_code,
        "invoice_number": invoice.invoice_number,
        "seller_name": invoice.seller_name,
        "buyer_name": invoice.buyer_name,
        "buyer_tax_no": invoice.buyer_tax_no,
        "invoice_date": _serialize_scalar(invoice.invoice_date),
        "invoice_amount": _serialize_scalar(invoice.invoice_amount),
        "parse_source": invoice.parse_source,
        "processing_status": invoice.processing_status,
        "system_decision": invoice.system_decision,
        "review_status": invoice.review_status,
        "artifact_status": invoice.artifact_status,
        "duplicate_flag": invoice.duplicate_flag,
        "duplicate_group_key": invoice.duplicate_group_key,
        "risk_flags": _json_load(invoice.risk_flags, []),
        "display_status": display_status,
        "problem_count": invoice.problem_count,
        "failure_reason": invoice.failure_reason,
        "preview_path": invoice.storage_path_renamed or invoice.storage_path_original,
    }
    payload.update(serialize_invoice_compliance(invoice))
    return payload


def serialize_invoice_detail(invoice: InvoiceRecord) -> dict[str, object]:
    payload = serialize_invoice_summary(invoice)
    payload["last_error_stage"] = invoice.last_error_stage
    payload["last_error_code"] = invoice.last_error_code
    payload["last_error_message"] = invoice.last_error_message
    payload["retryable"] = invoice.retryable
    payload["provider_diagnostic"] = _latest_attempt_diagnostic(invoice)
    payload["evidence_items"] = [serialize_document_evidence(item) for item in invoice.evidence_items]
    payload["extracted_fields"] = [serialize_extracted_field(item) for item in invoice.extracted_fields]
    payload["field_checks"] = [serialize_field_check(item) for item in invoice.field_checks]
    payload["review_actions"] = [serialize_review_action(item) for item in invoice.review_actions]
    return payload


def _latest_attempt_diagnostic(invoice: InvoiceRecord) -> dict[str, object]:
    if not invoice.last_attempt_id:
        return {}
    for attempt in invoice.processing_attempts:
        if attempt.id == invoice.last_attempt_id:
            return _json_load(attempt.diagnostic_json, {})
    return {}


def serialize_document_evidence(evidence: DocumentEvidence) -> dict[str, object]:
    return {
        "id": evidence.id,
        "source_type": evidence.source_type,
        "raw_text": evidence.raw_text,
        "pages": _json_load(evidence.pages_json, []),
        "text_blocks": _json_load(evidence.text_blocks_json, []),
        "table_lines": _json_load(evidence.table_lines_json, []),
        "field_candidates": _json_load(evidence.field_candidates_json, []),
        "confidence_summary": _json_load(evidence.confidence_summary_json, {}),
        "provider_name": evidence.provider_name,
        "provider_version": evidence.provider_version,
        "provider_error_code": evidence.provider_error_code,
    }


def serialize_extracted_field(field: ExtractedField) -> dict[str, object]:
    return {
        "id": field.id,
        "field_name": field.field_name,
        "extracted_value": field.extracted_value,
        "normalized_value": field.normalized_value,
        "confidence": _serialize_scalar(field.confidence),
        "page_no": field.page_no,
        "source_fragment": field.source_fragment,
        "bbox": _json_load(field.bbox_json or "", None),
    }


def serialize_field_check(check: FieldCheck) -> dict[str, object]:
    return {
        "id": check.id,
        "field_name": check.field_name,
        "expected_value": check.expected_value,
        "actual_value": check.actual_value,
        "match_result": check.match_result,
        "reason": check.reason,
    }


def serialize_review_action(action: ReviewAction) -> dict[str, object]:
    return {
        "id": action.id,
        "review_action": action.review_action,
        "review_note": action.review_note,
        "reviewed_by": action.reviewed_by,
        "reviewed_at": _serialize_scalar(action.reviewed_at),
    }


def serialize_rule_version(version: RuleVersion) -> dict[str, object]:
    return {
        "id": version.id,
        "kind": version.kind,
        "version_no": version.version_no,
        "content": _json_load(version.content_json, {}),
        "is_active": version.is_active,
        "change_summary": version.change_summary,
        "changed_by": version.changed_by,
        "changed_at": _serialize_scalar(version.changed_at),
        "change_reason": version.change_reason,
    }
