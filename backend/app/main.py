from __future__ import annotations

from fastapi import FastAPI

from backend.app.db.session import DEFAULT_DATABASE_URL, create_database_engine, create_session_factory, init_db


def create_app(database_url: str = DEFAULT_DATABASE_URL) -> FastAPI:
    engine = create_database_engine(database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)

    app = FastAPI(title="Invoice Assistant API", version="0.1.0")
    app.state.engine = engine
    app.state.session_factory = session_factory

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "invoice-assistant"}

    return app


app = create_app()
