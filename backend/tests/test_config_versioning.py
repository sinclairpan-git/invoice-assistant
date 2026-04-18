import json

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
    assert versions[0].is_active is False
    assert versions[1].is_active is True
    assert json.loads(versions[0].content_json) == {"rate": "6%"}
    assert json.loads(versions[1].content_json) == {"rate": "9%"}

    audit_logs = session.scalars(
        select(AuditLog).where(AuditLog.entity_type == "rule_version")
    ).all()
    assert len(audit_logs) == 2
    assert audit_logs[1].changed_by == "fin-admin"
    assert audit_logs[1].change_summary == "adjust tax profile"
    assert audit_logs[1].change_reason == "policy update"
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
    latest_tax = config_service.create_version(
        kind="tax_profile",
        content={"rate": "9%"},
        changed_by="fin-admin",
        change_summary="promote tax profile",
        change_reason="policy update",
    )
    latest_business = config_service.create_version(
        kind="business_rules",
        content={"require_buyer_tax_no": True},
        changed_by="ops-admin",
        change_summary="enable buyer tax check",
        change_reason="tighten validation",
    )
    latest_naming = config_service.create_version(
        kind="naming_rules",
        content={"pattern": "{seller}_{date}_{amount}"},
        changed_by="ops-admin",
        change_summary="revise naming rule",
        change_reason="align archive format",
    )

    batch = batch_service.create_batch(
        files=[IncomingFile(filename="invoice.pdf", content=b"%PDF-1.7\ninvoice")],
        created_by="tester",
        batch_no="BATCH-CFG-001",
    )

    saved_batch = session.get(Batch, batch.id)
    assert saved_batch is not None
    assert saved_batch.tax_profile_version_id == latest_tax.id
    assert saved_batch.business_rule_version_id == latest_business.id
    assert saved_batch.naming_rule_version_id == latest_naming.id

    snapshot = json.loads(saved_batch.snapshot_json)
    assert snapshot["tax_profile"]["version_no"] == "v2"
    assert snapshot["business_rules"]["id"] == latest_business.id
    assert snapshot["naming_rules"]["content"]["pattern"] == "{seller}_{date}_{amount}"
