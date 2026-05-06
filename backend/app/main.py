from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.dependencies import CONTROLLED_ROLES
from backend.app.api.actors import router as actors_router
from backend.app.api.batches import router as batches_router
from backend.app.api.config import router as config_router
from backend.app.api.runtime import router as runtime_router
from backend.app.core.runtime_config import build_runtime_config
from backend.app.api.invoices import router as invoices_router
from backend.app.db.session import (
    BACKEND_ROOT,
    DEFAULT_DATABASE_URL,
    create_database_engine,
    create_session_factory,
    init_db,
)
from backend.app.core.logging import get_app_logger
from backend.app.services.processing_runner import InProcessBatchRunner
from backend.app.services.recovery_service import RecoveryService

LOCAL_TRUSTED_ACTOR = {
    "actor_id": "local-admin",
    "display_name": "本机管理员",
    "roles": list(CONTROLLED_ROLES),
}


def resolve_storage_root(database_url: str) -> Path:
    if database_url.startswith("sqlite:///") and database_url != "sqlite:///:memory:":
        sqlite_path = Path(database_url.removeprefix("sqlite:///")).expanduser()
        return sqlite_path.parent / "storage"
    return BACKEND_ROOT / "data" / "storage"


def configure_trusted_actor(
    app: FastAPI, actor_payload: dict[str, object] = LOCAL_TRUSTED_ACTOR
) -> None:
    app.state.trusted_actor = dict(actor_payload)


def create_app(
    database_url: str = DEFAULT_DATABASE_URL,
    *,
    trusted_actor: dict[str, object] | None = LOCAL_TRUSTED_ACTOR,
    runtime_overrides: dict[str, object] | None = None,
) -> FastAPI:
    runtime_config = build_runtime_config(
        database_url,
        backend_root=BACKEND_ROOT,
        overrides=runtime_overrides,
    )
    engine = create_database_engine(runtime_config.database_url)
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

    app = FastAPI(title="Invoice Assistant API", version="0.5.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.logger = get_app_logger()
    app.state.runtime_config = runtime_config
    app.state.storage_root = runtime_config.storage_root
    app.state.processing_runner = InProcessBatchRunner(
        session_factory=session_factory,
        storage_root=app.state.storage_root,
    )
    if trusted_actor is not None:
        configure_trusted_actor(app, trusted_actor)

    app.include_router(actors_router)
    app.include_router(batches_router)
    app.include_router(invoices_router)
    app.include_router(config_router)
    app.include_router(runtime_router)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "invoice-assistant"}

    _configure_release_frontend(app)

    return app


def _configure_release_frontend(app: FastAPI) -> None:
    runtime_config = app.state.runtime_config
    frontend_static_dir = runtime_config.frontend_static_dir
    if frontend_static_dir is None:
        return

    index_file = frontend_static_dir / "index.html"
    assets_dir = frontend_static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="release-assets")
    if not index_file.is_file():
        return

    @app.get("/", include_in_schema=False)
    async def spa_root() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{frontend_path:path}", include_in_schema=False)
    async def spa_fallback(frontend_path: str) -> FileResponse:
        if _is_reserved_backend_path(frontend_path):
            raise _not_found()
        return FileResponse(index_file)


def _is_reserved_backend_path(frontend_path: str) -> bool:
    reserved_prefixes = (
        "api",
        "health",
        "openapi.json",
        "docs",
        "redoc",
    )
    return any(
        frontend_path == prefix or frontend_path.startswith(f"{prefix}/")
        for prefix in reserved_prefixes
    )


def _not_found():
    from fastapi import HTTPException

    return HTTPException(status_code=404, detail="Not Found")


app = create_app()
