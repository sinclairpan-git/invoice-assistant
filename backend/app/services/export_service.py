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
from backend.app.db.models import Batch, ExportJob, InvoiceRecord
from backend.app.services.status_service import DISPLAY_STATUS_PASS, derive_display_status, summarize_suggested_pass


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "storage"
SUPPORTED_EXPORT_TYPES = {"suggested_pass_zip", "issue_zip", "excel_manifest"}


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

    def create_export(self, *, batch_id: str, export_type: str, created_by: str) -> ExportResult:
        if export_type not in SUPPORTED_EXPORT_TYPES:
            raise ValueError(f"Unsupported export type: {export_type!r}")

        batch = self.session.get(Batch, batch_id)
        if batch is None:
            raise LookupError(f"Batch {batch_id!r} not found.")

        invoices = self.session.scalars(
            select(InvoiceRecord).where(InvoiceRecord.batch_id == batch_id).order_by(InvoiceRecord.original_filename.asc())
        ).all()

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        export_dir = self.storage_root / "exports" / batch.batch_no
        export_dir.mkdir(parents=True, exist_ok=True)

        if export_type == "excel_manifest":
            output_file = export_dir / f"{export_type}_{timestamp}.xlsx"
        else:
            output_file = export_dir / f"{export_type}_{timestamp}.zip"

        selected_invoices = self._select_invoices(export_type=export_type, invoices=invoices)

        try:
            if export_type == "excel_manifest":
                self._write_excel_manifest(output_file, batch=batch, invoices=invoices)
            else:
                self._write_zip(output_file, invoices=selected_invoices)

            summary = self._build_summary(export_type=export_type, selected_invoices=selected_invoices, all_invoices=invoices)
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
                summary_json=json.dumps({"error": str(exc)}, ensure_ascii=False, sort_keys=True),
            )
            self.session.add(job)
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
    def _select_invoices(*, export_type: str, invoices: list[InvoiceRecord]) -> list[InvoiceRecord]:
        if export_type == "suggested_pass_zip":
            return [
                invoice
                for invoice in invoices
                if invoice.system_decision == "suggested_pass" and not invoice.duplicate_flag
            ]
        if export_type == "issue_zip":
            return [
                invoice
                for invoice in invoices
                if derive_display_status(
                    processing_status=invoice.processing_status,
                    system_decision=invoice.system_decision,
                    duplicate_flag=invoice.duplicate_flag,
                )
                != DISPLAY_STATUS_PASS
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
            summary = summarize_suggested_pass(selected_invoices)
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

        batch_summary = summarize_suggested_pass(all_invoices)
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

    def _write_excel_manifest(self, output_file: Path, *, batch: Batch, invoices: list[InvoiceRecord]) -> None:
        headers = [
            "批次号",
            "原文件名",
            "重命名文件名",
            "显示状态",
            "系统判定",
            "人工复核状态",
            "金额",
            "发票号码",
            "购方名称",
            "风险标记",
            "失败原因",
        ]
        rows: list[list[str]] = [headers]

        for invoice in invoices:
            display_status = derive_display_status(
                processing_status=invoice.processing_status,
                system_decision=invoice.system_decision,
                duplicate_flag=invoice.duplicate_flag,
            )
            rows.append(
                [
                    batch.batch_no,
                    invoice.original_filename,
                    invoice.renamed_filename or "",
                    display_status,
                    invoice.system_decision or "",
                    invoice.review_status,
                    "" if invoice.invoice_amount is None else f"{Decimal(str(invoice.invoice_amount)):.2f}",
                    invoice.invoice_number or "",
                    invoice.buyer_name or "",
                    ",".join(json.loads(invoice.risk_flags or "[]")),
                    invoice.failure_reason or "",
                ]
            )

        self._write_simple_xlsx(output_file, sheet_name="批次台账", rows=rows)

    def _write_simple_xlsx(self, output_file: Path, *, sheet_name: str, rows: list[list[str]]) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                cell_ref = f"{self._column_letter(col_index)}{row_index}"
                text = escape(value or "")
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>')
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
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
        return PROJECT_ROOT / candidate

    def _relative_output_path(self, output_file: Path) -> str:
        try:
            return output_file.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return str(output_file)

    @staticmethod
    def _column_letter(index: int) -> str:
        letters = []
        current = index
        while current > 0:
            current, remainder = divmod(current - 1, 26)
            letters.append(chr(65 + remainder))
        return "".join(reversed(letters))
