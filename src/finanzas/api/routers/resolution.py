"""Resolution Pipeline vía HTTP (Sprint 3 B3, docs/22)."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import User
from finanzas.core.services.resolution import pipeline

router = APIRouter(prefix="/resolution", tags=["resolution"])


class RunRequest(BaseModel):
    resolvers: list[str] | None = None  # None = orden configurado (flag resolution.order)
    dry_run: bool = False


@router.post("/run")
def run(
    payload: RunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return pipeline.run(db, user, resolvers=payload.resolvers, dry_run=payload.dry_run)


@router.get("/resolvers")
def resolvers() -> dict[str, Any]:
    implemented = {"merchant", "category"}
    return {
        "available": list(pipeline.REGISTRY.keys()),
        "implemented": sorted(implemented),
        "stubs": sorted(set(pipeline.REGISTRY.keys()) - implemented),
        "default_order": pipeline.DEFAULT_ORDER,
    }
