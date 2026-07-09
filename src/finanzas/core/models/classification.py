"""Motor de reglas y auditoría de decisiones de clasificación (ADR-008, docs/04)."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from finanzas.core.models.base import Base, CreatedAtMixin, UuidPkMixin


class ClassificationRule(Base, UuidPkMixin, CreatedAtMixin):
    __tablename__ = "classification_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    matcher_type: Mapped[str] = mapped_column(String(24))  # RuleMatcherType
    pattern: Mapped[str] = mapped_column(Text)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    origin: Mapped[str] = mapped_column(String(12))  # RuleOrigin
    hits_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # FK circular con decisions: se crea con use_alter (ver migración 0001).
    created_from_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("classification_decisions.id", use_alter=True)
    )


class AiCall(Base, UuidPkMixin, CreatedAtMixin):
    """Registro de toda llamada a un LLM (ADR-008). Reemplaza al viejo ai_usage."""

    __tablename__ = "ai_calls"

    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(64))  # la que reporta la API
    prompt_id: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(16))
    prompt_sha256: Mapped[str] = mapped_column(String(64))
    task: Mapped[str] = mapped_column(String(32))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(8))  # AiCallStatus
    error_detail: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ClassificationDecision(Base, UuidPkMixin, CreatedAtMixin):
    """Historial auditable: una fila por decisión sobre una transacción (ADR-008).

    Reglas duras (aplicadas por el service, único escritor):
    - una decisión rule/ai jamás supersede a una user;
    - el estado denormalizado en transactions se actualiza en la misma transacción DB.
    """

    __tablename__ = "classification_decisions"
    __table_args__ = (
        # A lo sumo UNA decisión vigente por transacción (concurrencia, docs/04 §9).
        Index(
            "uq_decision_current_per_tx",
            "transaction_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transactions.id"), index=True)
    decided_by: Mapped[str] = mapped_column(String(8))  # DecidedBy
    rule_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("classification_rules.id"))
    ai_call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_calls.id"))
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    merchant: Mapped[str | None] = mapped_column(String(120))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("classification_decisions.id")
    )
