from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import re


DEFAULT_NAMING_TEMPLATE = "{date}_{amount}_{invoice_number}.pdf"


@dataclass(frozen=True)
class NamingResult:
    renamed_filename: str | None
    reason: str | None


def build_renamed_filename(
    *,
    invoice_date: date | datetime | None,
    invoice_amount: Decimal | str | float | None,
    invoice_number: str | None,
    template: str = DEFAULT_NAMING_TEMPLATE,
) -> NamingResult:
    missing_fields = []
    if invoice_date is None:
        missing_fields.append("invoice_date")
    if invoice_amount in (None, ""):
        missing_fields.append("invoice_amount")
    if not str(invoice_number or "").strip():
        missing_fields.append("invoice_number")
    if missing_fields:
        reason = "Missing required rename fields: " + ", ".join(missing_fields)
        return NamingResult(renamed_filename=None, reason=reason)

    normalized_date = _format_date(invoice_date)
    normalized_amount = _format_amount(invoice_amount)
    normalized_invoice_number = _sanitize_component(str(invoice_number))
    filename = template.format(
        date=normalized_date,
        amount=normalized_amount,
        invoice_number=normalized_invoice_number,
    )
    return NamingResult(renamed_filename=filename, reason=None)


def _format_date(value: date | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().strftime("%Y%m%d")
    return value.strftime("%Y%m%d")


def _format_amount(value: Decimal | str | float) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount:.2f}"


def _sanitize_component(value: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", value.strip())
