from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.app.db.models import InvoiceRecord
from backend.app.services.status_service import derive_display_status


APPROVED_REVIEW_STATUSES = {"manually_approved"}
REJECTED_REVIEW_STATUSES = {"manually_rejected"}
RISK_FLAG_LABELS = {
    "low_confidence": "低置信度",
    "fuzzy_line_items": "明细模糊",
    "suspected_duplicate": "疑似重复",
}


@dataclass(frozen=True)
class InvoiceComplianceSummary:
    basic_compliance_status: str
    business_compliance_status: str
    final_decision: str
    decision_reasons: list[str]
    suggested_actions: list[str]
    archiveable_pass: bool
    pending_review_gate: bool


@dataclass(frozen=True)
class ArchiveablePassSummary:
    count: int
    total_amount: Decimal


def build_invoice_compliance_summary(
    invoice: InvoiceRecord,
) -> InvoiceComplianceSummary:
    display_status = derive_display_status(
        processing_status=invoice.processing_status,
        system_decision=invoice.system_decision,
        duplicate_flag=invoice.duplicate_flag,
    )
    field_failures = _field_failures(invoice)
    risk_reasons = [
        _risk_flag_label(flag) for flag in _load_json_list(invoice.risk_flags)
    ]
    review_reason = _review_reason(invoice)

    basic_status = (
        "不通过"
        if invoice.processing_status in {"failed", "processing_failed"}
        else "通过"
    )
    pending_review_gate = (
        invoice.system_decision == "review_required"
        and not invoice.duplicate_flag
        and invoice.review_status not in APPROVED_REVIEW_STATUSES
        and invoice.review_status not in REJECTED_REVIEW_STATUSES
    )

    if invoice.processing_status in {"failed", "processing_failed"}:
        reasons = _dedupe(
            [invoice.failure_reason, invoice.last_error_message, "处理失败"]
        )
        return InvoiceComplianceSummary(
            basic_compliance_status="不通过",
            business_compliance_status="不通过",
            final_decision="处理失败",
            decision_reasons=reasons,
            suggested_actions=["修复失败原因后重试"],
            archiveable_pass=False,
            pending_review_gate=False,
        )

    if invoice.review_status in APPROVED_REVIEW_STATUSES:
        reasons = _dedupe(
            field_failures + risk_reasons + [review_reason or "人工复核已确认通过"]
        )
        return InvoiceComplianceSummary(
            basic_compliance_status=basic_status,
            business_compliance_status="通过",
            final_decision="人工确认通过",
            decision_reasons=reasons or ["人工复核已确认通过"],
            suggested_actions=["纳入建议通过归档"],
            archiveable_pass=True,
            pending_review_gate=False,
        )

    if invoice.review_status in REJECTED_REVIEW_STATUSES:
        reasons = _dedupe(
            field_failures + risk_reasons + [review_reason or "人工复核已确认不通过"]
        )
        return InvoiceComplianceSummary(
            basic_compliance_status=basic_status,
            business_compliance_status="不通过",
            final_decision="人工确认不通过",
            decision_reasons=reasons or ["人工复核已确认不通过"],
            suggested_actions=["转入问题票归档"],
            archiveable_pass=False,
            pending_review_gate=False,
        )

    if invoice.duplicate_flag:
        reasons = _dedupe(field_failures + ["命中重复票指纹"] + risk_reasons)
        return InvoiceComplianceSummary(
            basic_compliance_status=basic_status,
            business_compliance_status="不通过",
            final_decision="疑似重复",
            decision_reasons=reasons or ["命中重复票指纹"],
            suggested_actions=["转入问题票归档"],
            archiveable_pass=False,
            pending_review_gate=False,
        )

    if invoice.system_decision == "suggested_reject":
        reasons = _dedupe(field_failures + risk_reasons + ["系统判定不通过"])
        return InvoiceComplianceSummary(
            basic_compliance_status=basic_status,
            business_compliance_status="不通过",
            final_decision="不合规",
            decision_reasons=reasons,
            suggested_actions=["转入问题票归档"],
            archiveable_pass=False,
            pending_review_gate=False,
        )

    if pending_review_gate or display_status == "待复核":
        reasons = _dedupe(field_failures + risk_reasons + ["系统判定需要人工复核"])
        return InvoiceComplianceSummary(
            basic_compliance_status=basic_status,
            business_compliance_status="待人工复核",
            final_decision="需人工复核",
            decision_reasons=reasons,
            suggested_actions=["需人工复核后再导出"],
            archiveable_pass=False,
            pending_review_gate=True,
        )

    if invoice.system_decision == "suggested_pass":
        reasons = _dedupe(field_failures + risk_reasons + ["系统判定通过"])
        return InvoiceComplianceSummary(
            basic_compliance_status=basic_status,
            business_compliance_status="通过",
            final_decision="可归档",
            decision_reasons=reasons,
            suggested_actions=["纳入建议通过归档"],
            archiveable_pass=True,
            pending_review_gate=False,
        )

    reasons = _dedupe(field_failures + risk_reasons + ["系统判定需要人工复核"])
    return InvoiceComplianceSummary(
        basic_compliance_status=basic_status,
        business_compliance_status="待人工复核",
        final_decision="需人工复核",
        decision_reasons=reasons,
        suggested_actions=["需人工复核后再导出"],
        archiveable_pass=False,
        pending_review_gate=True,
    )


def summarize_archiveable_pass(records: list[Any]) -> ArchiveablePassSummary:
    count = 0
    total_amount = Decimal("0.00")

    for record in records:
        summary = build_invoice_compliance_summary(record)
        if not summary.archiveable_pass:
            continue

        count += 1
        if getattr(record, "invoice_amount", None) not in (None, ""):
            total_amount += Decimal(str(record.invoice_amount)).quantize(
                Decimal("0.01")
            )

    return ArchiveablePassSummary(
        count=count, total_amount=total_amount.quantize(Decimal("0.01"))
    )


def serialize_invoice_compliance(invoice: InvoiceRecord) -> dict[str, object]:
    summary = build_invoice_compliance_summary(invoice)
    return {
        "basic_compliance_status": summary.basic_compliance_status,
        "business_compliance_status": summary.business_compliance_status,
        "final_decision": summary.final_decision,
        "decision_reasons": summary.decision_reasons,
        "suggested_actions": summary.suggested_actions,
    }


def _field_failures(invoice: InvoiceRecord) -> list[str]:
    failures: list[str] = []
    for check in invoice.field_checks:
        match_result = (check.match_result or "").lower()
        if match_result not in {
            "failed",
            "mismatch",
            "mismatched",
            "reject",
            "rejected",
        }:
            continue
        failures.append(check.reason or f"{check.field_name} 校验未通过")
    return failures


def _review_reason(invoice: InvoiceRecord) -> str | None:
    if not invoice.review_actions:
        return None
    latest_action = max(invoice.review_actions, key=lambda item: item.reviewed_at)
    if latest_action.review_action == "approve":
        return "人工复核已确认通过"
    if latest_action.review_action == "reject":
        return "人工复核已确认不通过"
    return latest_action.review_note or "人工复核已保留待复核"


def _risk_flag_label(flag: str) -> str:
    return RISK_FLAG_LABELS.get(flag, flag)


def _load_json_list(payload: str | None) -> list[str]:
    if not payload:
        return []
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dedupe(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
