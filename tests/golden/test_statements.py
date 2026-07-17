"""Runner golden de parsers de cartola (docs/13 §4).

Cada caso activo con validates=[parser] se parsea y compara campo a campo
contra expected.json. Cada caso con validates=[error] afirma el fallo declarado.
Ningún parser se acepta sin pasar por aquí.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from finanzas.connectors.statements.registry import detect
from finanzas.shared.errors import ParserError
from tests.golden.conftest import case_input, discover_cases

PARSER_CASES = discover_cases(validates="parser")
ERROR_CASES = discover_cases(validates="error")


def _load_expected(case_dir: Path) -> dict[str, Any]:
    return json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("case_id", "case_dir", "manifest"),
    PARSER_CASES,
    ids=[c[0] for c in PARSER_CASES],
)
def test_parser_contra_expected(case_id: str, case_dir: Path, manifest: dict) -> None:
    input_path = case_input(case_dir)
    content = input_path.read_bytes()
    password = manifest.get("password")

    detection = detect(input_path.name, content, password)
    assert detection is not None, f"{case_id}: ningún parser reconoció el input"
    parser, _info = detection

    statement = parser.parse(input_path.name, content, password)
    expected = _load_expected(case_dir)["transactions"]

    actual = [
        {
            "posted_at": t.posted_at.isoformat(),
            "amount": str(t.amount),
            "currency": t.currency,
            "description_raw": t.description_raw,
        }
        for t in statement.transactions
    ]
    assert actual == expected, f"{case_id}: salida del parser difiere del expected"


@pytest.mark.parametrize(
    ("case_id", "case_dir", "manifest"),
    ERROR_CASES,
    ids=[c[0] for c in ERROR_CASES],
)
def test_errores_declarados(case_id: str, case_dir: Path, manifest: dict) -> None:
    input_path = case_input(case_dir)
    content = input_path.read_bytes()
    password = manifest.get("password")
    expected = _load_expected(case_dir)
    outcome = expected["outcome"]

    detection = detect(input_path.name, content, password)
    if outcome == "unsupported":
        assert detection is None, (
            f"{case_id}: un parser reclamó un formato que debe ser 'no compatible'"
        )
    elif outcome == "parser_error":
        assert detection is not None, f"{case_id}: el formato debía ser reconocido"
        parser, _info = detection
        with pytest.raises(ParserError) as excinfo:
            parser.parse(input_path.name, content, password)
        assert expected["error_contains"] in str(excinfo.value), (
            f"{case_id}: el error no contiene {expected['error_contains']!r}"
        )
    else:
        pytest.fail(f"{case_id}: outcome desconocido {outcome!r}")


def test_hay_casos_golden() -> None:
    """El runner sin casos es un falso verde: debe existir al menos un caso de cada tipo."""
    assert PARSER_CASES, "No hay casos golden de parser"
    assert ERROR_CASES, "No hay casos golden de error"
