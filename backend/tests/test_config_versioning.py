import json

import pytest
from sqlalchemy import select

from backend.app.db.models import AuditLog, Batch, RuleVersion
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
    init_db,
)
from backend.app.services.batch_service import BatchService, IncomingFile
from backend.app.services.config_service import ConfigService
from backend.app.services.storage_service import StorageService


def build_session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'config.db'}"
    engine = create_database_engine(database_url)
    init_db(engine)
    return create_session_factory(engine)()


def test_config_versions_are_appended_and_audited(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    first = config_service.create_version(
        kind="tax_profile",
        content={"rate": "6%"},
        changed_by="fin-admin",
        change_summary="create initial tax profile",
        change_reason="bootstrap",
    )
    second = config_service.create_version(
        kind="tax_profile",
        content={"rate": "9%"},
        changed_by="fin-admin",
        change_summary="adjust tax profile",
        change_reason="policy update",
    )

    versions = session.scalars(
        select(RuleVersion)
        .where(RuleVersion.kind == "tax_profile")
        .order_by(RuleVersion.version_no)
    ).all()
    assert len(versions) == 2
    assert first.version_no == "v1"
    assert second.version_no == "v2"
    assert first.bundle_version_no == "b1"
    assert second.bundle_version_no == "b2"
    assert versions[0].is_active is False
    assert versions[1].is_active is True
    assert json.loads(versions[0].content_json) == {"rate": "6%"}
    assert json.loads(versions[1].content_json) == {"rate": "9%"}

    audit_logs = session.scalars(
        select(AuditLog).where(AuditLog.entity_type == "rule_version")
    ).all()
    assert len(audit_logs) == 6
    assert audit_logs[1].changed_by == "fin-admin"
    assert any(log.change_summary == "adjust tax profile" for log in audit_logs)
    assert any(log.change_reason == "policy update" for log in audit_logs)
    assert audit_logs[1].changed_at is not None


def test_batch_creation_binds_latest_active_rule_versions(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)
    storage_service = StorageService(tmp_path / "storage")
    batch_service = BatchService(
        session=session, storage_service=storage_service, config_service=config_service
    )

    config_service.create_version(
        kind="tax_profile",
        content={"rate": "6%"},
        changed_by="fin-admin",
        change_summary="initial tax profile",
        change_reason="bootstrap",
    )
    config_service.create_version(
        kind="tax_profile",
        content={"rate": "9%"},
        changed_by="fin-admin",
        change_summary="promote tax profile",
        change_reason="policy update",
    )
    config_service.create_version(
        kind="business_rules",
        content={"require_buyer_tax_no": True},
        changed_by="ops-admin",
        change_summary="enable buyer tax check",
        change_reason="tighten validation",
    )
    config_service.create_version(
        kind="naming_rules",
        content={"pattern": "{seller}_{date}_{amount}"},
        changed_by="ops-admin",
        change_summary="revise naming rule",
        change_reason="align archive format",
    )
    active_tax = config_service.get_latest_active("tax_profile")
    active_business = config_service.get_latest_active("business_rules")
    active_naming = config_service.get_latest_active("naming_rules")

    batch = batch_service.create_batch(
        files=[IncomingFile(filename="invoice.pdf", content=b"%PDF-1.7\ninvoice")],
        created_by="tester",
        batch_no="BATCH-CFG-001",
    )

    saved_batch = session.get(Batch, batch.id)
    assert saved_batch is not None
    assert active_tax is not None
    assert active_business is not None
    assert active_naming is not None
    assert saved_batch.tax_profile_version_id == active_tax.id
    assert saved_batch.business_rule_version_id == active_business.id
    assert saved_batch.naming_rule_version_id == active_naming.id
    assert saved_batch.config_bundle_version_no == active_naming.bundle_version_no

    snapshot = json.loads(saved_batch.snapshot_json)
    assert snapshot["tax_profile"]["id"] == active_tax.id
    assert snapshot["tax_profile"]["bundle_version_no"] == active_tax.bundle_version_no
    assert snapshot["business_rules"]["id"] == active_business.id
    assert snapshot["naming_rules"]["id"] == active_naming.id
    assert snapshot["naming_rules"]["content"]["pattern"] == "{seller}_{date}_{amount}"


def test_setup_status_requires_minimum_fields_for_required_rule_kinds(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    initial_status = config_service.get_setup_status()
    assert initial_status["complete"] is False
    assert initial_status["missing_required_fields"] == {
        "tax_profile": ["company_name", "taxpayer_id"],
        "business_rules": ["template_name"],
        "naming_rules": ["pattern"],
    }

    config_service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co"},
        changed_by="fin-admin",
        change_summary="incomplete tax profile",
        change_reason="test fixture",
    )
    config_service.create_version(
        kind="business_rules",
        content={},
        changed_by="ops-admin",
        change_summary="seed incomplete business rules",
        change_reason="test fixture",
    )
    config_service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="seed naming rules",
        change_reason="test fixture",
    )

    incomplete_status = config_service.get_setup_status()
    assert incomplete_status["complete"] is False
    assert incomplete_status["missing_required_fields"] == {
        "tax_profile": ["taxpayer_id"],
        "business_rules": ["template_name"],
        "naming_rules": [],
    }

    config_service.create_version(
        kind="business_rules",
        content={"template_name": "regular"},
        changed_by="ops-admin",
        change_summary="complete business rules",
        change_reason="test fixture",
    )

    config_service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000X"},
        changed_by="fin-admin",
        change_summary="complete tax profile",
        change_reason="test fixture",
    )

    complete_status = config_service.get_setup_status()
    assert complete_status["complete"] is True
    assert complete_status["missing_required_fields"] == {
        "tax_profile": [],
        "business_rules": [],
        "naming_rules": [],
    }


def test_setup_status_accepts_legacy_business_rules_shape(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    config_service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co", "buyer_tax_no": "91310000X"},
        changed_by="fin-admin",
        change_summary="complete tax profile",
        change_reason="test fixture",
    )
    config_service.create_version(
        kind="business_rules",
        content={"minimum_confidence": 0.75},
        changed_by="ops-admin",
        change_summary="legacy business rules",
        change_reason="test fixture",
    )
    config_service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="seed naming rules",
        change_reason="test fixture",
    )

    setup_status = config_service.get_setup_status()
    assert setup_status["complete"] is True
    assert setup_status["missing_required_fields"] == {
        "tax_profile": [],
        "business_rules": [],
        "naming_rules": [],
    }


def test_create_initial_setup_creates_three_active_versions_atomically(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    created_versions = config_service.create_initial_setup(
        tax_profile={
            "company_name": "Shanghai Example Co",
            "taxpayer_id": "91310000X",
            "address_phone": "Shanghai Pudong 021-12345678",
            "bank_account": "招商银行上海分行 1234567890",
        },
        business_rules={
            "template_name": "regular",
            "display_name": "常规模板",
            "minimum_confidence": 0.85,
        },
        naming_rules={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="首次配置",
        change_reason="首次配置向导",
    )

    assert set(created_versions.keys()) == {
        "tax_profile",
        "business_rules",
        "naming_rules",
    }

    versions = session.scalars(select(RuleVersion).order_by(RuleVersion.kind)).all()
    assert len(versions) == 3
    assert all(version.is_active is True for version in versions)
    assert [version.version_no for version in versions] == ["v1", "v1", "v1"]
    assert {version.bundle_version_no for version in versions} == {"b1"}

    setup_status = config_service.get_setup_status()
    assert setup_status["complete"] is True
    assert setup_status["missing_required_fields"] == {
        "tax_profile": [],
        "business_rules": [],
        "naming_rules": [],
    }


def test_create_initial_setup_rolls_back_everything_when_validation_fails(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    with pytest.raises(ValueError, match="minimum_confidence"):
        config_service.create_initial_setup(
            tax_profile={
                "buyer_name": "Shanghai Example Co",
                "buyer_tax_no": "91310000X",
            },
            business_rules={
                "template_name": "regular",
                "display_name": "常规模板",
                "minimum_confidence": "NaN",
            },
            naming_rules={"pattern": "{date}_{amount}_{number}"},
            changed_by="ops-admin",
            change_summary="首次配置",
            change_reason="首次配置向导",
        )

    assert session.scalars(select(RuleVersion)).all() == []
    assert session.scalars(select(AuditLog)).all() == []


def test_active_bundle_uses_shared_bundle_version_and_canonical_sections(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    config_service.create_initial_setup(
        tax_profile={
            "company_name": "Shanghai Example Co",
            "taxpayer_id": "91310000X",
        },
        business_rules={
            "template_name": "regular",
            "display_name": "常规模板",
            "minimum_confidence": 0.85,
        },
        naming_rules={"pattern": "{date}_{amount}_{number}"},
        changed_by="ops-admin",
        change_summary="首次配置",
        change_reason="首次配置向导",
    )
    config_service.create_version(
        kind="tax_profile",
        content={
            "company_name": "Shanghai Example Co",
            "taxpayer_id": "91310000Y",
        },
        changed_by="ops-admin",
        change_summary="更新税号",
        change_reason="财务资料变更",
    )

    active_bundle = config_service.get_active_bundle()
    assert active_bundle is not None
    assert active_bundle["bundle_version_no"] == "b2"
    assert active_bundle["profile"]["buyer_tax_no"] == "91310000Y"
    assert active_bundle["review_policy"]["template_name"] == "regular"
    assert active_bundle["naming_policy"]["pattern"] == "{date}_{amount}_{number}"
    assert active_bundle["component_versions"]["tax_profile"]["bundle_version_no"] == "b2"

    bundle_versions = config_service.list_bundle_versions()
    assert [item["bundle_version_no"] for item in bundle_versions] == ["b2", "b1"]


def test_tax_profile_is_normalized_to_buyer_profile_fields(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)

    version = config_service.create_version(
        kind="tax_profile",
        content={
            "company_name": "深信服科技股份有限公司",
            "taxpayer_id": "91440300726171773F",
            "address_phone": "深圳市南山区西丽街道西丽社区仙洞路16号深信服科技大厦7楼 26581949",
            "bank_account": "招商银行股份有限公司深圳高新园科创支行 811980479210001",
        },
        changed_by="fin-admin",
        change_summary="normalize tax profile",
        change_reason="test fixture",
    )

    saved_content = json.loads(version.content_json)
    assert saved_content["company_name"] == "深信服科技股份有限公司"
    assert saved_content["buyer_name"] == "深信服科技股份有限公司"
    assert saved_content["taxpayer_id"] == "91440300726171773F"
    assert saved_content["buyer_tax_no"] == "91440300726171773F"
    assert (
        saved_content["address_phone"]
        == "深圳市南山区西丽街道西丽社区仙洞路16号深信服科技大厦7楼 26581949"
    )
    assert saved_content["buyer_address"] == "深圳市南山区西丽街道西丽社区仙洞路16号深信服科技大厦7楼"
    assert saved_content["buyer_phone"] == "26581949"
    assert (
        saved_content["bank_account"]
        == "招商银行股份有限公司深圳高新园科创支行 811980479210001"
    )
    assert saved_content["buyer_bank"] == "招商银行股份有限公司深圳高新园科创支行"
    assert saved_content["buyer_account"] == "811980479210001"
