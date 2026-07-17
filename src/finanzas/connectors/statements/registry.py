"""Registro de parsers de cartola: la única lista que crece al agregar un banco."""

from finanzas.connectors.statements.base import DetectionResult, StatementParser
from finanzas.connectors.statements.edwards_cc_pdf import EdwardsCcPdfParser
from finanzas.connectors.statements.generic_csv import GenericCsvParser

_PARSERS: list[StatementParser] = [
    GenericCsvParser(),
    EdwardsCcPdfParser(),  # bloque 2: nace con sus casos golden (docs/13, docs/18)
]


def all_parsers() -> list[StatementParser]:
    return list(_PARSERS)


def detect(
    filename: str, content: bytes, password: str | None = None
) -> tuple[StatementParser, DetectionResult] | None:
    """Prueba todos los parsers y devuelve el de mayor confianza, o None."""
    best: tuple[StatementParser, DetectionResult] | None = None
    for parser in _PARSERS:
        result = parser.sniff(filename, content, password)
        if result is not None and (best is None or result.confidence > best[1].confidence):
            best = (parser, result)
    return best
