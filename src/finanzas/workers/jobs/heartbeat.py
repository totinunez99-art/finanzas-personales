"""Heartbeat: job trivial que valida el ciclo completo del worker.

Existe para que la infraestructura (scheduler → run_job → job_runs → página de
salud) sea verificable ANTES de tener jobs reales. Se elimina cuando el primer
job funcional lo reemplace como señal de vida.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finanzas.core.models import DomainEvent


def run(session: Session) -> dict[str, Any]:
    events = session.execute(select(func.count()).select_from(DomainEvent)).scalar()
    return {"domain_events_total": events}
