"""Scheduler del worker (ADR-005): APScheduler en proceso propio.

Registro central de jobs. Cada job corre vía run_job() (tracking + eventos).
`misfire_grace_time` amplio: el PC no corre 24/7, al arrancar se ejecuta lo
atrasado (docs/07 §2).
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from finanzas.shared.config import get_settings
from finanzas.shared.logging import configure_logging, get_logger
from finanzas.workers import runner
from finanzas.workers.jobs import heartbeat

logger = get_logger("scheduler")

# (nombre, función, trigger). Los jobs reales (sync_email, fetch_exchange_rates,
# classify_pending, daily_backup) se agregan aquí en la fase funcional.
JOBS = [
    ("heartbeat", heartbeat.run, IntervalTrigger(minutes=5)),
]


def main() -> None:
    settings = get_settings()
    configure_logging(settings)

    # Guarda de arranque: jamás tocar tablas sin DB lista y migrada (docs/15).
    # Compose ya lo garantiza por orden; esto protege arranques manuales.
    from finanzas.core.db import assert_migrated, wait_for_db

    try:
        wait_for_db(timeout_seconds=60)
        assert_migrated()
    except Exception as exc:
        logger.error("worker_startup_blocked", detail=str(exc))
        raise SystemExit(1) from exc

    scheduler = BlockingScheduler(timezone=settings.timezone)

    for name, fn, trigger in JOBS:
        scheduler.add_job(
            runner.run_job,
            trigger=trigger,
            args=(name, fn),
            id=name,
            max_instances=1,          # lock: nunca dos instancias del mismo job
            coalesce=True,            # ejecuciones atrasadas colapsan en una
            misfire_grace_time=3600,  # catch-up al encender el PC
        )
        # Además, una pasada inmediata al arrancar (docs/07 §2).
        scheduler.add_job(runner.run_job, args=(name, fn), id=f"{name}_startup")

    logger.info("scheduler_started", jobs=[name for name, _, _ in JOBS])
    scheduler.start()


if __name__ == "__main__":
    main()
