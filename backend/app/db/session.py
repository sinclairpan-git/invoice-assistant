from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.models import Base


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = BACKEND_ROOT / "data" / "invoice_assistant.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"

SQLITE_ADDITIVE_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "batches": (
        ("active_job_id", "active_job_id VARCHAR(36)"),
        ("last_recovered_at", "last_recovered_at DATETIME"),
        ("last_stage_code", "last_stage_code VARCHAR(64)"),
        ("last_stage_text", "last_stage_text VARCHAR(255)"),
    ),
    "invoice_records": (
        ("processing_stage", "processing_stage VARCHAR(64) NOT NULL DEFAULT 'queued'"),
        ("last_attempt_id", "last_attempt_id VARCHAR(36)"),
        ("retry_count", "retry_count INTEGER NOT NULL DEFAULT 0"),
        ("last_error_stage", "last_error_stage VARCHAR(64)"),
        ("last_error_code", "last_error_code VARCHAR(64)"),
        ("last_error_message", "last_error_message TEXT"),
        ("retryable", "retryable BOOLEAN NOT NULL DEFAULT 0"),
    ),
    "document_evidence": (("attempt_id", "attempt_id VARCHAR(36)"),),
    "extracted_fields": (("attempt_id", "attempt_id VARCHAR(36)"),),
    "field_checks": (("attempt_id", "attempt_id VARCHAR(36)"),),
}

SQLITE_INDEX_DDLS = (
    "CREATE INDEX IF NOT EXISTS ix_batches_active_job_id ON batches (active_job_id)",
    "CREATE INDEX IF NOT EXISTS ix_invoice_records_last_attempt_id ON invoice_records (last_attempt_id)",
    "CREATE INDEX IF NOT EXISTS ix_document_evidence_attempt_id ON document_evidence (attempt_id)",
    "CREATE INDEX IF NOT EXISTS ix_extracted_fields_attempt_id ON extracted_fields (attempt_id)",
    "CREATE INDEX IF NOT EXISTS ix_field_checks_attempt_id ON field_checks (attempt_id)",
)


def create_database_engine(database_url: str = DEFAULT_DATABASE_URL) -> Engine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        sqlite_path = Path(database_url.removeprefix("sqlite:///")).expanduser()
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_additive_migrations(engine)


def _apply_sqlite_additive_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        for table_name, columns in SQLITE_ADDITIVE_COLUMNS.items():
            existing_columns = {
                row[1]
                for row in conn.exec_driver_sql(
                    f"PRAGMA table_info('{table_name}')"
                ).fetchall()
            }
            if not existing_columns:
                continue

            for column_name, ddl in columns:
                if column_name in existing_columns:
                    continue
                conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")
                existing_columns.add(column_name)

        for ddl in SQLITE_INDEX_DDLS:
            conn.exec_driver_sql(ddl)


def get_db_session(
    session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
