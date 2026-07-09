"""Transacción: tabla central del dominio (docs/03 §3)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from finanzas.core.models.base import Base, TimestampMixin, UuidPkMixin
from finanzas.core.models.enums import TransactionSource, TransactionStatus, values


def _in_list(column: str, options: list[str]) -> str:
    quoted = ", ".join(f"'{o}'" for o in options)
    return f"{column} IN ({quoted})"


class Transaction(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        # Idempotencia a nivel de DB: dos procesos no pueden duplicar (docs/03 §4).
        UniqueConstraint("account_id", "dedup_hash"),
        CheckConstraint(_in_list("status", values(TransactionStatus)), name="status_valid"),
        CheckConstraint(_in_list("source", values(TransactionSource)), name="source_valid"),
        # Similitud léxica para reconciliación y few-shot (docs/03 §5, ADR-007).
        Index(
            "ix_transactions_description_norm_trgm",
            "description_norm",
            postgresql_using="gin",
            postgresql_ops={"description_norm": "gin_trgm_ops"},
        ),
        Index("ix_transactions_account_posted", "account_id", "posted_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))

    posted_at: Mapped[date] = mapped_column(Date)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))  # negativo = cargo
    currency: Mapped[str] = mapped_column(String(3))

    description_raw: Mapped[str] = mapped_column(Text)  # inmutable: evidencia de origen
    description_norm: Mapped[str] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(120))

    # Estado ACTUAL de clasificación, denormalizado. Historial: classification_decisions
    # (ADR-008). Único escritor: el service de clasificación.
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    classified_by: Mapped[str | None] = mapped_column(String(8))  # DecidedBy
    classification_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    status: Mapped[str] = mapped_column(String(12))  # TransactionStatus (docs/03 §5)
    source: Mapped[str] = mapped_column(String(10))  # TransactionSource
    source_ref: Mapped[str] = mapped_column(Text)  # msg-id de correo o batch+fila

    dedup_hash: Mapped[str] = mapped_column(String(64))
    intra_day_seq: Mapped[int] = mapped_column(Integer, default=0)  # docs/03 §4, caso borde

    reconciled_with_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transactions.id"))
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("import_batches.id"))

    # Texto crudo de cuotas ("03/12") hasta que Fase 2 lo estructure (deuda D-02).
    installment_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
