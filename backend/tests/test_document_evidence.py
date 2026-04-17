import json

import pytest

from backend.app.services.parsing.evidence_models import EvidenceAdapterError
from backend.app.services.parsing.providers import adapt_ocr_output, adapt_text_extraction


def test_text_extraction_payload_adapts_to_unified_document_evidence():
    evidence = adapt_text_extraction(
        {
            "provider_name": "pdfminer",
            "provider_version": "2026.4",
            "raw_text": "Buyer: Shanghai Example",
            "pages": [{"page_no": 1, "char_count": 120}],
            "text_blocks": [{"page_no": 1, "text": "Buyer: Shanghai Example"}],
            "field_candidates": {
                "buyer_name": {
                    "value": "Shanghai Example",
                    "confidence": 0.97,
                    "page_no": 1,
                    "source_fragment": "Buyer: Shanghai Example",
                }
            },
            "confidence_summary": {"overall": 0.95, "fields": {"buyer_name": 0.97}},
        }
    )

    assert evidence.source_type == "text"
    assert evidence.provider_name == "pdfminer"
    assert evidence.best_candidate("buyer_name").confidence == 0.97

    record = evidence.to_record("invoice-1")
    assert record.source_type == "text"
    assert json.loads(record.field_candidates_json)[0]["field_name"] == "buyer_name"


def test_ocr_payload_adapts_to_unified_document_evidence():
    evidence = adapt_ocr_output(
        {
            "provider_name": "paddleocr",
            "provider_version": "3.0",
            "text": "Invoice No: 12345678",
            "text_blocks": [{"page_no": 1, "text": "Invoice No: 12345678", "bbox_json": {"x0": 1, "y0": 2}}],
            "table_lines": [{"text": "Consulting Service", "row_no": 1}],
            "field_candidates": [
                {"field_name": "invoice_number", "value": "12345678", "normalized_value": "12345678", "confidence": 0.88}
            ],
        }
    )

    assert evidence.source_type == "ocr"
    assert evidence.provider_name == "paddleocr"
    assert evidence.best_candidate("invoice_number").normalized_value == "12345678"
    assert evidence.confidence_summary.overall == pytest.approx(0.88)


def test_missing_raw_text_raises_structured_error():
    with pytest.raises(EvidenceAdapterError) as exc_info:
        adapt_text_extraction({"provider_name": "pdfminer", "provider_version": "2026.4"})

    error = exc_info.value.to_dict()
    assert error["code"] == "missing_raw_text"
    assert error["provider_name"] == "pdfminer"
    assert error["source_type"] == "text"
