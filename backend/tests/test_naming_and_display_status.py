from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from backend.app.services.naming_service import (
    DEFAULT_NAMING_TEMPLATE,
    build_renamed_filename,
)
from backend.app.services.status_service import (
    BUSINESS_BUCKET_BATCH_DUPLICATE,
    BUSINESS_BUCKET_NEEDS_ATTENTION,
    BUSINESS_BUCKET_PENDING_REVIEW,
    BUSINESS_BUCKET_SUGGESTED_PASS,
    DISPLAY_STATUS_DUPLICATE,
    DISPLAY_STATUS_FAILED,
    DISPLAY_STATUS_PASS,
    DISPLAY_STATUS_PROCESSING,
    DISPLAY_STATUS_REJECT,
    DISPLAY_STATUS_REVIEW,
    derive_business_bucket,
    derive_display_status,
    derive_stable_status,
    summarize_business_buckets,
    summarize_suggested_pass,
)


def test_default_naming_template_uses_date_amount_and_invoice_number():
    result = build_renamed_filename(
        invoice_date=date(2026, 4, 17),
        invoice_amount=Decimal("123.45"),
        invoice_number="A123456789",
        template=DEFAULT_NAMING_TEMPLATE,
    )

    assert result.renamed_filename == "20260417_123.45_A123456789.pdf"
    assert result.reason is None


def test_missing_key_fields_skip_rename_with_reason():
    result = build_renamed_filename(
        invoice_date=None,
        invoice_amount=Decimal("123.45"),
        invoice_number="A123456789",
    )

    assert result.renamed_filename is None
    assert result.reason == "Missing required rename fields: invoice_date"


def test_display_status_priority_matches_spec():
    assert (
        derive_display_status(
            processing_status="processing_failed",
            system_decision="suggested_pass",
            duplicate_flag=False,
        )
        == DISPLAY_STATUS_FAILED
    )
    assert (
        derive_display_status(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=True,
        )
        == DISPLAY_STATUS_DUPLICATE
    )
    assert (
        derive_display_status(
            processing_status="queued",
            system_decision=None,
            duplicate_flag=False,
        )
        == DISPLAY_STATUS_PROCESSING
    )
    assert (
        derive_display_status(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
            review_status="manually_approved",
        )
        == DISPLAY_STATUS_PASS
    )
    assert (
        derive_display_status(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=False,
            review_status="manually_rejected",
        )
        == DISPLAY_STATUS_REJECT
    )
    assert (
        derive_display_status(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
        )
        == DISPLAY_STATUS_REVIEW
    )
    assert (
        derive_display_status(
            processing_status="completed",
            system_decision="suggested_reject",
            duplicate_flag=False,
        )
        == DISPLAY_STATUS_REJECT
    )
    assert (
        derive_display_status(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=False,
        )
        == DISPLAY_STATUS_PASS
    )


def test_stable_status_and_business_bucket_follow_canonical_contract():
    review_invoice = derive_stable_status(
        processing_status="completed",
        system_decision="review_required",
        duplicate_flag=False,
        review_status="not_reviewed",
    )
    assert review_invoice.to_dict() == {
        "processing_status": "completed",
        "review_status": "pending",
        "archive_status": "not_ready",
    }
    assert (
        derive_business_bucket(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
            review_status="not_reviewed",
        )
        == BUSINESS_BUCKET_PENDING_REVIEW
    )

    duplicate_invoice = derive_stable_status(
        processing_status="completed",
        system_decision="suggested_pass",
        duplicate_flag=True,
        review_status="not_reviewed",
    )
    assert duplicate_invoice.to_dict() == {
        "processing_status": "completed",
        "review_status": "pending",
        "archive_status": "not_ready",
    }
    assert (
        derive_business_bucket(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=True,
            review_status="not_reviewed",
        )
        == BUSINESS_BUCKET_BATCH_DUPLICATE
    )

    approved_invoice = derive_stable_status(
        processing_status="completed",
        system_decision="review_required",
        duplicate_flag=False,
        review_status="manually_approved",
    )
    assert approved_invoice.to_dict() == {
        "processing_status": "completed",
        "review_status": "approved",
        "archive_status": "ready_to_save",
    }
    assert (
        derive_business_bucket(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
            review_status="manually_approved",
        )
        == BUSINESS_BUCKET_SUGGESTED_PASS
    )

    failed_invoice = derive_stable_status(
        processing_status="processing_failed",
        system_decision=None,
        duplicate_flag=False,
        review_status="not_reviewed",
    )
    assert failed_invoice.to_dict() == {
        "processing_status": "failed",
        "review_status": "not_required",
        "archive_status": "not_ready",
    }
    assert (
        derive_business_bucket(
            processing_status="processing_failed",
            system_decision=None,
            duplicate_flag=False,
            review_status="not_reviewed",
        )
        == BUSINESS_BUCKET_NEEDS_ATTENTION
    )


def test_suggested_pass_summary_supports_total_amount_and_filter_scope():
    records = [
        SimpleNamespace(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=False,
            invoice_amount=Decimal("100.00"),
        ),
        SimpleNamespace(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=True,
            invoice_amount=Decimal("88.00"),
        ),
        SimpleNamespace(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
            invoice_amount=Decimal("66.00"),
        ),
    ]

    batch_summary = summarize_suggested_pass(records)
    filtered_summary = summarize_suggested_pass(
        records, filter_display_status=DISPLAY_STATUS_PASS
    )

    assert batch_summary.count == 1
    assert batch_summary.total_amount == Decimal("100.00")
    assert filtered_summary.count == 1
    assert filtered_summary.total_amount == Decimal("100.00")


def test_suggested_pass_summary_ignores_stale_persisted_display_status():
    records = [
        SimpleNamespace(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
            display_status=DISPLAY_STATUS_PASS,
            invoice_amount=Decimal("120.00"),
        )
    ]

    filtered_summary = summarize_suggested_pass(
        records, filter_display_status=DISPLAY_STATUS_PASS
    )

    assert filtered_summary.count == 0
    assert filtered_summary.total_amount == Decimal("0.00")


def test_business_bucket_summary_uses_canonical_counts():
    records = [
        SimpleNamespace(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=False,
            review_status="not_reviewed",
        ),
        SimpleNamespace(
            processing_status="completed",
            system_decision="review_required",
            duplicate_flag=False,
            review_status="not_reviewed",
        ),
        SimpleNamespace(
            processing_status="completed",
            system_decision="suggested_pass",
            duplicate_flag=True,
            review_status="not_reviewed",
        ),
        SimpleNamespace(
            processing_status="processing_failed",
            system_decision=None,
            duplicate_flag=False,
            review_status="not_reviewed",
        ),
    ]

    summary = summarize_business_buckets(records).to_dict()

    assert summary[BUSINESS_BUCKET_SUGGESTED_PASS]["count"] == 1
    assert summary[BUSINESS_BUCKET_PENDING_REVIEW]["count"] == 1
    assert summary[BUSINESS_BUCKET_BATCH_DUPLICATE]["count"] == 1
    assert summary[BUSINESS_BUCKET_NEEDS_ATTENTION]["count"] == 1
