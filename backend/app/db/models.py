from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suggested_pass_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suggested_pass_total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    tax_profile_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rule_versions.id"), nullable=True
    )
    business_rule_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rule_versions.id"), nullable=True
    )
    naming_rule_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rule_versions.id"), nullable=True
    )
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    export_manifest_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    invoices: Mapped[list["InvoiceRecord"]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class InvoiceRecord(Base):
    __tablename__ = "invoice_records"
    __table_args__ = (UniqueConstraint("batch_id", "original_filename", name="uq_invoice_batch_original_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("batches.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    renamed_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path_original: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path_renamed: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invoice_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    buyer_tax_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    parse_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    system_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    artifact_status: Mapped[str] = mapped_column(String(32), nullable=False, default="original_only")
    duplicate_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_group_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    risk_flags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    display_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    problem_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped[Batch] = relationship(back_populates="invoices")
    evidence_items: Mapped[list["DocumentEvidence"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    field_checks: Mapped[list["FieldCheck"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class DocumentEvidence(Base):
    __tablename__ = "document_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoice_records.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    text_blocks_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    table_lines_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    field_candidates_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    confidence_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    provider_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    invoice: Mapped[InvoiceRecord] = relationship(back_populates="evidence_items")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoice_records.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extracted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_fragment: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped[InvoiceRecord] = relationship(back_populates="extracted_fields")


class FieldCheck(Base):
    __tablename__ = "field_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoice_records.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_result: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    invoice: Mapped[InvoiceRecord] = relationship(back_populates="field_checks")


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (UniqueConstraint("kind", "version_no", name="uq_rule_kind_version_no"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version_no: Mapped[str] = mapped_column(String(32), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    change_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=False)


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(String(36), ForeignKey("invoice_records.id"), nullable=False, index=True)
    review_action: Mapped[str] = mapped_column(String(64), nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    invoice: Mapped[InvoiceRecord] = relationship(back_populates="review_actions")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("batches.id"), nullable=False, index=True)
    export_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    batch: Mapped[Batch] = relationship(back_populates="export_jobs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    change_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
