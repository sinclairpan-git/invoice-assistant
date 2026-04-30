from __future__ import annotations

import json
import math
import re
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog, RuleVersion


RULE_KINDS = ("tax_profile", "business_rules", "naming_rules")
SETUP_STATUS_RULE_KINDS = ("tax_profile", "business_rules", "naming_rules")
RULE_KIND_TO_BUNDLE_SECTION = {
    "tax_profile": "profile",
    "business_rules": "review_policy",
    "naming_rules": "naming_policy",
}
BUNDLE_SECTION_TO_RULE_KIND = {
    section: kind for kind, section in RULE_KIND_TO_BUNDLE_SECTION.items()
}
REQUIRED_SETUP_FIELDS = {
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
        if not activate:
            raise ValueError("Canonical ConfigBundle publishing requires activate=True.")

        bundle_content = self._active_bundle_content()
        bundle_content[RULE_KIND_TO_BUNDLE_SECTION[kind]] = dict(content)
        versions = self._publish_bundle_versions(
            profile=bundle_content["profile"],
            review_policy=bundle_content["review_policy"],
            naming_policy=bundle_content["naming_policy"],
            changed_by=changed_by,
            change_summary=change_summary,
            change_reason=change_reason,
            activate=True,
        )
        self.session.commit()
        for version in versions.values():
            self.session.refresh(version)
        return versions[kind]

    def publish_bundle(
        self,
        *,
        profile: dict[str, object],
        review_policy: dict[str, object],
        naming_policy: dict[str, object],
        changed_by: str,
        change_summary: str,
        change_reason: str,
    ) -> dict[str, RuleVersion]:
        versions = self._publish_bundle_versions(
            profile=profile,
            review_policy=review_policy,
            naming_policy=naming_policy,
            changed_by=changed_by,
            change_summary=change_summary,
            change_reason=change_reason,
            activate=True,
        )
        self.session.commit()
        for version in versions.values():
            self.session.refresh(version)
        return versions

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
        try:
            versions = self._publish_bundle_versions(
                profile=tax_profile,
                review_policy=business_rules,
                naming_policy=naming_rules,
                changed_by=changed_by,
                change_summary=change_summary,
                change_reason=change_reason,
                activate=True,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        for version in versions.values():
            self.session.refresh(version)
        return versions

    def get_latest_active(self, kind: str) -> RuleVersion | None:
        if kind not in RULE_KINDS:
            raise ValueError(f"Unsupported rule kind: {kind!r}")
        return self.session.scalar(
            select(RuleVersion)
            .where(RuleVersion.kind == kind, RuleVersion.is_active.is_(True))
            .order_by(RuleVersion.changed_at.desc())
            .limit(1)
        )

    def list_bundle_versions(self) -> list[dict[str, object]]:
        grouped_versions = self._list_grouped_bundle_versions()
        return [
            self._build_bundle_payload(grouped_versions[bundle_version_no])
            for bundle_version_no in sorted(
                grouped_versions.keys(),
                key=self._bundle_sort_key,
                reverse=True,
            )
        ]

    def get_active_bundle(self) -> dict[str, object] | None:
        active_versions = self._get_active_versions()
        if not any(version is not None for version in active_versions.values()):
            return None
        return self._build_bundle_payload(active_versions)

    def get_active_snapshot(self) -> dict[str, dict[str, object] | None]:
        snapshot: dict[str, dict[str, object] | None] = {}
        for kind in RULE_KINDS:
            version = self.get_latest_active(kind)
            if version is None:
                snapshot[kind] = None
                continue
            snapshot[kind] = self._serialize_rule_version(version)
        return snapshot

    def get_setup_status(self) -> dict[str, object]:
        missing_required_fields: dict[str, list[str]] = {}
        for kind in SETUP_STATUS_RULE_KINDS:
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

    def _publish_bundle_versions(
        self,
        *,
        profile: dict[str, object],
        review_policy: dict[str, object],
        naming_policy: dict[str, object],
        changed_by: str,
        change_summary: str,
        change_reason: str,
        activate: bool,
    ) -> dict[str, RuleVersion]:
        if not activate:
            raise ValueError("ConfigBundle versions must activate immediately.")

        payloads = {
            "tax_profile": self._normalize_rule_content(
                kind="tax_profile", content=profile
            ),
            "business_rules": self._normalize_rule_content(
                kind="business_rules", content=review_policy
            ),
            "naming_rules": self._normalize_rule_content(
                kind="naming_rules", content=naming_policy
            ),
        }
        for kind, payload in payloads.items():
            self._validate_rule_content(kind=kind, content=payload)

        bundle_version_no = self._next_bundle_version_no()
        created_versions: dict[str, RuleVersion] = {}

        for kind in RULE_KINDS:
            current_versions = self.session.scalars(
                select(RuleVersion).where(
                    RuleVersion.kind == kind, RuleVersion.is_active.is_(True)
                )
            ).all()
            for version in current_versions:
                version.is_active = False

            next_version_no = self._next_rule_version_no(kind)
            version_id = str(uuid4())
            version = RuleVersion(
                id=version_id,
                kind=kind,
                version_no=next_version_no,
                bundle_version_no=bundle_version_no,
                content_json=json.dumps(payloads[kind], sort_keys=True),
                is_active=True,
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
                        "bundle_version_no": bundle_version_no,
                        "kind": kind,
                        "version_no": next_version_no,
                        "content": payloads[kind],
                        "activated": True,
                    },
                    sort_keys=True,
                ),
            )
            self.session.add(version)
            self.session.add(audit)
            created_versions[kind] = version

        self.session.flush()
        return created_versions

    def _get_active_versions(self) -> dict[str, RuleVersion | None]:
        return {kind: self.get_latest_active(kind) for kind in RULE_KINDS}

    def _active_bundle_content(self) -> dict[str, dict[str, object]]:
        active_bundle = self.get_active_bundle()
        if active_bundle is None:
            return {
                "profile": {},
                "review_policy": {},
                "naming_policy": {},
            }
        return {
            "profile": dict(active_bundle["profile"]),
            "review_policy": dict(active_bundle["review_policy"]),
            "naming_policy": dict(active_bundle["naming_policy"]),
        }

    def _build_bundle_payload(
        self, versions_by_kind: dict[str, RuleVersion | None]
    ) -> dict[str, object]:
        profile_version = versions_by_kind.get("tax_profile")
        review_policy_version = versions_by_kind.get("business_rules")
        naming_policy_version = versions_by_kind.get("naming_rules")
        ordered_versions = [
            version
            for version in (
                profile_version,
                review_policy_version,
                naming_policy_version,
            )
            if version is not None
        ]
        latest_version = max(ordered_versions, key=lambda item: item.changed_at)
        bundle_version_no = self._shared_bundle_version_no(ordered_versions)
        if bundle_version_no is None:
            bundle_version_no = self._legacy_bundle_version_no(ordered_versions)

        return {
            "bundle_version_no": bundle_version_no,
            "profile": self._rule_content(profile_version),
            "review_policy": self._rule_content(review_policy_version),
            "naming_policy": self._rule_content(naming_policy_version),
            "changed_by": latest_version.changed_by,
            "changed_at": latest_version.changed_at.isoformat(),
            "change_summary": latest_version.change_summary,
            "change_reason": latest_version.change_reason,
            "component_versions": {
                kind: self._serialize_rule_version(version)
                for kind, version in versions_by_kind.items()
                if version is not None
            },
        }

    def _list_grouped_bundle_versions(self) -> dict[str, dict[str, RuleVersion | None]]:
        versions = self.session.scalars(
            select(RuleVersion).order_by(RuleVersion.changed_at.desc(), RuleVersion.id.desc())
        ).all()
        grouped: dict[str, dict[str, RuleVersion | None]] = {}
        for version in versions:
            if not version.bundle_version_no:
                continue
            current = grouped.setdefault(
                version.bundle_version_no,
                {kind: None for kind in RULE_KINDS},
            )
            if current[version.kind] is None:
                current[version.kind] = version
        return grouped

    @staticmethod
    def _serialize_rule_version(version: RuleVersion) -> dict[str, object]:
        return {
            "id": version.id,
            "kind": version.kind,
            "version_no": version.version_no,
            "bundle_version_no": version.bundle_version_no,
            "content": json.loads(version.content_json),
            "is_active": version.is_active,
            "change_summary": version.change_summary,
            "changed_by": version.changed_by,
            "changed_at": version.changed_at.isoformat(),
            "change_reason": version.change_reason,
        }

    @staticmethod
    def _rule_content(version: RuleVersion | None) -> dict[str, object]:
        if version is None:
            return {}
        return json.loads(version.content_json)

    @staticmethod
    def _shared_bundle_version_no(versions: list[RuleVersion]) -> str | None:
        bundle_version_numbers = {
            version.bundle_version_no
            for version in versions
            if version.bundle_version_no
        }
        if len(bundle_version_numbers) == 1:
            return next(iter(bundle_version_numbers))
        return None

    def _legacy_bundle_version_no(self, versions: list[RuleVersion]) -> str:
        max_component_version = 0
        for version in versions:
            max_component_version = max(
                max_component_version,
                self._version_sort_key(version.version_no),
            )
        return f"legacy-b{max_component_version or 1}"

    def _next_rule_version_no(self, kind: str) -> str:
        version_count = self.session.scalar(
            select(func.count())
            .select_from(RuleVersion)
            .where(RuleVersion.kind == kind)
        )
        return f"v{(version_count or 0) + 1}"

    def _next_bundle_version_no(self) -> str:
        bundle_versions = self.session.scalars(
            select(RuleVersion.bundle_version_no).where(
                RuleVersion.bundle_version_no.is_not(None)
            )
        ).all()
        max_index = 0
        for bundle_version_no in bundle_versions:
            if not bundle_version_no:
                continue
            max_index = max(max_index, self._bundle_sort_key(bundle_version_no))
        return f"b{max_index + 1}"

    @staticmethod
    def _bundle_sort_key(bundle_version_no: str) -> int:
        match = re.search(r"(\d+)$", bundle_version_no)
        if match is None:
            return 0
        return int(match.group(1))

    @staticmethod
    def _version_sort_key(version_no: str) -> int:
        match = re.search(r"(\d+)$", version_no)
        if match is None:
            return 0
        return int(match.group(1))

    def _normalize_rule_content(
        self, *, kind: str, content: dict[str, object]
    ) -> dict[str, object]:
        if kind == "tax_profile":
            return self._normalize_tax_profile_content(content)
        return dict(content)

    def _normalize_tax_profile_content(
        self, content: dict[str, object]
    ) -> dict[str, object]:
        normalized = dict(content)

        company_name = self._first_non_empty_string(
            content.get("company_name"), content.get("buyer_name")
        )
        taxpayer_id = self._first_non_empty_string(
            content.get("taxpayer_id"), content.get("buyer_tax_no")
        )
        explicit_address = self._first_non_empty_string(content.get("buyer_address"))
        explicit_phone = self._first_non_empty_string(content.get("buyer_phone"))
        explicit_bank = self._first_non_empty_string(content.get("buyer_bank"))
        explicit_account = self._first_non_empty_string(content.get("buyer_account"))
        address_phone = self._first_non_empty_string(
            content.get("address_phone"),
            self._combine_parts(explicit_address, explicit_phone),
        )
        bank_account = self._first_non_empty_string(
            content.get("bank_account"),
            self._combine_parts(explicit_bank, explicit_account),
        )

        parsed_address, parsed_phone = self._split_address_phone(address_phone)
        parsed_bank, parsed_account = self._split_bank_account(bank_account)

        buyer_address = explicit_address or parsed_address
        buyer_phone = explicit_phone or parsed_phone
        buyer_bank = explicit_bank or parsed_bank
        buyer_account = explicit_account or parsed_account

        if company_name is not None:
            normalized["company_name"] = company_name
            normalized["buyer_name"] = company_name
        if taxpayer_id is not None:
            normalized["taxpayer_id"] = taxpayer_id
            normalized["buyer_tax_no"] = taxpayer_id
        if address_phone is not None:
            normalized["address_phone"] = address_phone
        if bank_account is not None:
            normalized["bank_account"] = bank_account
        if buyer_address is not None:
            normalized["buyer_address"] = buyer_address
        if buyer_phone is not None:
            normalized["buyer_phone"] = buyer_phone
        if buyer_bank is not None:
            normalized["buyer_bank"] = buyer_bank
        if buyer_account is not None:
            normalized["buyer_account"] = buyer_account

        return normalized

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
        if kind == "tax_profile":
            normalized = self._normalize_tax_profile_content(content)
            missing_fields: list[str] = []
            if self._is_missing_required_value(normalized.get("company_name")):
                missing_fields.append("company_name")
            if self._is_missing_required_value(normalized.get("taxpayer_id")):
                missing_fields.append("taxpayer_id")
            return missing_fields

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

    @staticmethod
    def _first_non_empty_string(*values: object) -> str | None:
        for value in values:
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    return trimmed
        return None

    @staticmethod
    def _combine_parts(left: str | None, right: str | None) -> str | None:
        if left and right:
            return f"{left} {right}"
        return left or right

    @staticmethod
    def _split_address_phone(value: str | None) -> tuple[str | None, str | None]:
        if value is None:
            return None, None
        trimmed = value.strip()
        if not trimmed:
            return None, None

        match = re.match(
            r"^(?P<address>.+?)\s+(?P<phone>(?:\+?\d[\d-]{5,}|\d{6,}))$",
            trimmed,
        )
        if not match:
            return trimmed, None
        return match.group("address").strip(), match.group("phone").strip()

    @staticmethod
    def _split_bank_account(value: str | None) -> tuple[str | None, str | None]:
        if value is None:
            return None, None
        trimmed = value.strip()
        if not trimmed:
            return None, None

        match = re.match(r"^(?P<bank>.+?)\s+(?P<account>[0-9A-Za-z]+)$", trimmed)
        if not match:
            return trimmed, None
        return match.group("bank").strip(), match.group("account").strip()
