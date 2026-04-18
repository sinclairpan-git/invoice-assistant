from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog, RuleVersion


RULE_KINDS = ("tax_profile", "business_rules", "naming_rules")


class ConfigService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_version(
        self,
        *,
        kind: str,
        content: dict,
        changed_by: str,
        change_summary: str,
        change_reason: str,
        activate: bool = True,
    ) -> RuleVersion:
        if kind not in RULE_KINDS:
            raise ValueError(f"Unsupported rule kind: {kind!r}")

        version_count = self.session.scalar(
            select(func.count())
            .select_from(RuleVersion)
            .where(RuleVersion.kind == kind)
        )
        next_version_no = f"v{(version_count or 0) + 1}"

        if activate:
            current_versions = self.session.scalars(
                select(RuleVersion).where(
                    RuleVersion.kind == kind, RuleVersion.is_active.is_(True)
                )
            ).all()
            for version in current_versions:
                version.is_active = False

        version_id = str(uuid4())
        version = RuleVersion(
            id=version_id,
            kind=kind,
            version_no=next_version_no,
            content_json=json.dumps(content, sort_keys=True),
            is_active=activate,
            change_summary=change_summary,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        audit = AuditLog(
            entity_type="rule_version",
            entity_id=version_id,
            action="create",
            changed_by=changed_by,
            change_summary=change_summary,
            change_reason=change_reason,
            payload_json=json.dumps(
                {
                    "kind": kind,
                    "version_no": next_version_no,
                    "content": content,
                    "activated": activate,
                },
                sort_keys=True,
            ),
        )

        self.session.add(version)
        self.session.add(audit)
        self.session.commit()
        self.session.refresh(version)
        return version

    def get_latest_active(self, kind: str) -> RuleVersion | None:
        if kind not in RULE_KINDS:
            raise ValueError(f"Unsupported rule kind: {kind!r}")
        return self.session.scalar(
            select(RuleVersion)
            .where(RuleVersion.kind == kind, RuleVersion.is_active.is_(True))
            .order_by(RuleVersion.changed_at.desc())
            .limit(1)
        )

    def get_active_snapshot(self) -> dict[str, dict[str, object] | None]:
        snapshot: dict[str, dict[str, object] | None] = {}
        for kind in RULE_KINDS:
            version = self.get_latest_active(kind)
            if version is None:
                snapshot[kind] = None
                continue
            snapshot[kind] = {
                "id": version.id,
                "version_no": version.version_no,
                "content": json.loads(version.content_json),
                "changed_by": version.changed_by,
                "change_summary": version.change_summary,
                "change_reason": version.change_reason,
            }
        return snapshot
