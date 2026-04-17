from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_session
from backend.app.api.serializers import serialize_batch
from backend.app.db.models import Batch
from backend.app.services.export_service import ExportService
from backend.app.services.progress_service import ProgressService


router = APIRouter(prefix="/api/batches", tags=["batches"])


class ExportRequest(BaseModel):
    export_type: str
    created_by: str


@router.get("")
def list_batches(session: Session = Depends(get_session)) -> dict[str, object]:
    batches = session.scalars(select(Batch).order_by(Batch.created_at.desc())).all()
    progress_service = ProgressService(session)
    items = [
        serialize_batch(batch, progress=progress_service.refresh_batch(batch.id, persist=False))
        for batch in batches
    ]
    return {"items": items}


@router.get("/{batch_id}")
def get_batch(batch_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found.")

    progress = ProgressService(session).refresh_batch(batch_id, persist=False)
    return {"item": serialize_batch(batch, progress=progress, include_snapshot=True, include_exports=True)}


@router.get("/{batch_id}/progress")
def get_batch_progress(batch_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    try:
        progress = ProgressService(session).refresh_batch(batch_id, persist=False)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": progress.to_dict()}


@router.post("/{batch_id}/exports")
def create_export(batch_id: str, request: ExportRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    service = ExportService(session)
    try:
        result = service.create_export(
            batch_id=batch_id,
            export_type=request.export_type,
            created_by=request.created_by,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "item": {
            "job_id": result.job_id,
            "export_type": result.export_type,
            "status": result.status,
            "output_path": result.output_path,
            "summary": result.summary,
        }
    }
