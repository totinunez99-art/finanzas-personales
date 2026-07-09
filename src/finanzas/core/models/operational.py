"""Tablas operativas: importaciones, tasas, eventos, jobs, settings, correos sin parsear."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from finanzas.core.models.base import Base, CreatedAtMixin, UuidPkMixin


class ImportBatch(Base, UuidPkMixin, CreatedAtMixin):
    __tablename__ = "import_batches"
    # Reimportar el mismo archivo es no-op explícito (docs/03).
    __table_args__ = (UniqueConstraint("account_id", "file_sha256"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    connector: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str | None] = mapped_column(String(255))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_duplicated: Mapped[int] = mapped_column(Integer, default=0)
    rows_reconciled: Mapped[int] = mapped_column(Integer, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # ImportBatchStatus
    error_detail: Mapped[str | None] = mapped_column(Text)
    # Trazabilidad de parser (sesión 11, requisito CTO): qué versión produjo qué.
    parser_version: Mapped[str | None] = mapped_column(String(16))
    detected_format: Mapped[str | None] = mapped_column(String(64))
    validation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))


class ExchangeRate(Base, UuidPkMixin, CreatedAtMixin):
    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("date", "currency"),)

    date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))  # UF | USD
    rate_clp: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    source: Mapped[str] = mapped_column(String(64))


class DomainEvent(Base, UuidPkMixin, CreatedAtMixin):
    """Event log unificado (ADR-009). Append-only; payload = referencias, no copias."""

    __tablename__ = "domain_events"
    __table_args__ = (
        Index("ix_domain_events_entity", "entity", "entity_id"),
        Index("ix_domain_events_type_time", "event_type", "occurred_at"),
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    event_type: Mapped[str] = mapped_column(String(48))  # EventType (catálogo cerrado)
    entity: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    actor: Mapped[str] = mapped_column(String(64))  # system | user | job:<name>
    correlation_id: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class JobRun(Base, UuidPkMixin):
    __tablename__ = "job_runs"

    job_name: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(8), default="running")  # JobStatus
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class AppSetting(Base):
    """Flags dinámicos (docs/11 §2). El contrato vive en shared/flags.py."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB)  # envuelto: {"v": <valor>}
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(64))


class UnrecognizedFile(Base, UuidPkMixin, CreatedAtMixin):
    """Archivos que ningún parser reconoció (Import Wizard, docs/14).

    Guarda metadatos estructurales —no el contenido— para diseñar el parser
    faltante. El archivo original queda en manos del usuario.
    """

    __tablename__ = "unrecognized_files"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    extension: Mapped[str] = mapped_column(String(16))
    header_preview: Mapped[str | None] = mapped_column(String(500))  # primeras líneas, truncado
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|resolved


class UnparsedEmail(Base, UuidPkMixin, CreatedAtMixin):
    """Correos bancarios que ningún parser reconoció. Nunca se descartan (docs/05 §2)."""

    __tablename__ = "unparsed_emails"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    imap_uid: Mapped[str] = mapped_column(String(32))
    message_id: Mapped[str | None] = mapped_column(String(255))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subject: Mapped[str | None] = mapped_column(String(255))
    from_addr: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|resolved|ignored
