from __future__ import annotations

import json
import math
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog, RuleVersion


RULE_KINDS = ("tax_profile", "business_rules", "naming_rules")
REQUIRED_SETUP_FIELDS = {
    "tax_profile": ("buyer_name", "buyer_tax_no"),
    "business_rules": ("template_name",),
    "naming_rules": ("pattern",),
}
DEFAULT_BUSINESS_RULE_TEMPLATES = {
    "conservative": {
        "template_name": "conservative",
        "display_name": "保守模板",
        "minimum_confidence": 0.9,
    },
    "regular": {
        "template_name": "regular",
        "display_name": "常规模板",
        "minimum_confidence": 0.75,
    },
}


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
        version = self._append_version(
            kind=kind,
            content=content,
            changed_by=changed_by,
            change_summary=change_summary,
            change_reason=change_reason,
            activate=activate,
        )
        self.session.commit()
        self.session.refresh(version)
        return version

    def create_initial_setup(
        self,
        *,
        tax_profile: dict[str, object],
        business_rules: dict[str, object],
        naming_rules: dict[str, object],
        changed_by: str,
        change_summary: str,
        change_reason: str,
    ) -> dict[str, RuleVersion]:
        created_versions: dict[str, RuleVersion] = {}
        payloads = {
            "tax_profile": tax_profile,
            "business_rules": business_rules,
            "naming_rules": naming_rules,
        }

        try:
            for kind in RULE_KINDS:
                created_versions[kind] = self._append_version(
                    kind=kind,
                    content=payloads[kind],
                    changed_by=changed_by,
                    change_summary=change_summary,
                    change_reason=change_reason,
                    activate=True,
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        for version in created_versions.values():
            self.session.refresh(version)
        return created_versions

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

    def get_setup_status(self) -> dict[str, object]:
        missing_required_fields: dict[str, list[str]] = {}
        for kind, required_fields in REQUIRED_SETUP_FIELDS.items():
            version = self.get_latest_active(kind)
            content = json.loads(version.content_json) if version is not None else {}
            missing_required_fields[kind] = self._missing_required_fields(
                kind=kind, content=content
            )
        return {
            "complete": all(
                not missing_fields
                for missing_fields in missing_required_fields.values()
            ),
            "default_business_rule_templates": DEFAULT_BUSINESS_RULE_TEMPLATES,
            "missing_required_fields": missing_required_fields,
        }

    def _append_version(
        self,
        *,
        kind: str,
        content: dict[str, object],
        changed_by: str,
        change_summary: str,
        change_reason: str,
        activate: bool,
    ) -> RuleVersion:
        self._validate_rule_content(kind=kind, content=content)

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
        self.session.flush()
        return version

    def _validate_rule_content(self, *, kind: str, content: dict[str, object]) -> None:
        if kind != "business_rules":
            return

        if "minimum_confidence" not in content:
            return

        raw_value = content.get("minimum_confidence")
        if isinstance(raw_value, bool):
            raise ValueError("minimum_confidence 必须是 0 到 1 之间的数字。")
        if not isinstance(raw_value, (int, float)):
            raise ValueError("minimum_confidence 必须是 0 到 1 之间的数字。")

        minimum_confidence = float(raw_value)
        if math.isnan(minimum_confidence) or math.isinf(minimum_confidence):
            raise ValueError("minimum_confidence 必须是 0 到 1 之间的数字。")
        if minimum_confidence < 0 or minimum_confidence > 1:
            raise ValueError("minimum_confidence 必须在 0 到 1 之间。")

    @staticmethod
    def _is_missing_required_value(value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        return False

    def _missing_required_fields(
        self, *, kind: str, content: dict[str, object]
    ) -> list[str]:
        if kind == "business_rules":
            has_template_name = not self._is_missing_required_value(
                content.get("template_name")
            )
            has_legacy_minimum_confidence = not self._is_missing_required_value(
                content.get("minimum_confidence")
            )
            if has_template_name or has_legacy_minimum_confidence:
                return []
            return ["template_name"]

        return [
            field_name
            for field_name in REQUIRED_SETUP_FIELDS[kind]
            if self._is_missing_required_value(content.get(field_name))
        ]
