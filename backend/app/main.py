from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from backend.app.api.batches import router as batches_router
from backend.app.api.config import router as config_router
from backend.app.api.invoices import router as invoices_router
from backend.app.db.session import BACKEND_ROOT, DEFAULT_DATABASE_URL, create_database_engine, create_session_factory, init_db
from backend.app.core.logging import get_app_logger
from backend.app.services.processing_runner import InProcessBatchRunner
from backend.app.services.recovery_service import RecoveryService


def resolve_storage_root(database_url: str) -> Path:
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        sqlite_path = Path(database_url.removeprefix("sqlite:///")).expanduser()
        return sqlite_path.parent / "storage"
    return BACKEND_ROOT / "data" / "storage"


def create_app(database_url: str = DEFAULT_DATABASE_URL) -> FastAPI:
    engine = create_database_engine(database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        session = session_factory()
        try:
            RecoveryService(
                session=session,
                processing_runner=app.state.processing_runner,
            ).recover_stale_jobs()
        finally:
            session.close()

        try:
            yield
        finally:
            app.state.processing_runner.shutdown()

    app = FastAPI(title="Invoice Assistant API", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.logger = get_app_logger()
    app.state.storage_root = resolve_storage_root(database_url)
    app.state.processing_runner = InProcessBatchRunner(
        session_factory=session_factory,
        storage_root=app.state.storage_root,
    )

    app.include_router(batches_router)
    app.include_router(invoices_router)
    app.include_router(config_router)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "invoice-assistant"}

    return app


app = create_app()
