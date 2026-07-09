"""Ejecución de jobs con tracking en job_runs (docs/07 §2).

Todo job pasa por run_job(): registro de inicio/fin/error, correlation_id
propio y evento job.failed ante error. Los jobs reciben una Session y
devuelven un dict de detalle; no manejan commit propio.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finanzas.core.db import session_scope
from finanzas.core.models import JobRun
from finanzas.core.models.enums import EventType, JobStatus
from finanzas.core.services.events import emit
from finanzas.shared.logging import bind_correlation_id, get_logger

logger = get_logger("workers")

JobFn = Callable[[Session], dict[str, Any]]


def _db_now(session: Session) -> datetime:
    """Hora desde Postgres: una sola fuente de tiempo (docs/10 §8)."""
    return session.execute(select(func.now())).scalar_one()


def run_job(job_name: str, fn: JobFn) -> None:
    bind_correlation_id()
    logger.info("job_started", job=job_name)

    # 1) Registrar inicio en su propia transacción: si el job muere, queda el rastro.
    with session_scope() as session:
        run = JobRun(job_name=job_name, status=JobStatus.RUNNING.value)
        session.add(run)
        session.flush()
        run_id = run.id

    # 2) Ejecutar el job y cerrar el registro en la misma transacción que su trabajo.
    try:
        with session_scope() as session:
            detail = fn(session)
            tracked = session.get(JobRun, run_id)
            if tracked is not None:
                tracked.status = JobStatus.OK.value
                tracked.detail = detail
                tracked.finished_at = _db_now(session)
        logger.info("job_finished", job=job_name, status="ok")
    except Exception as exc:
        logger.error("job_failed", job=job_name, error=str(exc), exc_info=True)
        with session_scope() as session:
            tracked = session.get(JobRun, run_id)
            if tracked is not None:
                tracked.status = JobStatus.ERROR.value
                tracked.detail = {"error": str(exc)[:500]}
                tracked.finished_at = _db_now(session)
            emit(
                session,
                EventType.JOB_FAILED,
                entity="job_run",
                entity_id=run_id,
                actor=f"job:{job_name}",
                payload={"error": str(exc)[:500]},
            )
