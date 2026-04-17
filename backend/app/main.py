from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.batches import router as batches_router
from backend.app.api.config import router as config_router
from backend.app.api.invoices import router as invoices_router
from backend.app.db.session import DEFAULT_DATABASE_URL, create_database_engine, create_session_factory, init_db
from backend.app.core.logging import get_app_logger


def create_app(database_url: str = DEFAULT_DATABASE_URL) -> FastAPI:
    engine = create_database_engine(database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)

    app = FastAPI(title="Invoice Assistant API", version="0.1.0")
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.logger = get_app_logger()

    app.include_router(batches_router)
    app.include_router(invoices_router)
    app.include_router(config_router)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "invoice-assistant"}

    return app


app = create_app()
