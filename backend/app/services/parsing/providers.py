from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
from statistics import fmean
from typing import Any, Literal

import pypdfium2
from pypdf import PdfReader
from rapidocr_onnxruntime import RapidOCR

from backend.app.services.parsing.evidence_models import (
    ConfidenceSummary,
    EvidenceAdapterError,
    FieldCandidate,
    StructuredParseError,
    TextBlock,
    UnifiedDocumentEvidence,
)

TEXT_PROVIDER_NAME = "pypdf"
OCR_PROVIDER_NAME = "rapidocr-onnxruntime"
OCR_RENDERER_NAME = "pypdfium2"
TEXT_BASE_CONFIDENCE = 0.94
OCR_LOW_CONFIDENCE_THRESHOLD = 0.75
PDF_RENDER_SCALE = 2.0

_OCR_ENGINE: RapidOCR | None = None


@dataclass(frozen=True)
class ProviderExtractionPayload:
    source_type: Literal["text", "ocr"]
    provider_name: str
    provider_version: str
    raw_text: str
    pages: list[dict[str, object]] = field(default_factory=list)
    text_blocks: list[dict[str, object]] = field(default_factory=list)
    table_lines: list[dict[str, object]] = field(default_factory=list)
    base_confidence: float = 0.0
    confidence_flags: list[str] = field(default_factory=list)
    provider_error_code: str | None = None


def extract_pdf_text(content: bytes) -> ProviderExtractionPayload:
    provider_version = _package_version(TEXT_PROVIDER_NAME)
    try:
        reader = PdfReader(BytesIO(content))
    except Exception as exc:
        raise EvidenceAdapterError(
            _structured_error(
                code="pdf_text_extraction_failed",
                message="PDF text extraction failed before any usable text was produced.",
                provider_name=TEXT_PROVIDER_NAME,
                provider_version=provider_version,
                source_type="text",
                details={"exception_type": type(exc).__name__},
            )
        ) from exc

    pages: list[dict[str, object]] = []
    text_blocks: list[dict[str, object]] = []
    table_lines: list[dict[str, object]] = []
    page_texts: list[str] = []

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception as exc:
            raise EvidenceAdapterError(
                _structured_error(
                    code="pdf_page_text_extraction_failed",
                    message=f"PDF text extraction failed on page {page_no}.",
                    provider_name=TEXT_PROVIDER_NAME,
                    provider_version=provider_version,
                    source_type="text",
                    details={"page_no": page_no, "exception_type": type(exc).__name__},
                )
            ) from exc

        pages.append(
            {
                "page_no": page_no,
                "char_count": len(page_text),
                "text_available": bool(page_text),
            }
        )
        if not page_text:
            continue

        page_texts.append(page_text)
        text_blocks.append({"page_no": page_no, "text": page_text})
        for row_no, line_text in enumerate(_split_lines(page_text), start=1):
            table_lines.append(
                {"page_no": page_no, "row_no": row_no, "text": line_text}
            )

    raw_text = "\n".join(page_texts).strip()
    if not raw_text:
        raise EvidenceAdapterError(
            _structured_error(
                code="pdf_text_empty",
                message="PDF text extraction completed, but no usable text was found.",
                provider_name=TEXT_PROVIDER_NAME,
                provider_version=provider_version,
                source_type="text",
            )
        )

    return ProviderExtractionPayload(
        source_type="text",
        provider_name=TEXT_PROVIDER_NAME,
        provider_version=provider_version,
        raw_text=raw_text,
        pages=pages,
        text_blocks=text_blocks,
        table_lines=table_lines,
        base_confidence=TEXT_BASE_CONFIDENCE,
    )


def extract_local_ocr(content: bytes) -> ProviderExtractionPayload:
    provider_version = f"{_package_version(OCR_PROVIDER_NAME)}+{OCR_RENDERER_NAME}-{_package_version(OCR_RENDERER_NAME)}"
    try:
        document = pypdfium2.PdfDocument(content)
    except Exception as exc:
        raise EvidenceAdapterError(
            _structured_error(
                code="ocr_pdf_render_failed",
                message="Local OCR could not open the PDF for page rendering.",
                provider_name=OCR_PROVIDER_NAME,
                provider_version=provider_version,
                source_type="ocr",
                details={"exception_type": type(exc).__name__},
            )
        ) from exc

    engine = _get_ocr_engine()
    pages: list[dict[str, object]] = []
    text_blocks: list[dict[str, object]] = []
    table_lines: list[dict[str, object]] = []
    page_texts: list[str] = []
    confidences: list[float] = []

    for page_no, page in enumerate(document, start=1):
        try:
            page_image = page.render(scale=PDF_RENDER_SCALE).to_pil()
        except Exception as exc:
            raise EvidenceAdapterError(
                _structured_error(
                    code="ocr_page_render_failed",
                    message=f"Local OCR could not render page {page_no}.",
                    provider_name=OCR_PROVIDER_NAME,
                    provider_version=provider_version,
                    source_type="ocr",
                    details={"page_no": page_no, "exception_type": type(exc).__name__},
                )
            ) from exc

        try:
            ocr_lines, _ = engine(page_image)
        except Exception as exc:
            raise EvidenceAdapterError(
                _structured_error(
                    code="ocr_extraction_failed",
                    message=f"Local OCR failed while recognizing page {page_no}.",
                    provider_name=OCR_PROVIDER_NAME,
                    provider_version=provider_version,
                    source_type="ocr",
                    details={"page_no": page_no, "exception_type": type(exc).__name__},
                )
            ) from exc

        page_line_texts: list[str] = []
        for row_no, raw_line in enumerate(ocr_lines or [], start=1):
            if len(raw_line) != 3:
                continue
            bbox_points, raw_text, confidence = raw_line
            line_text = str(raw_text or "").strip()
            if not line_text:
                continue

            bbox_json = _coerce_bbox(bbox_points)
            confidence_value = float(confidence)
            page_line_texts.append(line_text)
            confidences.append(confidence_value)
            text_blocks.append(
                {"page_no": page_no, "text": line_text, "bbox_json": bbox_json}
            )
            table_lines.append(
                {
                    "page_no": page_no,
                    "row_no": row_no,
                    "text": line_text,
                    "bbox_json": bbox_json,
                    "confidence": confidence_value,
                    "ocr": True,
                }
            )

        page_text = "\n".join(page_line_texts).strip()
        pages.append(
            {
                "page_no": page_no,
                "char_count": len(page_text),
                "ocr_line_count": len(page_line_texts),
            }
        )
        if page_text:
            page_texts.append(page_text)

    raw_text = "\n".join(page_texts).strip()
    if not raw_text:
        raise EvidenceAdapterError(
            _structured_error(
                code="ocr_no_text",
                message="Local OCR finished, but no usable text was recognized.",
                provider_name=OCR_PROVIDER_NAME,
                provider_version=provider_version,
                source_type="ocr",
            )
        )

    overall_confidence = fmean(confidences) if confidences else 0.0
    confidence_flags: list[str] = []
    if overall_confidence < OCR_LOW_CONFIDENCE_THRESHOLD:
        confidence_flags.append("ocr_low_confidence")

    return ProviderExtractionPayload(
        source_type="ocr",
        provider_name=OCR_PROVIDER_NAME,
        provider_version=provider_version,
        raw_text=raw_text,
        pages=pages,
        text_blocks=text_blocks,
        table_lines=table_lines,
        base_confidence=overall_confidence,
        confidence_flags=confidence_flags,
    )


def adapt_text_extraction(payload: Mapping[str, Any]) -> UnifiedDocumentEvidence:
    return _adapt_payload(payload, source_type="text")


def adapt_ocr_output(payload: Mapping[str, Any]) -> UnifiedDocumentEvidence:
    return _adapt_payload(payload, source_type="ocr")


def _adapt_payload(
    payload: Mapping[str, Any], *, source_type: str
) -> UnifiedDocumentEvidence:
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
    field_candidates = _coerce_field_candidates(
        payload.get("field_candidates") or payload.get("fields")
    )
    confidence_summary = _coerce_confidence_summary(
        payload.get("confidence_summary"), field_candidates
    )

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
        payload.setdefault(
            "normalized_value", _normalize_value(str(payload.get("value") or ""))
        )
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


def _coerce_confidence_summary(
    raw_value: Any, field_candidates: list[FieldCandidate]
) -> ConfidenceSummary:
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
        overall = sum(candidate.confidence for candidate in field_candidates) / len(
            field_candidates
        )
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
    details: dict[str, object] | None = None,
) -> StructuredParseError:
    return StructuredParseError(
        code=code,
        message=message,
        provider_name=provider_name,
        provider_version=provider_version,
        source_type=source_type,
        details=details or {},
    )


def _normalize_value(value: str) -> str:
    return "".join(value.split()).strip()


def _split_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def _coerce_bbox(raw_bbox: Any) -> dict[str, float] | None:
    if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
        return None
    x_values: list[float] = []
    y_values: list[float] = []
    for point in raw_bbox:
        if not isinstance(point, list) or len(point) != 2:
            return None
        x_values.append(float(point[0]))
        y_values.append(float(point[1]))
    return {
        "x0": min(x_values),
        "y0": min(y_values),
        "x1": max(x_values),
        "y1": max(y_values),
    }


def _get_ocr_engine() -> RapidOCR:
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE
