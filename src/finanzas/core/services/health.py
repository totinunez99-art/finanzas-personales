"""Servicio de salud y resumen de métricas (docs/10 §3, §5).

Fase 1: conectividad, versión de migración y estado de jobs. Las vistas
metrics_* llegan con las funcionalidades que las alimentan.
"""

from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from finanzas import __version__
from finanzas.core.models import DomainEvent, JobRun


def check_health(session: Session) -> dict[str, Any]:
    db_ok = session.execute(text("SELECT 1")).scalar() == 1
    try:
        migration = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        # DB accesible pero sin migrar: estado válido y visible, no un 500.
        session.rollback()
        migration = None
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "migration": migration,
        "version": __version__,
    }


def metrics_summary(session: Session) -> dict[str, Any]:
    # Última ejecución por job (estado de workers, docs/10 §3).
    latest = (
        select(
            JobRun.job_name,
            func.max(JobRun.started_at).label("last_started"),
        )
        .group_by(JobRun.job_name)
        .subquery()
    )
    rows = session.execute(
        select(JobRun).join(
            latest,
            (JobRun.job_name == latest.c.job_name) & (JobRun.started_at == latest.c.last_started),
        )
    ).scalars()
    jobs = [
        {
            "job": r.job_name,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
        }
        for r in rows
    ]
    events_count = session.execute(select(func.count()).select_from(DomainEvent)).scalar()
    return {"jobs": jobs, "domain_events_total": events_count}
