from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.parsing.evidence_models import UnifiedDocumentEvidence


HIGH_CONFIDENCE_THRESHOLD = 0.85
BUYER_FIELDS = (
    "buyer_name",
    "buyer_tax_no",
    "buyer_address",
    "buyer_phone",
    "buyer_bank",
    "buyer_account",
)


@dataclass(frozen=True)
class BuyerFieldCheckResult:
    field_name: str
    expected_value: str | None
    actual_value: str | None
    match_result: str
    reason: str
    confidence: float | None = None


@dataclass(frozen=True)
class BuyerValidationResult:
    decision: str
    reasons: list[str]
    checks: list[BuyerFieldCheckResult]


def validate_buyer_fields(
    *,
    evidence: UnifiedDocumentEvidence,
    tax_profile: dict[str, object],
    high_confidence_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
) -> BuyerValidationResult:
    checks: list[BuyerFieldCheckResult] = []
    reject_reasons: list[str] = []
    review_reasons: list[str] = []

    for field_name in BUYER_FIELDS:
        allowed_values = _allowed_values(field_name=field_name, tax_profile=tax_profile)
        if not allowed_values:
            continue

        candidate = evidence.best_candidate(field_name)
        expected_value = ", ".join(sorted(allowed_values))
        if candidate is None or not candidate.value.strip():
            checks.append(
                BuyerFieldCheckResult(
                    field_name=field_name,
                    expected_value=expected_value,
                    actual_value=None,
                    match_result="missing",
                    reason="Field not present in extracted evidence; strict reject is skipped.",
                )
            )
            continue

        actual_value = candidate.normalized_value or _normalize_field(
            field_name, candidate.value
        )
        if candidate.confidence < high_confidence_threshold:
            reason = f"{field_name} extracted with low confidence ({candidate.confidence:.2f})."
            checks.append(
                BuyerFieldCheckResult(
                    field_name=field_name,
                    expected_value=expected_value,
                    actual_value=actual_value,
                    match_result="low_confidence",
                    reason=reason,
                    confidence=candidate.confidence,
                )
            )
            review_reasons.append(reason)
            continue

        if actual_value in allowed_values:
            checks.append(
                BuyerFieldCheckResult(
                    field_name=field_name,
                    expected_value=expected_value,
                    actual_value=actual_value,
                    match_result="matched",
                    reason="High-confidence buyer field matched the configured tax profile.",
                    confidence=candidate.confidence,
                )
            )
            continue

        reason = f"{field_name} mismatched the configured buyer profile."
        checks.append(
            BuyerFieldCheckResult(
                field_name=field_name,
                expected_value=expected_value,
                actual_value=actual_value,
                match_result="mismatched",
                reason=reason,
                confidence=candidate.confidence,
            )
        )
        reject_reasons.append(reason)

    if reject_reasons:
        return BuyerValidationResult(
            decision="suggested_reject", reasons=reject_reasons, checks=checks
        )
    if review_reasons:
        return BuyerValidationResult(
            decision="review_required", reasons=review_reasons, checks=checks
        )
    return BuyerValidationResult(decision="suggested_pass", reasons=[], checks=checks)


def _allowed_values(*, field_name: str, tax_profile: dict[str, object]) -> set[str]:
    allowed_values: set[str] = set()
    primary = tax_profile.get(field_name)
    if isinstance(primary, str) and primary.strip():
        allowed_values.add(_normalize_field(field_name, primary))

    alias_key = f"{field_name}_aliases"
    aliases = tax_profile.get(alias_key, [])
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                allowed_values.add(_normalize_field(field_name, alias))
    return allowed_values


def _normalize_field(field_name: str, value: str) -> str:
    compact = "".join(value.split()).strip()
    if field_name in {"buyer_tax_no", "buyer_phone", "buyer_account"}:
        return compact.upper()
    return compact
