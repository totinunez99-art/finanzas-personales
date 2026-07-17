"""Utilidades de texto REUTILIZABLES entre bancos (bloque 2, Edwards P1).

Nada aquí conoce a un banco específico. Lo específico vive en cada parser.
"""

import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from finanzas.shared.errors import ParserError


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def parse_amount(raw: str) -> Decimal:
    """Montos con separadores chilenos. Reglas deterministas y testeadas:

    - Con '.' y ',': el separador MAS A LA DERECHA es el decimal.
    - Solo ',': decimal si deja 1-2 digitos al final; si no, miles.
    - Solo '.': decimal si deja 1-2 digitos al final; si no, miles ("1.234.567").
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


def resolve_year(day: int, month: int, period_start: date, period_end: date) -> date:
    """Fecha DD/MM sin año → año que la deja dentro del período (docs/18 §9.1).

    Cubre el rollover diciembre-enero: cartola 29/12/2026→30/01/2027 asigna
    2026 a filas de diciembre y 2027 a las de enero.
    """
    for year in {period_start.year, period_end.year}:
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if period_start <= candidate <= period_end:
            return candidate
    raise ParserError(
        f"Fecha {day:02d}/{month:02d} fuera del período "
        f"{period_start.isoformat()}..{period_end.isoformat()}"
    )
