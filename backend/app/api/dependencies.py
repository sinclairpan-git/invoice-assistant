from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.db.session import get_db_session


def get_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    yield from get_db_session(session_factory)
