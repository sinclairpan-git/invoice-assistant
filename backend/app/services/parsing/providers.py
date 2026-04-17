from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.app.services.parsing.evidence_models import (
    ConfidenceSummary,
    EvidenceAdapterError,
    FieldCandidate,
    StructuredParseError,
    TextBlock,
    UnifiedDocumentEvidence,
)


def adapt_text_extraction(payload: Mapping[str, Any]) -> UnifiedDocumentEvidence:
    return _adapt_payload(payload, source_type="text")


def adapt_ocr_output(payload: Mapping[str, Any]) -> UnifiedDocumentEvidence:
    return _adapt_payload(payload, source_type="ocr")


def _adapt_payload(payload: Mapping[str, Any], *, source_type: str) -> UnifiedDocumentEvidence:
    provider_name = str(payload.get("provider_name") or "").strip()
    provider_version = str(payload.get("provider_version") or "unknown").strip()
    raw_text = str(payload.get("raw_text") or payload.get("text") or "").strip()

    if not provider_name:
        raise EvidenceAdapterError(
            _structured_error(
                code="missing_provider_name",
                message="Provider name is required for evidence adaptation.",
                provider_name="unknown",
                provider_version=provider_version,
                source_type=source_type,
            )
        )
    if not raw_text:
        raise EvidenceAdapterError(
            _structured_error(
                code="missing_raw_text",
                message="Raw text is required for evidence adaptation.",
                provider_name=provider_name,
                provider_version=provider_version,
                source_type=source_type,
            )
        )

    pages = _coerce_dict_list(payload.get("pages"))
    text_blocks = _coerce_text_blocks(payload.get("text_blocks"))
    table_lines = _coerce_dict_list(payload.get("table_lines") or payload.get("tables"))
    field_candidates = _coerce_field_candidates(payload.get("field_candidates") or payload.get("fields"))
    confidence_summary = _coerce_confidence_summary(payload.get("confidence_summary"), field_candidates)

    return UnifiedDocumentEvidence(
        source_type=source_type,
        raw_text=raw_text,
        pages=pages,
        text_blocks=text_blocks,
        table_lines=table_lines,
        field_candidates=field_candidates,
        confidence_summary=confidence_summary,
        provider_name=provider_name,
        provider_version=provider_version,
        provider_error_code=payload.get("provider_error_code"),
    )


def _coerce_dict_list(raw_value: Any) -> list[dict[str, object]]:
    if raw_value in (None, ""):
        return []
    if not isinstance(raw_value, list):
        return []
    normalized: list[dict[str, object]] = []
    for item in raw_value:
        if isinstance(item, Mapping):
            normalized.append(dict(item))
    return normalized


def _coerce_text_blocks(raw_value: Any) -> list[TextBlock]:
    return [TextBlock.model_validate(item) for item in _coerce_dict_list(raw_value)]


def _coerce_field_candidates(raw_value: Any) -> list[FieldCandidate]:
    candidates: list[FieldCandidate] = []
    if raw_value in (None, ""):
        return candidates

    if isinstance(raw_value, Mapping):
        for field_name, value in raw_value.items():
            if isinstance(value, list):
                for item in value:
                    candidates.append(_build_candidate(field_name, item))
            else:
                candidates.append(_build_candidate(field_name, value))
        return candidates

    if isinstance(raw_value, list):
        for item in raw_value:
            if isinstance(item, Mapping):
                field_name = str(item.get("field_name") or "").strip()
                if field_name:
                    candidates.append(FieldCandidate.model_validate(item))
        return candidates

    return candidates


def _build_candidate(field_name: str, raw_value: Any) -> FieldCandidate:
    if isinstance(raw_value, Mapping):
        payload = dict(raw_value)
        payload.setdefault("field_name", field_name)
        payload.setdefault("value", payload.get("normalized_value") or "")
        payload.setdefault("normalized_value", _normalize_value(str(payload.get("value") or "")))
        payload.setdefault("confidence", 0.0)
        payload.setdefault("metadata", {})
        return FieldCandidate.model_validate(payload)
    value = str(raw_value or "")
    return FieldCandidate(
        field_name=field_name,
        value=value,
        normalized_value=_normalize_value(value),
        confidence=0.0,
    )


def _coerce_confidence_summary(raw_value: Any, field_candidates: list[FieldCandidate]) -> ConfidenceSummary:
    if isinstance(raw_value, Mapping):
        payload = dict(raw_value)
        payload.setdefault("fields", {})
        payload.setdefault("flags", [])
        return ConfidenceSummary.model_validate(payload)

    field_confidences: dict[str, float] = {}
    for candidate in field_candidates:
        field_confidences[candidate.field_name] = max(
            candidate.confidence,
            field_confidences.get(candidate.field_name, 0.0),
        )
    if field_candidates:
        overall = sum(candidate.confidence for candidate in field_candidates) / len(field_candidates)
    else:
        overall = 0.0
    return ConfidenceSummary(overall=overall, fields=field_confidences, flags=[])


def _structured_error(
    *,
    code: str,
    message: str,
    provider_name: str,
    provider_version: str,
    source_type: str,
) -> StructuredParseError:
    return StructuredParseError(
        code=code,
        message=message,
        provider_name=provider_name,
        provider_version=provider_version,
        source_type=source_type,
    )


def _normalize_value(value: str) -> str:
    return "".join(value.split()).strip()
