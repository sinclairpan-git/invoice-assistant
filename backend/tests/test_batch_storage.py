import json

import pytest

from backend.app.db.models import AttachmentDocument, Batch, InvoiceRecord
from backend.app.db.session import (
    create_database_engine,
    create_session_factory,
    init_db,
)
from backend.app.services.batch_service import BatchService, IncomingFile
from backend.app.services.config_service import ConfigService
from backend.app.services.storage_service import (
    DuplicateOriginalFileError,
    InvalidFileTypeError,
    StorageService,
)


def build_session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'batch.db'}"
    engine = create_database_engine(database_url)
    init_db(engine)
    return create_session_factory(engine)()


def seed_active_rules(config_service: ConfigService) -> None:
    config_service.create_version(
        kind="tax_profile",
        content={"mode": "standard"},
        changed_by="tester",
        change_summary="seed tax profile",
        change_reason="test fixture",
    )
    config_service.create_version(
        kind="business_rules",
        content={"allow_personal": False},
        changed_by="tester",
        change_summary="seed business rules",
        change_reason="test fixture",
    )
    config_service.create_version(
        kind="naming_rules",
        content={"pattern": "{date}_{number}"},
        changed_by="tester",
        change_summary="seed naming rules",
        change_reason="test fixture",
    )


def test_batch_service_stores_original_files_and_rule_snapshot(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)
    seed_active_rules(config_service)
    storage_service = StorageService(tmp_path / "storage")
    batch_service = BatchService(
        session=session, storage_service=storage_service, config_service=config_service
    )

    batch = batch_service.create_batch(
        files=[
            IncomingFile(filename="invoice-a.pdf", content=b"%PDF-1.7\ninvoice-a"),
            IncomingFile(filename="invoice-b.pdf", content=b"%PDF-1.7\ninvoice-b"),
        ],
        created_by="tester",
        batch_no="BATCH-TEST-001",
    )

    stored_dir = tmp_path / "storage" / "originals" / "BATCH-TEST-001"
    assert stored_dir.exists()
    assert (stored_dir / "invoice-a.pdf").exists()
    assert (stored_dir / "invoice-b.pdf").exists()

    saved_batch = session.get(Batch, batch.id)
    assert saved_batch is not None
    assert saved_batch.total_files == 2
    snapshot = json.loads(saved_batch.snapshot_json)
    assert snapshot["tax_profile"]["version_no"] == "v1"
    assert snapshot["business_rules"]["id"] == saved_batch.business_rule_version_id
    assert snapshot["naming_rules"]["content"]["pattern"] == "{date}_{number}"

    invoice_records = (
        session.query(InvoiceRecord).filter(InvoiceRecord.batch_id == batch.id).all()
    )
    assert len(invoice_records) == 2
    assert {record.storage_path_original for record in invoice_records} == {
        "storage/originals/BATCH-TEST-001/invoice-a.pdf",
        "storage/originals/BATCH-TEST-001/invoice-b.pdf",
    }


def test_batch_service_separates_attachment_candidates_from_invoice_records(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)
    seed_active_rules(config_service)
    storage_service = StorageService(tmp_path / "storage")
    batch_service = BatchService(
        session=session, storage_service=storage_service, config_service=config_service
    )

    batch = batch_service.create_batch(
        files=[
            IncomingFile(
                filename="invoice-main.pdf", content=b"%PDF-1.7\ninvoice-main"
            ),
            IncomingFile(
                filename="invoice-main-销货清单.pdf", content=b"%PDF-1.7\nattachment"
            ),
        ],
        created_by="tester",
        batch_no="BATCH-ATTACH-001",
    )

    invoice_records = (
        session.query(InvoiceRecord).filter(InvoiceRecord.batch_id == batch.id).all()
    )
    attachment_documents = (
        session.query(AttachmentDocument)
        .filter(AttachmentDocument.batch_id == batch.id)
        .all()
    )
    saved_batch = session.get(Batch, batch.id)

    assert saved_batch is not None
    assert saved_batch.total_files == 1
    assert len(invoice_records) == 1
    assert invoice_records[0].original_filename == "invoice-main.pdf"

    assert len(attachment_documents) == 1
    assert attachment_documents[0].original_filename == "invoice-main-销货清单.pdf"
    assert attachment_documents[0].attachment_status == "pending_match"
    assert (
        attachment_documents[0].storage_path_original
        == "storage/originals/BATCH-ATTACH-001/invoice-main-销货清单.pdf"
    )


def test_batch_service_rejects_duplicate_original_import(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)
    seed_active_rules(config_service)
    storage_service = StorageService(tmp_path / "storage")
    batch_service = BatchService(
        session=session, storage_service=storage_service, config_service=config_service
    )

    batch_service.create_batch(
        files=[IncomingFile(filename="invoice.pdf", content=b"%PDF-1.7\ninvoice")],
        created_by="tester",
        batch_no="BATCH-DUP-001",
    )

    with pytest.raises(DuplicateOriginalFileError):
        batch_service.create_batch(
            files=[
                IncomingFile(filename="invoice.pdf", content=b"%PDF-1.7\ninvoice-copy")
            ],
            created_by="tester",
            batch_no="BATCH-DUP-001",
        )


def test_batch_service_rejects_illegal_file_types(tmp_path):
    session = build_session(tmp_path)
    config_service = ConfigService(session)
    seed_active_rules(config_service)
    storage_service = StorageService(tmp_path / "storage")
    batch_service = BatchService(
        session=session, storage_service=storage_service, config_service=config_service
    )

    with pytest.raises(InvalidFileTypeError):
        batch_service.create_batch(
            files=[IncomingFile(filename="invoice.txt", content=b"plain text")],
            created_by="tester",
            batch_no="BATCH-BAD-001",
        )
