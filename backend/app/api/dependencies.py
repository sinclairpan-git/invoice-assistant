from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog
from backend.app.db.session import get_db_session


def get_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    yield from get_db_session(session_factory)


CONTROLLED_ROLES = ("config_admin", "reviewer", "exporter")


@dataclass(frozen=True)
class TrustedActor:
    actor_id: str
    display_name: str
    roles: tuple[str, ...]
    trusted: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "display_name": self.display_name,
            "roles": list(self.roles),
        }


def get_trusted_actor(request: Request) -> TrustedActor:
    actor_payload = getattr(request.app.state, "trusted_actor", None)
    if isinstance(actor_payload, dict):
        return TrustedActor(
            actor_id=str(actor_payload.get("actor_id") or "trusted-actor"),
            display_name=str(actor_payload.get("display_name") or "本机管理员"),
            roles=tuple(str(role) for role in actor_payload.get("roles", []) if str(role).strip()),
            trusted=True,
        )

    return TrustedActor(
        actor_id="local-operator",
        display_name="本机管理员",
        roles=CONTROLLED_ROLES,
        trusted=False,
    )


def resolve_actor(
    actor: TrustedActor,
    *,
    fallback_display_name: str | None = None,
) -> TrustedActor:
    if actor.trusted:
        return actor
    if not fallback_display_name or not fallback_display_name.strip():
        return actor
    return TrustedActor(
        actor_id=actor.actor_id,
        display_name=fallback_display_name.strip(),
        roles=actor.roles,
        trusted=False,
    )


def assert_actor_has_role(
    *,
    session: Session,
    actor: TrustedActor,
    required_role: str,
    entity_type: str,
    entity_id: str | None,
    denied_action: str,
    denied_detail: str,
    change_summary: str,
    change_reason: str,
    payload: dict[str, object] | None = None,
) -> None:
    if required_role in actor.roles:
        return

    audit = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id or str(uuid4()),
        action=denied_action,
        changed_by=actor.display_name,
        change_summary=change_summary,
        change_reason=change_reason,
        payload_json=json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
    )
    session.add(audit)
    session.commit()
    raise HTTPException(status_code=403, detail=denied_detail)
