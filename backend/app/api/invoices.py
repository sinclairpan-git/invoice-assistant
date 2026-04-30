from __future__ import annotations

from collections import Counter
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import (
    assert_actor_has_role,
    get_session,
    get_trusted_actor,
)
from backend.app.api.serializers import (
    serialize_invoice_detail,
    serialize_review_queue_item,
    serialize_invoice_summary,
    serialize_review_action,
)
from backend.app.db.models import Batch, InvoiceRecord, ReviewAction
from backend.app.services.compliance_service import summarize_archiveable_pass
from backend.app.services.review_queue_service import ReviewQueueService
from backend.app.services.retry_service import RetryService
from backend.app.services.status_service import (
    DISPLAY_STATUS_DUPLICATE,
    DISPLAY_STATUS_REVIEW,
    derive_archive_status,
    summarize_business_buckets,
)


router = APIRouter(prefix="/api", tags=["invoices"])


class ReviewActionRequest(BaseModel):
    review_action: str
    review_note: str | None = None
    reviewed_by: str | None = None


REVIEW_STATUS_BY_ACTION = {
    "approve": "manually_approved",
    "reject": "manually_rejected",
    "keep_review_required": "not_reviewed",
}


@router.get("/batches/{batch_id}/invoices")
def list_batch_invoices(
    batch_id: str,
    display_status: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found.")

    invoices = session.scalars(
        select(InvoiceRecord)
        .where(InvoiceRecord.batch_id == batch_id)
        .order_by(InvoiceRecord.original_filename.asc())
    ).all()

    all_items = [serialize_invoice_summary(invoice) for invoice in invoices]
    if display_status in {None, "", "全部"}:
        filtered_items = all_items
    else:
        filtered_items = [
            item for item in all_items if item["display_status"] == display_status
        ]

    status_counts = dict(Counter(item["display_status"] for item in all_items))
    batch_summary = summarize_archiveable_pass(invoices)
    filtered_summary = summarize_archiveable_pass(
        [
            invoice
            for invoice in invoices
            if display_status in {None, "", "全部"}
            or serialize_invoice_summary(invoice)["display_status"] == display_status
        ]
    )

    return {
        "items": filtered_items,
        "status_counts": status_counts,
        "batch_summary": {
            "count": batch_summary.count,
            "total_amount": f"{batch_summary.total_amount:.2f}",
        },
        "filtered_summary": {
            "count": filtered_summary.count,
            "total_amount": f"{filtered_summary.total_amount:.2f}",
        },
        "action_summary": summarize_business_buckets(invoices).to_dict(),
    }


@router.get("/invoices/{invoice_id}")
def get_invoice_detail(
    invoice_id: str, session: Session = Depends(get_session)
) -> dict[str, object]:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return {"item": serialize_invoice_detail(invoice)}


@router.get("/review-queue")
def list_review_queue(
    batch_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    service = ReviewQueueService(session)
    items = service.list_open_items(batch_id=batch_id)
    session.commit()

    invoice_statement = select(InvoiceRecord)
    if batch_id is not None:
        invoice_statement = invoice_statement.where(InvoiceRecord.batch_id == batch_id)
    invoices = session.scalars(invoice_statement).all()
    return {
        "items": [serialize_review_queue_item(item) for item in items],
        "action_summary": summarize_business_buckets(invoices).to_dict(),
    }


@router.get("/invoices/{invoice_id}/preview")
def get_invoice_preview(
    invoice_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> FileResponse:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    absolute_path = _resolve_preview_path(invoice=invoice, request=request)

    return FileResponse(
        absolute_path,
        media_type="application/pdf",
        filename=Path(absolute_path).name,
    )


@router.get("/invoices/{invoice_id}/preview-rendered")
def get_invoice_preview_rendered(
    invoice_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    absolute_path = _resolve_preview_path(invoice=invoice, request=request)
    render_error: str | None = None
    try:
        page_count = _count_pdf_pages(absolute_path)
    except Exception:
        page_count = 0
        render_error = "当前文件无法渲染为图片预览，请直接打开原始 PDF。"

    page_images = "\n".join(
        f'<img src="/api/invoices/{invoice.id}/preview-pages/{page_no}" alt="page {page_no}" style="width: 100%; display: block; margin: 0 auto 16px; background: #fff;" />'
        for page_no in range(1, page_count + 1)
    )
    empty_state = (
        f'<div class="empty">{escape(render_error)}</div>'
        if render_error
        else '<div class="empty">当前文件没有可渲染的页面。</div>'
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(invoice.original_filename)}</title>
    <style>
      body {{
        margin: 0;
        padding: 16px;
        background: #f5f5f2;
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      }}
      .preview {{
        max-width: 960px;
        margin: 0 auto;
      }}
      .toolbar {{
        position: sticky;
        top: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
        padding: 12px 16px;
        border: 1px solid #d9dfd3;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.94);
      }}
      .meta {{
        color: #546056;
        font-size: 14px;
      }}
      .link {{
        color: #1677ff;
        text-decoration: none;
      }}
      .empty {{
        padding: 40px 24px;
        text-align: center;
        border: 1px dashed #d9dfd3;
        border-radius: 10px;
        background: #fff;
      }}
    </style>
  </head>
  <body>
    <div class="preview">
      <div class="toolbar">
        <div class="meta">{escape(invoice.original_filename)} | {page_count} 页</div>
        <a class="link" href="/api/invoices/{invoice.id}/preview" target="_blank" rel="noreferrer">打开原始 PDF</a>
      </div>
      {page_images or empty_state}
    </div>
  </body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/invoices/{invoice_id}/preview-pages/{page_no}")
def get_invoice_preview_page(
    invoice_id: str,
    page_no: int,
    request: Request,
    session: Session = Depends(get_session),
) -> Response:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if page_no < 1:
        raise HTTPException(status_code=404, detail="Preview page not found.")

    absolute_path = _resolve_preview_path(invoice=invoice, request=request)
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="PDF preview renderer is unavailable.") from exc

    document = pdfium.PdfDocument(str(absolute_path))
    try:
        if page_no > len(document):
            raise HTTPException(status_code=404, detail="Preview page not found.")
        page = document[page_no - 1]
        bitmap = page.render(scale=2.0)
        image = bitmap.to_pil()
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return Response(content=buffer.getvalue(), media_type="image/png")
    finally:
        document.close()


@router.post("/invoices/{invoice_id}/retry")
def retry_invoice(
    invoice_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.processing_status != "processing_failed":
        return {
            "item": {
                "invoice_id": invoice.id,
                "batch_id": invoice.batch_id,
                "retried": False,
            }
        }

    service = RetryService(
        session=session,
        processing_runner=request.app.state.processing_runner,
    )
    try:
        service.retry_invoice(invoice_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "item": {
            "invoice_id": invoice.id,
            "batch_id": invoice.batch_id,
            "retried": True,
        }
    }


@router.post("/invoices/{invoice_id}/review-actions")
def create_review_action(
    invoice_id: str,
    request: ReviewActionRequest,
    session: Session = Depends(get_session),
    trusted_actor=Depends(get_trusted_actor),
) -> dict[str, object]:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    actor = trusted_actor
    assert_actor_has_role(
        session=session,
        actor=actor,
        required_role="reviewer",
        entity_type="invoice_review",
        entity_id=invoice.id,
        denied_action="review_denied",
        denied_detail="当前操作者缺少 reviewer 角色。",
        change_summary=f"review_action={request.review_action}",
        change_reason=request.review_note or "missing reviewer role",
        payload={
            "invoice_id": invoice.id,
            "review_action": request.review_action,
        },
    )

    if request.review_action not in REVIEW_STATUS_BY_ACTION:
        raise HTTPException(status_code=400, detail="Unsupported review action.")

    display_status = serialize_invoice_summary(invoice)["display_status"]
    if display_status not in {DISPLAY_STATUS_REVIEW, DISPLAY_STATUS_DUPLICATE}:
        raise HTTPException(
            status_code=400,
            detail="Only review-required or duplicate invoices can be manually reviewed.",
        )

    review = ReviewAction(
        invoice_id=invoice.id,
        review_action=request.review_action,
        review_note=request.review_note,
        reviewed_by=actor.display_name,
    )
    invoice.review_status = REVIEW_STATUS_BY_ACTION[request.review_action]
    invoice.archive_status = derive_archive_status(
        processing_status=invoice.processing_status,
        system_decision=invoice.system_decision,
        duplicate_flag=invoice.duplicate_flag,
        review_status=invoice.review_status,
        archive_status=invoice.archive_status,
        artifact_status=invoice.artifact_status,
    )

    session.add(review)
    review_queue_service = ReviewQueueService(session)
    review_queue_item = review_queue_service.sync_invoice(invoice)
    session.commit()
    session.refresh(invoice)
    session.refresh(review)
    if review_queue_item is not None:
        session.refresh(review_queue_item)

    batch_invoices = session.scalars(
        select(InvoiceRecord).where(InvoiceRecord.batch_id == invoice.batch_id)
    ).all()

    return {
        "item": serialize_review_action(review),
        "invoice": serialize_invoice_summary(invoice),
        "review_queue_item": serialize_review_queue_item(review_queue_item),
        "batch_action_summary": summarize_business_buckets(batch_invoices).to_dict(),
    }


def _resolve_preview_path(*, invoice: InvoiceRecord, request: Request) -> Path:
    storage_path = invoice.storage_path_renamed or invoice.storage_path_original
    if not storage_path:
        raise HTTPException(status_code=404, detail="Preview file not found.")

    storage_root = Path(request.app.state.storage_root).resolve()
    storage_parent = storage_root.parent
    storage_candidate = Path(storage_path)
    if storage_candidate.is_absolute():
        absolute_path = storage_candidate.resolve()
    else:
        absolute_path = (storage_parent / storage_candidate).resolve()

    allowed_roots = (storage_root, storage_parent)
    if not any(absolute_path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="Invalid preview path.")
    if not absolute_path.is_file():
        raise HTTPException(status_code=404, detail="Preview file not found.")
    return absolute_path


def _count_pdf_pages(path: Path) -> int:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="PDF preview renderer is unavailable.") from exc

    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()
