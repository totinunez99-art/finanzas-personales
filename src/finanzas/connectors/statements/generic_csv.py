"""Conector CSV de referencia (formato propio documentado).

Doble propósito:
1. Puente inmediato: cualquier cartola convertida a este formato entra al sistema HOY.
2. Implementación de referencia del contrato StatementParser para los conectores
   bancarios reales (bancochile llegará con sus casos golden, docs/13).

Formato (delimitador ';' o ','):
    fecha;descripcion;monto[;moneda]
    2026-06-01;COMPRA LIDER;-12.345[;CLP]

- fecha: YYYY-MM-DD, DD-MM-YYYY o DD/MM/YYYY.
- monto: signo explícito para cargos; separadores chilenos aceptados (reglas abajo).
- moneda: opcional; vacía = moneda de la cuenta destino.
"""

import csv
import io
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from finanzas.connectors.base import RawTransaction, SourceType
from finanzas.connectors.statements.base import (
    DetectionResult,
    ImportResult,
    ParserCapabilities,
    ValidationCheck,
    ValidationReport,
)
from finanzas.shared.errors import ParserError

_EXPECTED_HEADER = {"fecha", "descripcion", "monto"}
_OPTIONAL_HEADER = {"moneda"}
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _normalize_header(cell: str) -> str:
    return _strip_accents(cell.strip().lower())


def parse_amount(raw: str) -> Decimal:
    """Montos con separadores chilenos. Reglas deterministas y testeadas:

    - Con '.' y ',': el separador MÁS A LA DERECHA es el decimal.
    - Solo ',': decimal si deja 1-2 dígitos al final; si no, miles.
    - Solo '.': decimal si deja 1-2 dígitos al final; si no, miles ("1.234.567").
    """
    s = raw.strip().replace(" ", "").replace("$", "")
    if not s:
        raise ParserError("Monto vacío")
    negative = s.startswith("-")
    s = s.lstrip("+-")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = f"{head.replace(',', '')}.{tail}" if len(tail) in (1, 2) else s.replace(",", "")
    elif "." in s:
        head, _, tail = s.rpartition(".")
        if len(tail) not in (1, 2):
            s = s.replace(".", "")
    try:
        value = Decimal(s)
    except InvalidOperation as exc:
        raise ParserError(f"Monto ilegible: {raw!r}") from exc
    return -value if negative else value


def _parse_date(raw: str) -> date:
    cleaned = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ParserError(f"Fecha ilegible: {raw!r} (formatos: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY)")


class GenericCsvParser:
    name = "generic_csv_v1"
    bank = "generic"
    version = "1.1.0"  # 1.1.0: migración a ImportResult (sesión 11)
    capabilities = ParserCapabilities(file_types=("csv",))

    def sniff(
        self, filename: str, content: bytes, password: str | None = None
    ) -> DetectionResult | None:
        if not filename.lower().endswith(".csv"):
            return None
        try:
            first_line = _decode(content).splitlines()[0]
        except (IndexError, UnicodeDecodeError):
            return None
        delimiter = ";" if ";" in first_line else ","
        header = {_normalize_header(c) for c in first_line.split(delimiter)}
        if _EXPECTED_HEADER.issubset(header) and header <= _EXPECTED_HEADER | _OPTIONAL_HEADER:
            return DetectionResult(
                parser_name=self.name,
                bank=self.bank,
                confidence=0.9,
                reason="Encabezado coincide con el formato CSV de referencia",
            )
        return None

    def parse(self, filename: str, content: bytes, password: str | None = None) -> ImportResult:
        text = _decode(content)
        lines = text.splitlines()
        if not lines:
            raise ParserError("Archivo vacío")

        delimiter = ";" if ";" in lines[0] else ","
        header = [_normalize_header(c) for c in lines[0].split(delimiter)]
        missing = _EXPECTED_HEADER - set(header)
        if missing:
            raise ParserError(
                f"Encabezado inválido: faltan columnas {sorted(missing)}. "
                "Se espera: fecha;descripcion;monto[;moneda]"
            )

        reader = csv.DictReader(io.StringIO(text), fieldnames=header, delimiter=delimiter)
        next(reader)  # descartar encabezado
        transactions: list[RawTransaction] = []
        for line_number, row in enumerate(reader, start=2):
            values = {k: (v or "").strip() for k, v in row.items() if k is not None}
            if not any(values.values()):
                continue  # línea vacía tolerada
            description = values.get("descripcion", "")
            if not description:
                raise ParserError(f"Fila {line_number}: descripción vacía")
            try:
                posted_at = _parse_date(values.get("fecha", ""))
                amount = parse_amount(values.get("monto", ""))
            except ParserError as exc:
                raise ParserError(f"Fila {line_number}: {exc.message}") from exc
            transactions.append(
                RawTransaction(
                    account_hint="",  # este formato no identifica cuenta: la elige el usuario
                    posted_at=posted_at,
                    amount=amount,
                    currency=values.get("moneda", "").upper(),
                    description_raw=description,
                    source=SourceType.STATEMENT,
                    source_ref=str(line_number),
                )
            )
        if not transactions:
            raise ParserError("El archivo no contiene movimientos")

        dates = [t.posted_at for t in transactions]
        # Este formato no trae saldos: la única validación dura posible es la de
        # contenido (ya aplicada fila a fila). Se declara explícitamente.
        validation = ValidationReport(
            checks=(
                ValidationCheck(
                    name="todas_las_filas_parseadas",
                    passed=True,
                    expected=str(len(transactions)),
                    actual=str(len(transactions)),
                ),
            )
        )
        return ImportResult(
            transactions=transactions,
            parser_version=self.version,
            detected_format=self.name,
            period_start=min(dates),
            period_end=max(dates),
            validation=validation,
            quality_signals={"filas_completas": True},
        )
