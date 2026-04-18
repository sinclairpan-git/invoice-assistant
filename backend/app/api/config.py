from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import (
    assert_actor_has_role,
    get_session,
    get_trusted_actor,
    resolve_actor,
)
from backend.app.api.serializers import serialize_rule_version
from backend.app.db.models import RuleVersion
from backend.app.services.config_service import ConfigService, RULE_KINDS


router = APIRouter(prefix="/api/config", tags=["config"])


class CreateRuleVersionRequest(BaseModel):
    content: dict[str, object]
    changed_by: str | None = None
    change_summary: str
    change_reason: str
    activate: bool = True


@router.get("")
def get_active_config(session: Session = Depends(get_session)) -> dict[str, object]:
    service = ConfigService(session)
    active_versions = {
        kind: serialize_rule_version(version)
        for kind in RULE_KINDS
        if (version := service.get_latest_active(kind)) is not None
    }
    return {
        "active_snapshot": service.get_active_snapshot(),
        "active_versions": active_versions,
    }


@router.get("/{kind}/versions")
def list_rule_versions(
    kind: str, session: Session = Depends(get_session)
) -> dict[str, object]:
    if kind not in RULE_KINDS:
        raise HTTPException(status_code=400, detail="Unsupported rule kind.")

    versions = session.scalars(
        select(RuleVersion)
        .where(RuleVersion.kind == kind)
        .order_by(RuleVersion.changed_at.desc())
    ).all()
    return {"items": [serialize_rule_version(version) for version in versions]}


@router.post("/{kind}/versions")
def create_rule_version(
    kind: str,
    request: CreateRuleVersionRequest,
    session: Session = Depends(get_session),
    trusted_actor=Depends(get_trusted_actor),
) -> dict[str, object]:
    actor = resolve_actor(trusted_actor, fallback_display_name=request.changed_by)
    assert_actor_has_role(
        session=session,
        actor=actor,
        required_role="config_admin",
        entity_type="rule_version",
        entity_id=str(uuid4()),
        denied_action="create_denied",
        denied_detail="当前操作者缺少 config_admin 角色。",
        change_summary=request.change_summary,
        change_reason=request.change_reason,
        payload={
            "kind": kind,
            "activate": request.activate,
        },
    )
    service = ConfigService(session)
    try:
        version = service.create_version(
            kind=kind,
            content=request.content,
            changed_by=actor.display_name,
            change_summary=request.change_summary,
            change_reason=request.change_reason,
            activate=request.activate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": serialize_rule_version(version)}
