from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import (
    assert_actor_has_role,
    get_session,
    get_trusted_actor,
)
from backend.app.api.serializers import serialize_batch
from backend.app.db.models import Batch
from backend.app.services.batch_service import BatchService, IncomingFile
from backend.app.services.config_service import ConfigService
from backend.app.services.export_service import ExportService
from backend.app.services.progress_service import ProgressService
from backend.app.services.retry_service import RetryService
from backend.app.services.storage_service import StorageError, StorageService


router = APIRouter(prefix="/api/batches", tags=["batches"])


def _ascii_download_filename(filename: str) -> str:
    suffix = Path(filename).suffix
    if suffix and suffix.isascii():
        return f"invoice-assistant-download{suffix}"
    return "invoice-assistant-download"


def _download_response_headers(filename: str) -> dict[str, str]:
    encoded_filename = quote(filename, safe="")
    fallback_filename = _ascii_download_filename(filename)
    return {
        "Content-Disposition": (
            f'attachment; filename="{fallback_filename}"; '
            f"filename*=UTF-8''{encoded_filename}"
        ),
        "X-Invoice-Assistant-Filename": encoded_filename,
    }


def get_storage_root(request: Request) -> Path:
    return Path(request.app.state.storage_root)


class ExportRequest(BaseModel):
    export_type: str
    created_by: str | None = None


class DownloadRequest(BaseModel):
    download_format: str
    selection_mode: str = "all"
    display_status: str | None = None
    invoice_ids: list[str] | None = None


@router.get("")
def list_batches(session: Session = Depends(get_session)) -> dict[str, object]:
    batches = session.scalars(select(Batch).order_by(Batch.created_at.desc())).all()
    progress_service = ProgressService(session)
    items = [
        serialize_batch(
            batch, progress=progress_service.refresh_batch(batch.id, persist=False)
        )
        for batch in batches
    ]
    return {"items": items}


@router.get("/{batch_id}")
def get_batch(
    batch_id: str, session: Session = Depends(get_session)
) -> dict[str, object]:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found.")

    progress = ProgressService(session).refresh_batch(batch_id, persist=False)
    return {
        "item": serialize_batch(
            batch, progress=progress, include_snapshot=True, include_exports=True
        )
    }


@router.get("/{batch_id}/progress")
def get_batch_progress(
    batch_id: str, session: Session = Depends(get_session)
) -> dict[str, object]:
    try:
        progress = ProgressService(session).refresh_batch(batch_id, persist=False)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": progress.to_dict()}


@router.post("")
async def create_batch(
    request: Request,
    created_by: str | None = Form(default=None),
    batch_no: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    trusted_actor=Depends(get_trusted_actor),
) -> dict[str, object]:
    if not files:
        raise HTTPException(
            status_code=400, detail="At least one file is required to create a batch."
        )

    config_service = ConfigService(session)
    setup_status = config_service.get_setup_status()
    if not setup_status["complete"]:
        raise HTTPException(
            status_code=400,
            detail="请先完成首次配置向导，再开始上传发票。",
        )

    incoming_files: list[IncomingFile] = []
    for uploaded_file in files:
        filename = uploaded_file.filename or "unnamed.pdf"
        incoming_files.append(
            IncomingFile(
                filename=filename,
                content=await uploaded_file.read(),
            )
        )

    service = BatchService(
        session=session,
        storage_service=StorageService(get_storage_root(request)),
        config_service=config_service,
    )
    actor = trusted_actor
    try:
        batch = service.create_batch(
            files=incoming_files,
            created_by=actor.display_name,
            batch_no=batch_no,
        )
        request.app.state.processing_runner.enqueue(batch.id)
    except (StorageError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    progress = ProgressService(session).refresh_batch(batch.id, persist=True)
    return {"item": serialize_batch(batch, progress=progress, include_snapshot=True)}


@router.post("/{batch_id}/exports")
def create_export(
    batch_id: str,
    request: Request,
    payload: ExportRequest,
    session: Session = Depends(get_session),
    trusted_actor=Depends(get_trusted_actor),
) -> dict[str, object]:
    actor = trusted_actor
    assert_actor_has_role(
        session=session,
        actor=actor,
        required_role="exporter",
        entity_type="export_job",
        entity_id=batch_id,
        denied_action="export_denied",
        denied_detail="当前操作者缺少 exporter 角色。",
        change_summary=f"export_type={payload.export_type}",
        change_reason="missing exporter role",
        payload={
            "batch_id": batch_id,
            "export_type": payload.export_type,
        },
    )
    service = ExportService(session, storage_root=get_storage_root(request))
    try:
        result = service.create_export(
            batch_id=batch_id,
            export_type=payload.export_type,
            created_by=actor.display_name,
            actor_roles=actor.roles,
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


@router.post("/{batch_id}/downloads")
def create_download(
    batch_id: str,
    payload: DownloadRequest,
    request: Request,
    session: Session = Depends(get_session),
    trusted_actor=Depends(get_trusted_actor),
) -> Response:
    actor = trusted_actor
    assert_actor_has_role(
        session=session,
        actor=actor,
        required_role="exporter",
        entity_type="export_job",
        entity_id=batch_id,
        denied_action="download_denied",
        denied_detail="当前操作者缺少 exporter 角色。",
        change_summary=f"download_format={payload.download_format}",
        change_reason="missing exporter role",
        payload={
            "batch_id": batch_id,
            "download_format": payload.download_format,
            "selection_mode": payload.selection_mode,
            "display_status": payload.display_status,
            "invoice_ids": payload.invoice_ids or [],
        },
    )
    service = ExportService(session, storage_root=get_storage_root(request))
    try:
        result = service.build_download(
            batch_id=batch_id,
            download_format=payload.download_format,
            created_by=actor.display_name,
            actor_roles=actor.roles,
            selection_mode=payload.selection_mode,
            display_status=payload.display_status,
            invoice_ids=payload.invoice_ids,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=result.content,
        media_type=result.media_type,
        headers=_download_response_headers(result.filename),
    )


@router.post("/{batch_id}/retry-failures")
def retry_batch_failures(
    batch_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    service = RetryService(
        session=session,
        processing_runner=request.app.state.processing_runner,
    )
    try:
        retried_invoice_ids = service.retry_batch_failures(batch_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "item": {
            "batch_id": batch_id,
            "retried_invoice_ids": retried_invoice_ids,
        }
    }
