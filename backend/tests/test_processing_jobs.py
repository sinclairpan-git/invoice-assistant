from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.models import Batch, InvoiceRecord, ProcessingAttempt, ProcessingJob
from backend.app.db.session import create_database_engine, create_session_factory, init_db
from backend.app.main import create_app


def build_session(tmp_path, name: str = "processing-jobs.db"):
    engine = create_database_engine(f"sqlite:///{tmp_path / name}")
    init_db(engine)
    return create_session_factory(engine)()


def test_processing_job_schema_is_created_and_runtime_columns_are_present(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    app = create_app(database_url)

    inspector = inspect(app.state.engine)
    table_names = set(inspector.get_table_names())

    assert {"processing_jobs", "processing_attempts"}.issubset(table_names)

    batch_columns = {column["name"] for column in inspector.get_columns("batches")}
    assert {"active_job_id", "last_recovered_at", "last_stage_code", "last_stage_text"}.issubset(batch_columns)

    invoice_columns = {column["name"] for column in inspector.get_columns("invoice_records")}
    assert {
        "processing_stage",
        "last_attempt_id",
        "retry_count",
        "last_error_stage",
        "last_error_code",
        "last_error_message",
        "retryable",
    }.issubset(invoice_columns)

    for table_name in ("document_evidence", "extracted_fields", "field_checks"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "attempt_id" in columns


def test_processing_job_attempt_relationships_and_current_attempt_pointer(tmp_path):
    session = build_session(tmp_path)

    batch = Batch(batch_no="BATCH-JOB-001", created_by="tester", snapshot_json="{}")
    session.add(batch)
    session.flush()

    invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="invoice-001.pdf",
        storage_path_original="storage/originals/BATCH-JOB-001/invoice-001.pdf",
        file_sha256="a" * 64,
        invoice_amount=Decimal("88.00"),
        processing_status="processing",
        processing_stage="ocr",
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
    )
    session.add(invoice)
    session.flush()

    job = ProcessingJob(
        batch_id=batch.id,
        status="running",
        current_stage="extracting",
        total_items=1,
        completed_items=0,
        failed_items=0,
        recovery_token="recovery-batch-job-001",
    )
    session.add(job)
    session.flush()

    attempt = ProcessingAttempt(
        job_id=job.id,
        invoice_id=invoice.id,
        attempt_no=1,
        status="running",
        stage="extracting",
        parse_source="pdf_text",
        provider_name="pypdf",
        provider_version="1.0.0",
        input_sha256="b" * 64,
    )
    session.add(attempt)
    session.flush()

    batch.active_job_id = job.id
    batch.last_stage_code = "extracting"
    batch.last_stage_text = "文本抽取中"
    invoice.last_attempt_id = attempt.id
    invoice.retry_count = 1
    invoice.last_error_stage = "extracting"
    invoice.last_error_code = "TEMP_PROVIDER_ERROR"
    invoice.last_error_message = "provider timeout"
    invoice.retryable = True

    session.commit()
    session.refresh(batch)
    session.refresh(invoice)
    session.refresh(job)
    session.refresh(attempt)

    assert batch.active_job_id == job.id
    assert batch.last_stage_code == "extracting"
    assert batch.processing_jobs[0].id == job.id

    assert invoice.last_attempt_id == attempt.id
    assert invoice.retry_count == 1
    assert invoice.retryable is True
    assert invoice.processing_attempts[0].id == attempt.id

    assert job.batch_id == batch.id
    assert job.attempts[0].id == attempt.id
    assert attempt.invoice_id == invoice.id
    assert attempt.job_id == job.id


def test_processing_attempt_invoice_attempt_no_is_unique(tmp_path):
    session = build_session(tmp_path)

    batch = Batch(batch_no="BATCH-JOB-UNIQUE", created_by="tester", snapshot_json="{}")
    session.add(batch)
    session.flush()

    invoice = InvoiceRecord(
        batch_id=batch.id,
        original_filename="invoice-duplicate.pdf",
        storage_path_original="storage/originals/BATCH-JOB-UNIQUE/invoice-duplicate.pdf",
        file_sha256="c" * 64,
        review_status="not_reviewed",
        artifact_status="original_only",
        duplicate_flag=False,
        risk_flags="[]",
    )
    session.add(invoice)
    session.flush()

    job_one = ProcessingJob(batch_id=batch.id, recovery_token="recovery-unique-1")
    job_two = ProcessingJob(batch_id=batch.id, recovery_token="recovery-unique-2")
    session.add_all([job_one, job_two])
    session.flush()

    session.add_all(
        [
            ProcessingAttempt(job_id=job_one.id, invoice_id=invoice.id, attempt_no=1),
            ProcessingAttempt(job_id=job_two.id, invoice_id=invoice.id, attempt_no=1),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_init_db_adds_runtime_columns_to_legacy_sqlite_schema(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'legacy.db'}")

    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE batches (
                id VARCHAR(36) PRIMARY KEY,
                batch_no VARCHAR(64) NOT NULL,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL,
                total_files INTEGER NOT NULL DEFAULT 0,
                completed_files INTEGER NOT NULL DEFAULT 0,
                processing_files INTEGER NOT NULL DEFAULT 0,
                failed_files INTEGER NOT NULL DEFAULT 0,
                suggested_pass_count INTEGER NOT NULL DEFAULT 0,
                suggested_pass_total_amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
                snapshot_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE invoice_records (
                id VARCHAR(36) PRIMARY KEY,
                batch_id VARCHAR(36) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                renamed_filename VARCHAR(255),
                storage_path_original VARCHAR(512) NOT NULL,
                storage_path_renamed VARCHAR(512),
                file_sha256 VARCHAR(64) NOT NULL,
                invoice_code VARCHAR(64),
                invoice_number VARCHAR(64),
                seller_name VARCHAR(255),
                buyer_name VARCHAR(255),
                buyer_tax_no VARCHAR(64),
                invoice_date DATE,
                invoice_amount NUMERIC(18, 2),
                parse_source VARCHAR(64),
                processing_status VARCHAR(32) NOT NULL DEFAULT 'queued',
                system_decision VARCHAR(32),
                review_status VARCHAR(32) NOT NULL DEFAULT 'not_reviewed',
                artifact_status VARCHAR(32) NOT NULL DEFAULT 'original_only',
                duplicate_flag BOOLEAN NOT NULL DEFAULT 0,
                duplicate_group_key VARCHAR(128),
                risk_flags TEXT NOT NULL DEFAULT '[]',
                display_status VARCHAR(64),
                problem_count INTEGER NOT NULL DEFAULT 0,
                failure_reason TEXT,
                UNIQUE(batch_id, original_filename)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE document_evidence (
                id VARCHAR(36) PRIMARY KEY,
                invoice_id VARCHAR(36) NOT NULL,
                source_type VARCHAR(64) NOT NULL,
                raw_text TEXT,
                pages_json TEXT NOT NULL DEFAULT '[]',
                text_blocks_json TEXT NOT NULL DEFAULT '[]',
                table_lines_json TEXT NOT NULL DEFAULT '[]',
                field_candidates_json TEXT NOT NULL DEFAULT '[]',
                confidence_summary_json TEXT NOT NULL DEFAULT '{}',
                provider_name VARCHAR(128),
                provider_version VARCHAR(64),
                provider_error_code VARCHAR(64)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE extracted_fields (
                id VARCHAR(36) PRIMARY KEY,
                invoice_id VARCHAR(36) NOT NULL,
                field_name VARCHAR(64) NOT NULL,
                extracted_value TEXT,
                normalized_value TEXT,
                confidence NUMERIC(5, 4),
                page_no INTEGER,
                source_fragment TEXT,
                bbox_json TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE field_checks (
                id VARCHAR(36) PRIMARY KEY,
                invoice_id VARCHAR(36) NOT NULL,
                field_name VARCHAR(64) NOT NULL,
                expected_value TEXT,
                actual_value TEXT,
                match_result VARCHAR(32) NOT NULL,
                reason TEXT NOT NULL
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO batches (
                id, batch_no, created_at, created_by, status, total_files, completed_files,
                processing_files, failed_files, suggested_pass_count, suggested_pass_total_amount, snapshot_json
            ) VALUES (
                'batch-legacy', 'BATCH-LEGACY-001', '2026-04-17T00:00:00+00:00', 'tester', 'queued',
                1, 0, 0, 0, 0, 0, '{}'
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO invoice_records (
                id, batch_id, original_filename, storage_path_original, file_sha256,
                processing_status, review_status, artifact_status, duplicate_flag, risk_flags
            ) VALUES (
                'invoice-legacy', 'batch-legacy', 'legacy.pdf',
                'storage/originals/BATCH-LEGACY-001/legacy.pdf', 'd' || substr('dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 2),
                'queued', 'not_reviewed', 'original_only', 0, '[]'
            )
            """
        )

    init_db(engine)

    inspector = inspect(engine)
    assert {"processing_jobs", "processing_attempts"}.issubset(set(inspector.get_table_names()))

    invoice_columns = {column["name"] for column in inspector.get_columns("invoice_records")}
    assert {"processing_stage", "last_attempt_id", "retry_count", "retryable"}.issubset(invoice_columns)

    batch_columns = {column["name"] for column in inspector.get_columns("batches")}
    assert {"active_job_id", "last_recovered_at", "last_stage_code", "last_stage_text"}.issubset(batch_columns)

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT processing_stage, retry_count, retryable
                FROM invoice_records
                WHERE id = 'invoice-legacy'
                """
            )
        ).one()

    assert row.processing_stage == "queued"
    assert row.retry_count == 0
    assert row.retryable == 0
