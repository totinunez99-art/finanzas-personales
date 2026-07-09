"""Contrato de todo conector de ingesta (docs/05 §1).

Fase 1: solo la interfaz. Los conectores concretos (email IMAP, cartolas)
llegan cuando existan fixtures reales anonimizados — nunca antes.
"""

import enum
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


class SourceType(enum.StrEnum):
    EMAIL = "email"
    STATEMENT = "statement"
    API = "api"


@dataclass(frozen=True)
class RawTransaction:
    """Contrato único de salida de TODO conector. ImportService consume esto
    sin saber de dónde viene; agregar un banco o API = un conector nuevo."""

    account_hint: str
    posted_at: date
    amount: Decimal  # negativo = cargo
    currency: str
    description_raw: str
    source: SourceType
    source_ref: str
    occurred_at: datetime | None = None
    merchant_hint: str | None = None
    installment_raw: str | None = None  # "03/12" si aparece en el texto


@dataclass(frozen=True)
class FetchContext:
    """Parámetros de una corrida de ingesta (se amplía en la fase funcional)."""

    correlation_id: str


class Connector(Protocol):
    name: str
    source: SourceType

    def fetch(self, ctx: FetchContext) -> list[RawTransaction]: ...
