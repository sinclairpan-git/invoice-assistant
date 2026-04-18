from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class DuplicateDetectionResult:
    duplicate_flag: bool
    duplicate_group_key: str | None
    decision: str
    risk_flags: list[str]
    matched_keys: list[str]


def detect_suspected_duplicate(
    *,
    invoice_data: dict[str, Any],
    history: list[dict[str, Any]],
) -> DuplicateDetectionResult:
    current_key = build_duplicate_group_key(invoice_data)
    if current_key is None:
        return DuplicateDetectionResult(
            duplicate_flag=False,
            duplicate_group_key=None,
            decision=str(invoice_data.get("system_decision") or "review_required"),
            risk_flags=list(invoice_data.get("risk_flags", [])),
            matched_keys=[],
        )

    matched_keys = [
        history_key
        for item in history
        if (history_key := build_duplicate_group_key(item)) == current_key
    ]
    if not matched_keys:
        return DuplicateDetectionResult(
            duplicate_flag=False,
            duplicate_group_key=current_key,
            decision=str(invoice_data.get("system_decision") or "review_required"),
            risk_flags=list(invoice_data.get("risk_flags", [])),
            matched_keys=[],
        )

    decision = str(invoice_data.get("system_decision") or "review_required")
    if decision == "suggested_pass":
        decision = "review_required"

    risk_flags = list(invoice_data.get("risk_flags", []))
    if "suspected_duplicate" not in risk_flags:
        risk_flags.append("suspected_duplicate")

    return DuplicateDetectionResult(
        duplicate_flag=True,
        duplicate_group_key=current_key,
        decision=decision,
        risk_flags=risk_flags,
        matched_keys=matched_keys,
    )


def build_duplicate_group_key(invoice_data: dict[str, Any]) -> str | None:
    invoice_number = _normalize_text(invoice_data.get("invoice_number"))
    invoice_code = _normalize_text(invoice_data.get("invoice_code"))
    seller_name = _normalize_text(invoice_data.get("seller_name"))
    invoice_date = _normalize_date(invoice_data.get("invoice_date"))
    invoice_amount = _normalize_amount(invoice_data.get("invoice_amount"))

    required_values = (invoice_number, seller_name, invoice_date, invoice_amount)
    if any(value is None or value == "" for value in required_values):
        return None

    code_segment = invoice_code or "-"
    return "|".join(
        [invoice_number, code_segment, invoice_date, invoice_amount, seller_name]
    )


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return "".join(str(value).split()).strip().upper()


def _normalize_date(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _normalize_amount(value: object) -> str | None:
    if value is None or value == "":
        return None
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount:.2f}"
