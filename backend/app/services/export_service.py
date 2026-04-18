from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from logging import Logger
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_app_logger, log_event
from backend.app.db.models import (
    AttachmentDocument,
    AuditLog,
    Batch,
    ExportJob,
    InvoiceRecord,
)
from backend.app.services.compliance_service import (
    build_invoice_compliance_summary,
    summarize_archiveable_pass,
)
from backend.app.services.status_service import derive_display_status


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "storage"
SUPPORTED_EXPORT_TYPES = {"suggested_pass_zip", "issue_zip", "excel_manifest"}
TERMINAL_BATCH_STATUSES = {"completed", "completed_with_failures", "failed"}
ATTACHMENT_STATUS_LABELS = {
    "pending_match": "待匹配",
    "matched": "已匹配",
    "consumed": "已消费",
    "ambiguous": "匹配歧义",
    "unmatched": "未匹配",
    "parse_failed": "解析失败",
}


@dataclass(frozen=True)
class ExportResult:
    job_id: str
    export_type: str
    status: str
    output_path: str
    summary: dict[str, object]


class ExportService:
    def __init__(
        self,
        session: Session,
        *,
        storage_root: Path | str = DEFAULT_STORAGE_ROOT,
        logger: Logger | None = None,
    ) -> None:
        self.session = session
        self.storage_root = Path(storage_root)
        self.logger = logger or get_app_logger("export")

    def create_export(
        self,
        *,
        batch_id: str,
        export_type: str,
        created_by: str,
        actor_roles: tuple[str, ...] | list[str] = (),
    ) -> ExportResult:
        if export_type not in SUPPORTED_EXPORT_TYPES:
            raise ValueError(f"Unsupported export type: {export_type!r}")

        batch = self.session.get(Batch, batch_id)
        if batch is None:
            raise LookupError(f"Batch {batch_id!r} not found.")

        invoices = self.session.scalars(
            select(InvoiceRecord)
            .where(InvoiceRecord.batch_id == batch_id)
            .order_by(InvoiceRecord.original_filename.asc())
        ).all()

        gate_failure = self._validate_export_gate(
            batch=batch, invoices=invoices, export_type=export_type
        )
        if gate_failure is not None:
            self._record_audit(
                entity_id=batch.id,
                action="export_denied",
                changed_by=created_by,
                change_summary=f"export_type={export_type}",
                change_reason=gate_failure,
                payload=self._with_actor_roles(
                    actor_roles,
                    {
                        "batch_id": batch.id,
                        "export_type": export_type,
                        "gate": {
                            "allowed": False,
                            "reasons": [gate_failure],
                        },
                    },
                ),
            )
            self.session.commit()
            raise ValueError(
                self._gate_failure_message(
                    export_type=export_type, gate_failure=gate_failure
                )
            )

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        export_dir = self.storage_root / "exports" / batch.batch_no
        export_dir.mkdir(parents=True, exist_ok=True)

        if export_type == "excel_manifest":
            output_file = export_dir / f"{export_type}_{timestamp}.xlsx"
        else:
            output_file = export_dir / f"{export_type}_{timestamp}.zip"

        selected_invoices = self._select_invoices(
            export_type=export_type, invoices=invoices
        )

        try:
            if export_type == "excel_manifest":
                self._write_excel_manifest(output_file, batch=batch, invoices=invoices)
            else:
                self._write_zip(output_file, invoices=selected_invoices)

            summary = self._build_summary(
                export_type=export_type,
                selected_invoices=selected_invoices,
                all_invoices=invoices,
            )
            relative_output = self._relative_output_path(output_file)
            job = ExportJob(
                batch_id=batch.id,
                export_type=export_type,
                status="completed",
                output_path=relative_output,
                created_by=created_by,
                summary_json=json.dumps(summary, ensure_ascii=False, sort_keys=True),
            )
            self.session.add(job)
            self.session.flush()

            self._record_audit(
                entity_id=job.id,
                action="export_completed",
                changed_by=created_by,
                change_summary=f"export_type={export_type}",
                change_reason="export gate passed",
                payload=self._with_actor_roles(
                    actor_roles,
                    {
                        "batch_id": batch.id,
                        "job_id": job.id,
                        "export_type": export_type,
                        "output_path": relative_output,
                        "summary": summary,
                        "gate": {
                            "allowed": True,
                            "reasons": [],
                        },
                    },
                ),
            )

            if export_type == "excel_manifest":
                batch.export_manifest_path = relative_output

            self.session.commit()
            self.session.refresh(job)

            log_event(
                self.logger,
                "export_completed",
                batch_id=batch.id,
                export_type=export_type,
                output_path=relative_output,
                summary=summary,
            )
            return ExportResult(
                job_id=job.id,
                export_type=job.export_type,
                status=job.status,
                output_path=relative_output,
                summary=summary,
            )
        except Exception as exc:
            if output_file.exists():
                output_file.unlink()
            job = ExportJob(
                batch_id=batch.id,
                export_type=export_type,
                status="failed",
                output_path=None,
                created_by=created_by,
                summary_json=json.dumps(
                    {"error": str(exc)}, ensure_ascii=False, sort_keys=True
                ),
            )
            self.session.add(job)
            self.session.flush()
            self._record_audit(
                entity_id=job.id,
                action="export_failed",
                changed_by=created_by,
                change_summary=f"export_type={export_type}",
                change_reason=str(exc),
                payload=self._with_actor_roles(
                    actor_roles,
                    {
                        "batch_id": batch.id,
                        "job_id": job.id,
                        "export_type": export_type,
                        "error": str(exc),
                        "gate": {
                            "allowed": True,
                            "reasons": [],
                        },
                    },
                ),
            )
            self.session.commit()
            log_event(
                self.logger,
                "export_failed",
                batch_id=batch.id,
                export_type=export_type,
                error=str(exc),
            )
            raise

    @staticmethod
    def _select_invoices(
        *, export_type: str, invoices: list[InvoiceRecord]
    ) -> list[InvoiceRecord]:
        if export_type == "suggested_pass_zip":
            return [
                invoice
                for invoice in invoices
                if build_invoice_compliance_summary(invoice).archiveable_pass
            ]
        if export_type == "issue_zip":
            return [
                invoice
                for invoice in invoices
                if not build_invoice_compliance_summary(invoice).archiveable_pass
            ]
        return invoices

    @staticmethod
    def _build_summary(
        *,
        export_type: str,
        selected_invoices: list[InvoiceRecord],
        all_invoices: list[InvoiceRecord],
    ) -> dict[str, object]:
        if export_type == "suggested_pass_zip":
            summary = summarize_archiveable_pass(selected_invoices)
            return {
                "record_count": summary.count,
                "total_amount": f"{summary.total_amount:.2f}",
            }
        if export_type == "issue_zip":
            issue_amount = Decimal("0.00")
            for invoice in selected_invoices:
                if invoice.invoice_amount is not None:
                    issue_amount += Decimal(str(invoice.invoice_amount))
            return {
                "record_count": len(selected_invoices),
                "total_amount": f"{issue_amount.quantize(Decimal('0.01')):.2f}",
            }

        batch_summary = summarize_archiveable_pass(all_invoices)
        return {
            "record_count": len(all_invoices),
            "suggested_pass_count": batch_summary.count,
            "suggested_pass_total_amount": f"{batch_summary.total_amount:.2f}",
        }

    def _write_zip(self, output_file: Path, *, invoices: list[InvoiceRecord]) -> None:
        with ZipFile(output_file, "w", compression=ZIP_DEFLATED) as archive:
            for invoice in invoices:
                source_path = self._resolve_source_path(invoice)
                archive_name = invoice.renamed_filename or invoice.original_filename
                archive.write(source_path, arcname=archive_name)

    def _write_excel_manifest(
        self, output_file: Path, *, batch: Batch, invoices: list[InvoiceRecord]
    ) -> None:
        headers = [
            "批次号",
            "原文件名",
            "重命名文件名",
            "显示状态",
            "系统判定",
            "人工复核状态",
            "基础合规",
            "业务合规",
            "最终结论",
            "结论原因",
            "建议动作",
            "金额",
            "发票号码",
            "购方名称",
            "风险标记",
            "失败原因",
            "清单附件",
            "附件识别",
            "附件匹配依据",
        ]
        rows: list[list[str]] = [headers]
        attachments_by_invoice = self._group_attachments_by_invoice(batch)

        for invoice in invoices:
            display_status = derive_display_status(
                processing_status=invoice.processing_status,
                system_decision=invoice.system_decision,
                duplicate_flag=invoice.duplicate_flag,
            )
            compliance = build_invoice_compliance_summary(invoice)
            attachments = attachments_by_invoice.get(invoice.id, [])
            rows.append(
                [
                    batch.batch_no,
                    invoice.original_filename,
                    invoice.renamed_filename or "",
                    display_status,
                    invoice.system_decision or "",
                    invoice.review_status,
                    compliance.basic_compliance_status,
                    compliance.business_compliance_status,
                    compliance.final_decision,
                    "；".join(compliance.decision_reasons),
                    "；".join(compliance.suggested_actions),
                    ""
                    if invoice.invoice_amount is None
                    else f"{Decimal(str(invoice.invoice_amount)):.2f}",
                    invoice.invoice_number or "",
                    invoice.buyer_name or "",
                    ",".join(json.loads(invoice.risk_flags or "[]")),
                    invoice.failure_reason or "",
                    "；".join(
                        attachment.original_filename for attachment in attachments
                    ),
                    "；".join(
                        ATTACHMENT_STATUS_LABELS.get(
                            attachment.attachment_status, attachment.attachment_status
                        )
                        for attachment in attachments
                    ),
                    "；".join(
                        attachment.match_reason or "" for attachment in attachments
                    ),
                ]
            )

        self._write_simple_xlsx(output_file, sheet_name="批次台账", rows=rows)

    @staticmethod
    def _group_attachments_by_invoice(
        batch: Batch,
    ) -> dict[str, list[AttachmentDocument]]:
        grouped: dict[str, list[AttachmentDocument]] = {}
        for attachment in batch.attachment_documents:
            if not attachment.matched_invoice_id:
                continue
            grouped.setdefault(attachment.matched_invoice_id, []).append(attachment)
        for items in grouped.values():
            items.sort(key=lambda item: item.original_filename)
        return grouped

    def _write_simple_xlsx(
        self, output_file: Path, *, sheet_name: str, rows: list[list[str]]
    ) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                cell_ref = f"{self._column_letter(col_index)}{row_index}"
                text = escape(value or "")
                cells.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'
                )
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(sheet_rows)}</sheetData>"
            "</worksheet>"
        )
        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>"
        )
        workbook_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        )
        root_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )
        content_types_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        )

        with ZipFile(output_file, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types_xml)
            archive.writestr("_rels/.rels", root_rels_xml)
            archive.writestr("xl/workbook.xml", workbook_xml)
            archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
            archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    def _resolve_source_path(self, invoice: InvoiceRecord) -> Path:
        candidate = invoice.storage_path_renamed or invoice.storage_path_original
        path = Path(candidate)
        if path.is_absolute():
            return path
        return (self.storage_root.parent / path).resolve()

    def _relative_output_path(self, output_file: Path) -> str:
        try:
            return output_file.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return str(output_file)

    def _validate_export_gate(
        self, *, batch: Batch, invoices: list[InvoiceRecord], export_type: str
    ) -> str | None:
        is_terminal = (
            batch.status in TERMINAL_BATCH_STATUSES
            and batch.total_files > 0
            and batch.processing_files == 0
            and batch.completed_files + batch.failed_files == batch.total_files
        )
        if not is_terminal:
            return "batch_not_terminal"

        if export_type == "suggested_pass_zip" and any(
            build_invoice_compliance_summary(invoice).pending_review_gate
            for invoice in invoices
        ):
            return "pending_manual_review"

        return None

    @staticmethod
    def _gate_failure_message(*, export_type: str, gate_failure: str) -> str:
        if gate_failure == "batch_not_terminal":
            return "当前批次尚未处理完成，暂不允许导出。"
        if (
            gate_failure == "pending_manual_review"
            and export_type == "suggested_pass_zip"
        ):
            return "当前批次仍有待复核票据，无法导出建议通过 ZIP。"
        return "当前导出请求未通过门槛校验。"

    def _record_audit(
        self,
        *,
        entity_id: str,
        action: str,
        changed_by: str,
        change_summary: str,
        change_reason: str,
        payload: dict[str, object],
    ) -> None:
        self.session.add(
            AuditLog(
                entity_type="export_job",
                entity_id=entity_id,
                action=action,
                changed_by=changed_by,
                change_summary=change_summary,
                change_reason=change_reason,
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
        )

    @staticmethod
    def _with_actor_roles(
        actor_roles: tuple[str, ...] | list[str], payload: dict[str, object]
    ) -> dict[str, object]:
        if actor_roles:
            payload = dict(payload)
            payload["actor_roles"] = list(actor_roles)
        return payload

    @staticmethod
    def _column_letter(index: int) -> str:
        letters = []
        current = index
        while current > 0:
            current, remainder = divmod(current - 1, 26)
            letters.append(chr(65 + remainder))
        return "".join(reversed(letters))
