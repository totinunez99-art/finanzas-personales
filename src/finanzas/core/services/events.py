"""Emisión de eventos de dominio (ADR-009).

emit() agrega el evento a la MISMA sesión que la mutación: evento y cambio se
confirman (o revierten) juntos. No hace commit; eso es del dueño de la sesión.
"""

import uuid
from typing import Any

import structlog
from sqlalchemy.orm import Session

from finanzas.core.models import DomainEvent
from finanzas.core.models.enums import EventType


def emit(
    session: Session,
    event_type: EventType,
    entity: str,
    entity_id: uuid.UUID | None = None,
    actor: str = "system",
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> DomainEvent:
    if correlation_id is None:
        # Reutiliza el correlation_id del contexto de logging si existe (docs/10 §2).
        ctx = structlog.contextvars.get_contextvars()
        raw = ctx.get("correlation_id")
        correlation_id = raw if isinstance(raw, str) else None

    event = DomainEvent(
        event_type=event_type.value,
        entity=entity,
        entity_id=entity_id,
        actor=actor,
        payload=payload,
        correlation_id=correlation_id,
    )
    session.add(event)
    return event
