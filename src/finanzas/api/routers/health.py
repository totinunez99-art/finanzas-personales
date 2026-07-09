"""Endpoints de salud y resumen de métricas (docs/10 §5)."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from finanzas.api.deps import get_db
from finanzas.core.services.health import check_health, metrics_summary
from finanzas.core.services.settings_service import SettingsService

router = APIRouter(tags=["health"])
_settings_service = SettingsService()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    return check_health(db)


@router.get("/metrics/summary")
def metrics(db: Session = Depends(get_db)) -> dict[str, Any]:
    summary = metrics_summary(db)
    summary["flags_non_default"] = _settings_service.non_default(db)
    return summary
