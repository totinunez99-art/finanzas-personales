"""Reglas deterministas de montos chilenos (generic_csv.parse_amount)."""

from decimal import Decimal

import pytest

from finanzas.connectors.statements.generic_csv import parse_amount
from finanzas.shared.errors import ParserError


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-12345", Decimal("-12345")),
        ("-12.345", Decimal("-12345")),  # miles chileno
        ("1.234.567", Decimal("1234567")),  # miles chileno múltiple
        ("-12.345,50", Decimal("-12345.50")),  # miles punto + decimal coma
        ("-12,345.50", Decimal("-12345.50")),  # formato anglosajón
        ("-45,90", Decimal("-45.90")),  # coma decimal
        ("-45.90", Decimal("-45.90")),  # punto decimal (2 dígitos)
        ("125.000", Decimal("125000")),  # 3 dígitos tras punto = miles
        ("$ 1.250", Decimal("1250")),  # símbolo y espacios tolerados
        ("+500", Decimal("500")),
    ],
)
def test_parse_amount(raw: str, expected: Decimal) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1.2.3,4,5"])
def test_montos_ilegibles_fallan(raw: str) -> None:
    with pytest.raises(ParserError):
        parse_amount(raw)
