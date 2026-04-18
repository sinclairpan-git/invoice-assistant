from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.parsing.evidence_models import (
    ConfidenceSummary,
    FieldCandidate,
    UnifiedDocumentEvidence,
)
from backend.app.services.rules.buyer_validation import validate_buyer_fields
from backend.app.services.rules.duplicate_detector import detect_suspected_duplicate
from backend.app.services.rules.risk_classifier import classify_risk
from backend.app.services.status_service import summarize_suggested_pass


def build_evidence(*, field_candidates, table_lines=None, overall=0.95, flags=None):
    return UnifiedDocumentEvidence(
        source_type="text",
        raw_text="invoice",
        field_candidates=field_candidates,
        table_lines=table_lines or [],
        confidence_summary=ConfidenceSummary(
            overall=overall, fields={}, flags=flags or []
        ),
        provider_name="fixture",
        provider_version="1.0",
    )


def test_high_confidence_buyer_mismatch_rejects_invoice():
    evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="buyer_name",
                value="Wrong Buyer",
                normalized_value="WrongBuyer",
                confidence=0.98,
            ),
            FieldCandidate(
                field_name="buyer_tax_no",
                value="91310000X",
                normalized_value="91310000X",
                confidence=0.96,
            ),
        ]
    )

    result = validate_buyer_fields(
        evidence=evidence,
        tax_profile={
            "buyer_name": "Shanghai Example Co",
            "buyer_name_aliases": ["ShanghaiExampleCo"],
            "buyer_tax_no": "91310000Y",
        },
    )

    assert result.decision == "suggested_reject"
    assert any(check.match_result == "mismatched" for check in result.checks)


def test_fuzzy_or_low_confidence_invoice_is_routed_to_review():
    evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Trusted Seller",
                normalized_value="TrustedSeller",
                confidence=0.90,
            ),
            FieldCandidate(
                field_name="invoice_amount",
                value="100.00",
                normalized_value="100.00",
                confidence=0.55,
            ),
        ],
        table_lines=[{"text": "详见销货清单", "fuzzy": True}],
        overall=0.62,
        flags=["low_confidence"],
    )

    result = classify_risk(
        evidence=evidence,
        business_rules={
            "minimum_confidence": 0.75,
            "review_keywords": ["详见销货清单"],
            "seller_whitelist": ["TrustedSeller"],
        },
    )

    assert result.decision == "review_required"
    assert "fuzzy_line_items" in result.risk_flags
    assert "low_confidence" in result.risk_flags


def test_trusted_attachment_line_items_can_replace_review_keyword_for_classification():
    evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Trusted Seller",
                normalized_value="TrustedSeller",
                confidence=0.95,
            ),
            FieldCandidate(
                field_name="invoice_amount",
                value="100.00",
                normalized_value="100.00",
                confidence=0.93,
            ),
        ],
        table_lines=[{"text": "详见销货清单"}],
        overall=0.96,
    )
    attachment_evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Trusted Seller",
                normalized_value="TrustedSeller",
                confidence=0.95,
            ),
        ],
        table_lines=[{"text": "Office Supplies"}],
        overall=0.97,
    )

    result = classify_risk(
        evidence=evidence,
        attachment_evidence=attachment_evidence,
        business_rules={
            "minimum_confidence": 0.75,
            "review_keywords": ["详见销货清单"],
            "seller_whitelist": ["TrustedSeller"],
        },
    )

    assert result.decision == "suggested_pass"
    assert result.risk_flags == []
    assert "seller_whitelist" in result.matched_rules


def test_attachment_evidence_does_not_override_low_confidence_review():
    evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Trusted Seller",
                normalized_value="TrustedSeller",
                confidence=0.90,
            ),
            FieldCandidate(
                field_name="invoice_amount",
                value="100.00",
                normalized_value="100.00",
                confidence=0.55,
            ),
        ],
        table_lines=[{"text": "详见销货清单"}],
        overall=0.62,
        flags=["low_confidence"],
    )
    attachment_evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Trusted Seller",
                normalized_value="TrustedSeller",
                confidence=0.97,
            ),
        ],
        table_lines=[{"text": "Office Supplies"}],
        overall=0.97,
    )

    result = classify_risk(
        evidence=evidence,
        attachment_evidence=attachment_evidence,
        business_rules={
            "minimum_confidence": 0.75,
            "review_keywords": ["详见销货清单"],
            "seller_whitelist": ["TrustedSeller"],
        },
    )

    assert result.decision == "review_required"
    assert "low_confidence" in result.risk_flags


def test_attachment_evidence_is_ignored_without_review_keyword_trigger():
    evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Neutral Seller",
                normalized_value="NeutralSeller",
                confidence=0.95,
            ),
        ],
        table_lines=[{"text": "Regular Line"}],
        overall=0.96,
    )
    attachment_evidence = build_evidence(
        field_candidates=[
            FieldCandidate(
                field_name="seller_name",
                value="Neutral Seller",
                normalized_value="NeutralSeller",
                confidence=0.97,
            ),
        ],
        table_lines=[{"text": "Office Supplies"}],
        overall=0.97,
    )

    result = classify_risk(
        evidence=evidence,
        attachment_evidence=attachment_evidence,
        business_rules={
            "minimum_confidence": 0.75,
            "review_keywords": ["详见销货清单"],
            "pass_keywords": ["Office Supplies"],
        },
    )

    assert result.decision == "review_required"
    assert result.risk_flags == ["no_whitelist_match"]


def test_duplicate_invoice_is_flagged_and_excluded_from_suggested_pass_totals():
    duplicate = detect_suspected_duplicate(
        invoice_data={
            "invoice_number": "12345678",
            "invoice_code": "031001",
            "invoice_date": date(2026, 4, 17),
            "invoice_amount": Decimal("88.00"),
            "seller_name": "Trusted Seller",
            "system_decision": "suggested_pass",
            "risk_flags": [],
        },
        history=[
            {
                "invoice_number": "12345678",
                "invoice_code": "031001",
                "invoice_date": date(2026, 4, 17),
                "invoice_amount": Decimal("88.00"),
                "seller_name": "Trusted Seller",
            }
        ],
    )

    assert duplicate.duplicate_flag is True
    assert duplicate.decision == "review_required"
    assert "suspected_duplicate" in duplicate.risk_flags

    summary = summarize_suggested_pass(
        [
            SimpleNamespace(
                processing_status="completed",
                system_decision="suggested_pass",
                duplicate_flag=False,
                invoice_amount=Decimal("100.00"),
            ),
            SimpleNamespace(
                processing_status="completed",
                system_decision=duplicate.decision,
                duplicate_flag=duplicate.duplicate_flag,
                invoice_amount=Decimal("88.00"),
            ),
        ]
    )

    assert summary.count == 1
    assert summary.total_amount == Decimal("100.00")
