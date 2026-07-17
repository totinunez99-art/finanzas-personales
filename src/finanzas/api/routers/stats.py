"""Estadísticas e insights del período para el dashboard (Sprint 3)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from finanzas.api.deps import get_current_user, get_db
from finanzas.core.models import User
from finanzas.core.services.analytics import overview as analytics_overview
from finanzas.core.services.insights import generate_insights
from finanzas.core.services.reporting import financial_summary

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def summary(
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    account_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return financial_summary(db, user, period=period, account_id=account_id)


@router.get("/insights")
def insights(
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    account_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return [i.to_payload() for i in generate_insights(db, user, period, account_id)]


@router.get("/analytics")
def analytics(
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    account_id: uuid.UUID | None = Query(default=None),
    currency: str = Query(default="CLP", pattern="^(CLP|UF|USD)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return analytics_overview(db, user, period=period, account_id=account_id, currency=currency)
