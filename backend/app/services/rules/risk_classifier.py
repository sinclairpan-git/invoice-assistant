from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.parsing.evidence_models import UnifiedDocumentEvidence
from backend.app.services.rules.buyer_validation import BuyerValidationResult


DEFAULT_REVIEW_KEYWORDS = ("详见清单", "详见销货清单", "混合票", "混合项目")


@dataclass(frozen=True)
class RiskClassificationResult:
    decision: str
    reasons: list[str]
    risk_flags: list[str]
    matched_rules: list[str]


def classify_risk(
    *,
    evidence: UnifiedDocumentEvidence,
    business_rules: dict[str, object],
    buyer_validation: BuyerValidationResult | None = None,
    attachment_evidence: UnifiedDocumentEvidence | None = None,
) -> RiskClassificationResult:
    evidence = _select_classification_evidence(
        evidence=evidence,
        business_rules=business_rules,
        attachment_evidence=attachment_evidence,
    )

    if buyer_validation and buyer_validation.decision == "suggested_reject":
        return RiskClassificationResult(
            decision="suggested_reject",
            reasons=buyer_validation.reasons,
            risk_flags=["buyer_mismatch"],
            matched_rules=["buyer_validation"],
        )

    risk_flags: list[str] = []
    reasons: list[str] = []
    matched_rules: list[str] = []

    minimum_confidence = float(business_rules.get("minimum_confidence", 0.75))
    if evidence.confidence_summary.overall < minimum_confidence:
        risk_flags.append("low_confidence")
        reasons.append(
            f"Overall extraction confidence {evidence.confidence_summary.overall:.2f} is below threshold {minimum_confidence:.2f}."
        )
        matched_rules.append("minimum_confidence")

    if any(
        flag in {"low_confidence", "ocr_low_confidence"}
        for flag in evidence.confidence_summary.flags
    ):
        risk_flags.append("low_confidence")
        reasons.append(
            "Confidence summary already flagged the document as low confidence."
        )
        matched_rules.append("confidence_summary_flag")

    review_keywords = _normalized_set(
        business_rules.get("review_keywords", DEFAULT_REVIEW_KEYWORDS)
    )
    reject_keywords = _normalized_set(business_rules.get("reject_keywords", []))
    pass_keywords = _normalized_set(business_rules.get("pass_keywords", []))
    seller_blacklist = _normalized_set(business_rules.get("seller_blacklist", []))
    seller_whitelist = _normalized_set(business_rules.get("seller_whitelist", []))

    line_texts = [
        _normalize_text(str(line.get("text") or "")) for line in evidence.table_lines
    ]
    if any(
        keyword and keyword in line_text
        for keyword in review_keywords
        for line_text in line_texts
    ):
        risk_flags.append("fuzzy_line_items")
        reasons.append("Line items contain review keywords and require manual review.")
        matched_rules.append("review_keywords")

    if any(
        line.get("mixed_invoice") or line.get("fuzzy") for line in evidence.table_lines
    ):
        risk_flags.append("mixed_invoice")
        reasons.append("Line item metadata indicates mixed or fuzzy invoice content.")
        matched_rules.append("table_line_metadata")

    seller_candidate = evidence.best_candidate("seller_name")
    seller_name = _normalize_text(seller_candidate.value) if seller_candidate else ""
    if seller_name and seller_name in seller_blacklist:
        risk_flags.append("seller_blacklist_hit")
        reasons.append("Seller matched a configured blacklist entry.")
        matched_rules.append("seller_blacklist")
        return RiskClassificationResult(
            decision="suggested_reject",
            reasons=reasons,
            risk_flags=_dedupe(risk_flags),
            matched_rules=_dedupe(matched_rules),
        )

    if any(
        keyword and keyword in line_text
        for keyword in reject_keywords
        for line_text in line_texts
    ):
        risk_flags.append("reject_keyword_hit")
        reasons.append("Line items matched a configured reject keyword.")
        matched_rules.append("reject_keywords")
        return RiskClassificationResult(
            decision="suggested_reject",
            reasons=reasons,
            risk_flags=_dedupe(risk_flags),
            matched_rules=_dedupe(matched_rules),
        )

    if risk_flags:
        return RiskClassificationResult(
            decision="review_required",
            reasons=_dedupe(reasons),
            risk_flags=_dedupe(risk_flags),
            matched_rules=_dedupe(matched_rules),
        )

    if seller_name and seller_name in seller_whitelist:
        reasons.append("Seller matched whitelist rule.")
        matched_rules.append("seller_whitelist")
        return RiskClassificationResult(
            decision="suggested_pass",
            reasons=reasons,
            risk_flags=[],
            matched_rules=matched_rules,
        )

    if any(
        keyword and keyword in line_text
        for keyword in pass_keywords
        for line_text in line_texts
    ):
        reasons.append("Line items matched a configured pass keyword.")
        matched_rules.append("pass_keywords")
        return RiskClassificationResult(
            decision="suggested_pass",
            reasons=reasons,
            risk_flags=[],
            matched_rules=matched_rules,
        )

    return RiskClassificationResult(
        decision="suggested_pass",
        reasons=["No explicit risk rule matched; defaulting to pass."],
        risk_flags=[],
        matched_rules=[],
    )


def _normalized_set(raw_values: object) -> set[str]:
    if isinstance(raw_values, (list, tuple, set)):
        return {
            _normalize_text(str(value)) for value in raw_values if str(value).strip()
        }
    return set()


def _select_classification_evidence(
    *,
    evidence: UnifiedDocumentEvidence,
    business_rules: dict[str, object],
    attachment_evidence: UnifiedDocumentEvidence | None,
) -> UnifiedDocumentEvidence:
    if attachment_evidence is None or not attachment_evidence.table_lines:
        return evidence

    review_keywords = _normalized_set(
        business_rules.get("review_keywords", DEFAULT_REVIEW_KEYWORDS)
    )
    line_texts = [
        _normalize_text(str(line.get("text") or "")) for line in evidence.table_lines
    ]
    has_review_keyword = any(
        keyword and keyword in line_text
        for keyword in review_keywords
        for line_text in line_texts
    )
    if not has_review_keyword:
        return evidence

    minimum_confidence = float(business_rules.get("minimum_confidence", 0.75))
    if attachment_evidence.confidence_summary.overall < minimum_confidence:
        return evidence
    if any(
        flag in {"low_confidence", "ocr_low_confidence"}
        for flag in attachment_evidence.confidence_summary.flags
    ):
        return evidence

    merged = evidence.model_copy(deep=True)
    merged.table_lines = [dict(line) for line in attachment_evidence.table_lines]
    return merged


def _normalize_text(value: str) -> str:
    return "".join(value.split()).strip()


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
