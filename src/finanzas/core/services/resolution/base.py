"""Contrato ÚNICO de todo resolver del Resolution Pipeline (Sprint 3 B3, docs/22).

Merchant, Category, Recurring, Subscription, Anomaly e IA implementan ESTA
interfaz. Ningún resolver tiene privilegios: reciben la transacción y el
contexto, proponen cambios, y el PIPELINE aplica, audita y cronometra.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy.orm import Session

from finanzas.core.models import Transaction, User
from finanzas.core.models.enums import EventType


@dataclass
class ResolutionContext:
    """Estado compartido de una corrida del pipeline. Los resolvers cachean aquí
    (reglas, comercios conocidos, categorías) vía prepare(); jamás en globals."""

    session: Session
    user: User
    dry_run: bool = False
    cache: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EventSpec:
    """Evento a emitir SI el pipeline aplica los cambios (nunca en dry-run)."""

    event_type: EventType
    entity: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ResolutionResult:
    """Salida uniforme de cualquier resolver (requisito del dueño, sesión 16)."""

    resolver: str
    changes: dict[str, Any] = field(default_factory=dict)  # campo → nuevo valor
    confidence: Decimal | None = None
    explanation: list[dict[str, str]] = field(default_factory=list)  # factores
    evidence: dict[str, Any] = field(default_factory=dict)  # regla/patrón/historial usados
    events: tuple[EventSpec, ...] = ()
    duration_ms: float = 0.0  # la cronometra el pipeline, no el resolver
    skipped_reason: str | None = None  # ej: "protegido: corrección del usuario"

    @property
    def applied_anything(self) -> bool:
        return bool(self.changes)

    def to_payload(self) -> dict[str, Any]:
        return {
            "resolver": self.resolver,
            "changes": {k: str(v) for k, v in self.changes.items()},
            "confidence": str(self.confidence) if self.confidence is not None else None,
            "explanation": self.explanation,
            "evidence": {k: str(v) for k, v in self.evidence.items()},
            "duration_ms": round(self.duration_ms, 2),
            "skipped_reason": self.skipped_reason,
        }


NO_CHANGES = ResolutionResult(resolver="noop")


class Resolver(Protocol):
    """Interfaz única. resolve() NO muta la transacción ni la DB: propone.
    El pipeline aplica los cambios, emite los eventos y llama on_applied()."""

    name: str

    def prepare(self, ctx: ResolutionContext) -> None:
        """Carga caches/semillas en el contexto. Idempotente."""
        ...

    def resolve(self, tx: Transaction, ctx: ResolutionContext) -> ResolutionResult: ...

    def on_applied(self, tx: Transaction, ctx: ResolutionContext, result: ResolutionResult) -> None:
        """Efectos posteriores (ej: hits_count). Solo fuera de dry-run."""
        ...


def make_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)
