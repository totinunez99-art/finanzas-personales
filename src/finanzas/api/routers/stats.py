"""Estadísticas simples del período para el dashboard (Sprint 2)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import User
from finanzas.core.services.reporting import stats_summary

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def summary(
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    account_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return stats_summary(db, user, period=period, account_id=account_id)
