from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_trusted_actor


router = APIRouter(prefix="/api", tags=["actors"])


@router.get("/me")
def get_current_actor(trusted_actor=Depends(get_trusted_actor)) -> dict[str, object]:
    return {"item": trusted_actor.to_dict()}
