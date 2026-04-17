from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


DISPLAY_STATUS_FAILED = "处理失败"
DISPLAY_STATUS_DUPLICATE = "疑似重复"
DISPLAY_STATUS_REVIEW = "待复核"
DISPLAY_STATUS_REJECT = "系统建议驳回"
DISPLAY_STATUS_PASS = "系统建议通过"


@dataclass(frozen=True)
class SuggestedPassSummary:
    count: int
    total_amount: Decimal


def derive_display_status(
    *,
    processing_status: str | None,
    system_decision: str | None,
    duplicate_flag: bool,
) -> str:
    if processing_status in {"failed", "processing_failed"}:
        return DISPLAY_STATUS_FAILED
    if duplicate_flag:
        return DISPLAY_STATUS_DUPLICATE
    if system_decision == "review_required":
        return DISPLAY_STATUS_REVIEW
    if system_decision == "suggested_reject":
        return DISPLAY_STATUS_REJECT
    if system_decision == "suggested_pass":
        return DISPLAY_STATUS_PASS
    return DISPLAY_STATUS_REVIEW


def summarize_suggested_pass(
    records: list[Any],
    *,
    filter_display_status: str | None = None,
) -> SuggestedPassSummary:
    count = 0
    total_amount = Decimal("0.00")

    for record in records:
        display_status = getattr(record, "display_status", None) or derive_display_status(
            processing_status=getattr(record, "processing_status", None),
            system_decision=getattr(record, "system_decision", None),
            duplicate_flag=bool(getattr(record, "duplicate_flag", False)),
        )
        if filter_display_status is not None and display_status != filter_display_status:
            continue
        if getattr(record, "system_decision", None) != "suggested_pass":
            continue
        if bool(getattr(record, "duplicate_flag", False)):
            continue

        amount = getattr(record, "invoice_amount", None)
        count += 1
        if amount not in (None, ""):
            total_amount += Decimal(str(amount)).quantize(Decimal("0.01"))

    return SuggestedPassSummary(count=count, total_amount=total_amount.quantize(Decimal("0.01")))
