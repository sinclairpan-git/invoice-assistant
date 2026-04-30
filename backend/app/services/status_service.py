from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


DISPLAY_STATUS_FAILED = "处理失败"
DISPLAY_STATUS_PROCESSING = "处理中"
DISPLAY_STATUS_DUPLICATE = "疑似重复"
DISPLAY_STATUS_REVIEW = "待复核"
DISPLAY_STATUS_REJECT = "系统建议驳回"
DISPLAY_STATUS_PASS = "系统建议通过"

BUSINESS_BUCKET_SUGGESTED_PASS = "suggested_pass"
BUSINESS_BUCKET_PENDING_REVIEW = "pending_review"
BUSINESS_BUCKET_BATCH_DUPLICATE = "batch_duplicate"
BUSINESS_BUCKET_NEEDS_ATTENTION = "needs_attention"

BUSINESS_BUCKET_LABELS = {
    BUSINESS_BUCKET_SUGGESTED_PASS: "建议通过",
    BUSINESS_BUCKET_PENDING_REVIEW: "待人工确认",
    BUSINESS_BUCKET_BATCH_DUPLICATE: "本批次重复",
    BUSINESS_BUCKET_NEEDS_ATTENTION: "需补充/重试",
}


@dataclass(frozen=True)
class SuggestedPassSummary:
    count: int
    total_amount: Decimal


@dataclass(frozen=True)
class StableInvoiceStatus:
    processing_status: str
    review_status: str
    archive_status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "processing_status": self.processing_status,
            "review_status": self.review_status,
            "archive_status": self.archive_status,
        }


@dataclass(frozen=True)
class BatchActionSummary:
    suggested_pass_count: int
    pending_review_count: int
    batch_duplicate_count: int
    needs_attention_count: int

    def to_dict(self) -> dict[str, dict[str, object]]:
        return {
            BUSINESS_BUCKET_SUGGESTED_PASS: {
                "label": BUSINESS_BUCKET_LABELS[BUSINESS_BUCKET_SUGGESTED_PASS],
                "count": self.suggested_pass_count,
            },
            BUSINESS_BUCKET_PENDING_REVIEW: {
                "label": BUSINESS_BUCKET_LABELS[BUSINESS_BUCKET_PENDING_REVIEW],
                "count": self.pending_review_count,
            },
            BUSINESS_BUCKET_BATCH_DUPLICATE: {
                "label": BUSINESS_BUCKET_LABELS[BUSINESS_BUCKET_BATCH_DUPLICATE],
                "count": self.batch_duplicate_count,
            },
            BUSINESS_BUCKET_NEEDS_ATTENTION: {
                "label": BUSINESS_BUCKET_LABELS[BUSINESS_BUCKET_NEEDS_ATTENTION],
                "count": self.needs_attention_count,
            },
        }


def normalize_processing_status(processing_status: str | None) -> str:
    if processing_status in {"failed", "processing_failed"}:
        return "failed"
    if processing_status in {None, "", "queued"}:
        return "queued"
    if processing_status == "completed":
        return "completed"
    return "processing"


def normalize_review_status(
    review_status: str | None,
    *,
    system_decision: str | None,
    duplicate_flag: bool,
) -> str:
    if review_status in {"approved", "manually_approved"}:
        return "approved"
    if review_status in {"rejected", "manually_rejected"}:
        return "rejected"
    if review_status == "pending":
        return "pending"
    if system_decision == "review_required" or duplicate_flag:
        return "pending"
    return "not_required"


def derive_archive_status(
    *,
    processing_status: str | None,
    system_decision: str | None,
    duplicate_flag: bool,
    review_status: str | None,
    archive_status: str | None = None,
    artifact_status: str | None = None,
) -> str:
    if archive_status == "saved" or artifact_status == "saved":
        return "saved"

    normalized_processing = normalize_processing_status(processing_status)
    normalized_review = normalize_review_status(
        review_status,
        system_decision=system_decision,
        duplicate_flag=duplicate_flag,
    )

    if normalized_processing != "completed":
        return "not_ready"
    if normalized_review == "approved":
        return "ready_to_save"
    if normalized_review == "rejected":
        return "not_ready"
    if duplicate_flag:
        return "not_ready"
    if system_decision == "suggested_reject":
        return "not_ready"
    if normalized_review == "pending":
        return "not_ready"
    if system_decision in {"suggested_pass", "review_required"}:
        return "ready_to_save"
    return "not_ready"


def derive_stable_status(
    *,
    processing_status: str | None,
    system_decision: str | None,
    duplicate_flag: bool,
    review_status: str | None = None,
    archive_status: str | None = None,
    artifact_status: str | None = None,
) -> StableInvoiceStatus:
    normalized_processing = normalize_processing_status(processing_status)
    normalized_review = normalize_review_status(
        review_status,
        system_decision=system_decision,
        duplicate_flag=duplicate_flag,
    )
    normalized_archive = derive_archive_status(
        processing_status=normalized_processing,
        system_decision=system_decision,
        duplicate_flag=duplicate_flag,
        review_status=normalized_review,
        archive_status=archive_status,
        artifact_status=artifact_status,
    )
    return StableInvoiceStatus(
        processing_status=normalized_processing,
        review_status=normalized_review,
        archive_status=normalized_archive,
    )


def derive_display_status(
    *,
    processing_status: str | None,
    system_decision: str | None,
    duplicate_flag: bool,
    review_status: str | None = None,
) -> str:
    stable_status = derive_stable_status(
        processing_status=processing_status,
        system_decision=system_decision,
        duplicate_flag=duplicate_flag,
        review_status=review_status,
    )
    if stable_status.processing_status == "failed":
        return DISPLAY_STATUS_FAILED
    if stable_status.processing_status != "completed":
        return DISPLAY_STATUS_PROCESSING
    if stable_status.review_status == "approved":
        return DISPLAY_STATUS_PASS
    if stable_status.review_status == "rejected":
        return DISPLAY_STATUS_REJECT
    if duplicate_flag:
        return DISPLAY_STATUS_DUPLICATE
    if system_decision == "review_required":
        return DISPLAY_STATUS_REVIEW
    if system_decision == "suggested_reject":
        return DISPLAY_STATUS_REJECT
    if system_decision == "suggested_pass":
        return DISPLAY_STATUS_PASS
    return DISPLAY_STATUS_REVIEW


def derive_business_bucket(
    *,
    processing_status: str | None,
    system_decision: str | None,
    duplicate_flag: bool,
    review_status: str | None = None,
) -> str:
    normalized_processing = normalize_processing_status(processing_status)
    normalized_review = normalize_review_status(
        review_status,
        system_decision=system_decision,
        duplicate_flag=duplicate_flag,
    )

    if normalized_processing != "completed":
        return BUSINESS_BUCKET_NEEDS_ATTENTION
    if normalized_review == "approved":
        return BUSINESS_BUCKET_SUGGESTED_PASS
    if normalized_review == "rejected":
        return BUSINESS_BUCKET_NEEDS_ATTENTION
    if duplicate_flag:
        return BUSINESS_BUCKET_BATCH_DUPLICATE
    if system_decision == "suggested_pass":
        return BUSINESS_BUCKET_SUGGESTED_PASS
    if system_decision == "review_required" or normalized_review == "pending":
        return BUSINESS_BUCKET_PENDING_REVIEW
    return BUSINESS_BUCKET_NEEDS_ATTENTION


def derive_business_bucket_label(bucket: str) -> str:
    return BUSINESS_BUCKET_LABELS.get(bucket, bucket)


def summarize_business_buckets(records: list[Any]) -> BatchActionSummary:
    counts = {
        BUSINESS_BUCKET_SUGGESTED_PASS: 0,
        BUSINESS_BUCKET_PENDING_REVIEW: 0,
        BUSINESS_BUCKET_BATCH_DUPLICATE: 0,
        BUSINESS_BUCKET_NEEDS_ATTENTION: 0,
    }

    for record in records:
        bucket = derive_business_bucket(
            processing_status=getattr(record, "processing_status", None),
            system_decision=getattr(record, "system_decision", None),
            duplicate_flag=bool(getattr(record, "duplicate_flag", False)),
            review_status=getattr(record, "review_status", None),
        )
        counts[bucket] = counts.get(bucket, 0) + 1

    return BatchActionSummary(
        suggested_pass_count=counts[BUSINESS_BUCKET_SUGGESTED_PASS],
        pending_review_count=counts[BUSINESS_BUCKET_PENDING_REVIEW],
        batch_duplicate_count=counts[BUSINESS_BUCKET_BATCH_DUPLICATE],
        needs_attention_count=counts[BUSINESS_BUCKET_NEEDS_ATTENTION],
    )


def summarize_suggested_pass(
    records: list[Any],
    *,
    filter_display_status: str | None = None,
) -> SuggestedPassSummary:
    count = 0
    total_amount = Decimal("0.00")

    for record in records:
        display_status = derive_display_status(
            processing_status=getattr(record, "processing_status", None),
            system_decision=getattr(record, "system_decision", None),
            duplicate_flag=bool(getattr(record, "duplicate_flag", False)),
            review_status=getattr(record, "review_status", None),
        )
        if (
            filter_display_status is not None
            and display_status != filter_display_status
        ):
            continue

        if normalize_processing_status(getattr(record, "processing_status", None)) != "completed":
            continue
        if bool(getattr(record, "duplicate_flag", False)):
            continue
        if getattr(record, "system_decision", None) != "suggested_pass":
            continue

        amount = getattr(record, "invoice_amount", None)
        count += 1
        if amount not in (None, ""):
            total_amount += Decimal(str(amount)).quantize(Decimal("0.01"))

    return SuggestedPassSummary(
        count=count, total_amount=total_amount.quantize(Decimal("0.01"))
    )
