"""Logging estructurado (docs/10 §2).

JSON en producción, consola legible en desarrollo. `correlation_id` viaja por
contextvars y aparece en todo log del mismo flujo (request, batch o job).
"""

import logging
import sys
import uuid

import structlog

from finanzas.shared.config import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    renderer: structlog.typing.Processor
    if settings.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(module: str) -> structlog.typing.FilteringBoundLogger:
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(module=module)
    return logger


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def bind_correlation_id(correlation_id: str | None = None) -> str:
    """Fija el correlation_id del contexto actual y lo devuelve."""
    cid = correlation_id or new_correlation_id()
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    return cid
