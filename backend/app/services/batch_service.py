from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import AttachmentDocument, Batch, InvoiceRecord
from backend.app.services.config_service import ConfigService
from backend.app.services.storage_service import (
    DuplicateOriginalFileError,
    StorageService,
)


@dataclass(frozen=True)
class IncomingFile:
    filename: str
    content: bytes


class BatchService:
    def __init__(
        self,
        *,
        session: Session,
        storage_service: StorageService,
        config_service: ConfigService | None = None,
    ):
        self.session = session
        self.storage_service = storage_service
        self.config_service = config_service or ConfigService(session)

    def create_batch(
        self,
        *,
        files: list[IncomingFile],
        created_by: str,
        batch_no: str | None = None,
    ) -> Batch:
        if not files:
            raise ValueError("At least one file is required to create a batch.")

        batch_number = batch_no or self._generate_batch_no()
        self._assert_batch_import_is_allowed(batch_number=batch_number, files=files)
        snapshot = self.config_service.get_active_snapshot()
        invoice_file_count = sum(
            0 if self._looks_like_attachment(item.filename) else 1 for item in files
        )
        batch = Batch(
            batch_no=batch_number,
            created_by=created_by,
            status="queued",
            total_files=invoice_file_count,
            completed_files=0,
            processing_files=0,
            failed_files=0,
            tax_profile_version_id=self._snapshot_version_id(snapshot, "tax_profile"),
            business_rule_version_id=self._snapshot_version_id(
                snapshot, "business_rules"
            ),
            naming_rule_version_id=self._snapshot_version_id(snapshot, "naming_rules"),
            snapshot_json=json.dumps(snapshot, sort_keys=True),
        )

        try:
            self.session.add(batch)
            self.session.flush()

            for incoming_file in files:
                stored = self.storage_service.save_original(
                    batch_number, incoming_file.filename, incoming_file.content
                )
                if self._looks_like_attachment(incoming_file.filename):
                    attachment = AttachmentDocument(
                        batch_id=batch.id,
                        original_filename=stored.original_filename,
                        storage_path_original=stored.storage_path,
                        file_sha256=stored.file_sha256,
                        attachment_status="pending_match",
                    )
                    self.session.add(attachment)
                else:
                    invoice = InvoiceRecord(
                        batch_id=batch.id,
                        original_filename=stored.original_filename,
                        storage_path_original=stored.storage_path,
                        file_sha256=stored.file_sha256,
                        processing_status="queued",
                        review_status="not_reviewed",
                        artifact_status="original_only",
                    )
                    self.session.add(invoice)

            self.session.commit()
            self.session.refresh(batch)
            return batch
        except Exception:
            self.session.rollback()
            raise

    def _assert_batch_import_is_allowed(
        self, *, batch_number: str, files: list[IncomingFile]
    ) -> None:
        existing_batch = self.session.scalar(
            select(Batch).where(Batch.batch_no == batch_number)
        )
        if existing_batch is None:
            return

        existing_names = {
            name
            for name in self.session.scalars(
                select(InvoiceRecord.original_filename).where(
                    InvoiceRecord.batch_id == existing_batch.id
                )
            ).all()
        }
        existing_names.update(
            self.session.scalars(
                select(AttachmentDocument.original_filename).where(
                    AttachmentDocument.batch_id == existing_batch.id
                )
            ).all()
        )
        incoming_names = {incoming_file.filename for incoming_file in files}
        duplicate_names = sorted(existing_names.intersection(incoming_names))
        if duplicate_names:
            duplicate_list = ", ".join(duplicate_names)
            raise DuplicateOriginalFileError(
                f"Batch {batch_number!r} already contains immutable originals: {duplicate_list}."
            )
        raise ValueError(f"Batch number {batch_number!r} already exists.")

    @staticmethod
    def _snapshot_version_id(
        snapshot: dict[str, dict[str, object] | None], kind: str
    ) -> str | None:
        version = snapshot.get(kind)
        if version is None:
            return None
        version_id = version.get("id")
        return str(version_id) if version_id is not None else None

    @staticmethod
    def _generate_batch_no() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        suffix = uuid4().hex[:6]
        return f"BATCH-{timestamp}-{suffix}"

    @staticmethod
    def _looks_like_attachment(filename: str) -> bool:
        normalized = filename.casefold()
        attachment_keywords = ("清单", "销货清单", "明细", "附件", "list")
        return any(keyword in normalized for keyword in attachment_keywords)
