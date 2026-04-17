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


def get_db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
