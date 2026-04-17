from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models import DocumentEvidence


class TextBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")

    page_no: int = 1
    text: str
    bbox_json: dict[str, float] | None = None


class FieldCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field_name: str
    value: str
    normalized_value: str | None = None
    confidence: float = 0.0
    page_no: int | None = None
    source_fragment: str | None = None
    bbox_json: dict[str, float] | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ConfidenceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall: float = 0.0
    fields: dict[str, float] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)


class StructuredParseError(BaseModel):
    code: str
    message: str
    provider_name: str
    provider_version: str
    source_type: Literal["text", "ocr"]
    details: dict[str, object] = Field(default_factory=dict)


class EvidenceAdapterError(ValueError):
    def __init__(self, error: StructuredParseError) -> None:
        super().__init__(error.message)
        self.error = error

    def to_dict(self) -> dict[str, object]:
        return self.error.model_dump()


class UnifiedDocumentEvidence(BaseModel):
    source_type: Literal["text", "ocr"]
    raw_text: str | None = None
    pages: list[dict[str, object]] = Field(default_factory=list)
    text_blocks: list[TextBlock] = Field(default_factory=list)
    table_lines: list[dict[str, object]] = Field(default_factory=list)
    field_candidates: list[FieldCandidate] = Field(default_factory=list)
    confidence_summary: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
    provider_name: str
    provider_version: str
    provider_error_code: str | None = None

    def best_candidate(self, field_name: str) -> FieldCandidate | None:
        candidates = [candidate for candidate in self.field_candidates if candidate.field_name == field_name]
        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate.confidence)

    def to_record(self, invoice_id: str) -> DocumentEvidence:
        return DocumentEvidence(
            invoice_id=invoice_id,
            source_type=self.source_type,
            raw_text=self.raw_text,
            pages_json=json.dumps(self.pages, sort_keys=True),
            text_blocks_json=json.dumps([block.model_dump(mode="json") for block in self.text_blocks], sort_keys=True),
            table_lines_json=json.dumps(self.table_lines, sort_keys=True),
            field_candidates_json=json.dumps(
                [candidate.model_dump(mode="json") for candidate in self.field_candidates],
                sort_keys=True,
            ),
            confidence_summary_json=json.dumps(self.confidence_summary.model_dump(mode="json"), sort_keys=True),
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            provider_error_code=self.provider_error_code,
        )
