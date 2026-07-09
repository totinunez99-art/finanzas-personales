"""Contrato de parser de cartolas (Import Wizard, docs/14 + ajustes sesión 11).

Cada banco/formato = un parser independiente. El núcleo (ImportService) solo
conoce este contrato; agregar un banco no toca ninguna otra parte del sistema.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from finanzas.connectors.base import RawTransaction


@dataclass(frozen=True)
class DetectionResult:
    """Resultado de sniff(): 'este archivo parece mío, con esta confianza'."""

    parser_name: str
    bank: str
    confidence: float  # 0.0-1.0; el registry elige el máximo
    reason: str  # explicable en la UI ("encabezado coincide con ...")


@dataclass(frozen=True)
class ParserCapabilities:
    """Capacidades declaradas del conector (mensajes del wizard, integraciones futuras)."""

    file_types: tuple[str, ...]  # extensiones sin punto: ("csv",), ("pdf",)
    supports_password: bool = False
    provides_metadata: bool = False  # metadata estructurada del documento
    provides_balances: bool = False  # saldo inicial/final para cuadratura
    provides_account_hint: bool = False  # puede proponer la cuenta destino


@dataclass(frozen=True)
class ValidationCheck:
    """Un chequeo de integridad, con evidencia (auditable en la UI y en el batch)."""

    name: str  # ej: "cuadratura_global"
    passed: bool
    expected: str | None = None
    actual: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    checks: tuple[ValidationCheck, ...] = ()

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def to_payload(self) -> dict[str, Any]:
        """Serialización para import_batches.validation (jsonb)."""
        return {
            "passed": self.passed,
            "checks": [
                {"name": c.name, "passed": c.passed, "expected": c.expected, "actual": c.actual}
                for c in self.checks
            ],
        }


@dataclass(frozen=True)
class ImportResult:
    """Salida completa de un parser (reemplaza a ParsedStatement, sesión 11).

    extraction_confidence: proporción [0,1] de señales de calidad DETERMINISTAS
    satisfechas (quality_signals). No es probabilidad ni IA: es una medida
    documentada de cuán limpio fue el parseo. Las validaciones duras van en
    `validation` y su fallo impide importar; la confianza solo matiza.
    """

    transactions: list[RawTransaction]
    parser_version: str
    detected_format: str
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    validation: ValidationReport = field(default_factory=ValidationReport)
    warnings: list[str] = field(default_factory=list)
    extraction_confidence: float = 1.0
    quality_signals: dict[str, bool] = field(default_factory=dict)


def confidence_from_signals(signals: dict[str, bool]) -> float:
    """Fórmula única y documentada: proporción de señales satisfechas."""
    if not signals:
        return 1.0
    return round(sum(1 for v in signals.values() if v) / len(signals), 3)


class StatementParser(Protocol):
    name: str  # ej: "generic_csv_v1", "edwards_cc_pdf"
    bank: str  # ej: "generic", "edwards"
    capabilities: ParserCapabilities

    def sniff(
        self, filename: str, content: bytes, password: str | None = None
    ) -> DetectionResult | None:
        """None si el archivo no es de este parser. Nunca lanza excepciones."""
        ...

    def parse(self, filename: str, content: bytes, password: str | None = None) -> ImportResult:
        """Parsea TODO el archivo o lanza ParserError con mensaje accionable.
        Las validaciones duras fallidas DEBEN lanzar (nada parcial silencioso)."""
        ...
