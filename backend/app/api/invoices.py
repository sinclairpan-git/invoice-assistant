from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_session
from backend.app.api.serializers import serialize_invoice_detail, serialize_invoice_summary, serialize_review_action
from backend.app.db.models import Batch, InvoiceRecord, ReviewAction
from backend.app.services.status_service import DISPLAY_STATUS_DUPLICATE, DISPLAY_STATUS_REVIEW, summarize_suggested_pass


router = APIRouter(prefix="/api", tags=["invoices"])


class ReviewActionRequest(BaseModel):
    review_action: str
    review_note: str | None = None
    reviewed_by: str


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
        select(InvoiceRecord).where(InvoiceRecord.batch_id == batch_id).order_by(InvoiceRecord.original_filename.asc())
    ).all()

    all_items = [serialize_invoice_summary(invoice) for invoice in invoices]
    if display_status in {None, "", "全部"}:
        filtered_items = all_items
    else:
        filtered_items = [item for item in all_items if item["display_status"] == display_status]

    status_counts = dict(Counter(item["display_status"] for item in all_items))
    batch_summary = summarize_suggested_pass(invoices)
    filtered_summary = summarize_suggested_pass(
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
    }


@router.get("/invoices/{invoice_id}")
def get_invoice_detail(invoice_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return {"item": serialize_invoice_detail(invoice)}


@router.post("/invoices/{invoice_id}/review-actions")
def create_review_action(
    invoice_id: str,
    request: ReviewActionRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    invoice = session.get(InvoiceRecord, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    if request.review_action not in REVIEW_STATUS_BY_ACTION:
        raise HTTPException(status_code=400, detail="Unsupported review action.")

    display_status = serialize_invoice_summary(invoice)["display_status"]
    if display_status not in {DISPLAY_STATUS_REVIEW, DISPLAY_STATUS_DUPLICATE}:
        raise HTTPException(status_code=400, detail="Only review-required or duplicate invoices can be manually reviewed.")

    review = ReviewAction(
        invoice_id=invoice.id,
        review_action=request.review_action,
        review_note=request.review_note,
        reviewed_by=request.reviewed_by,
    )
    invoice.review_status = REVIEW_STATUS_BY_ACTION[request.review_action]

    session.add(review)
    session.commit()
    session.refresh(invoice)
    session.refresh(review)

    return {
        "item": serialize_review_action(review),
        "invoice": serialize_invoice_summary(invoice),
    }
