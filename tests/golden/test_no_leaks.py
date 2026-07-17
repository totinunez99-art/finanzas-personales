"""La CI rechaza cualquier fuga de datos personales en golden/cases (docs/13 §3)."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "golden" / "tools" / "verify_no_leaks.py"


def _load_tool():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("verify_no_leaks", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sin_fugas_en_golden_cases() -> None:
    tool = _load_tool()
    findings = tool.scan_cases(REPO_ROOT)
    assert findings == [], "Fugas detectadas en golden/cases:\n" + "\n".join(findings)


def test_el_escaner_detecta_fugas_conocidas() -> None:
    """Un escáner que no detecta nada podría estar roto: se prueba con fugas sintéticas."""
    tool = _load_tool()
    assert tool.scan_text("RUT 12.345.678-5 contacto", [])
    assert tool.scan_text("correo persona@dominioprivado.cl", [])
    assert tool.scan_text("ficticio demo@example.com", []) == []  # RFC 2606: no es fuga
    assert tool.scan_text("tarjeta 4111 1111 1111 1111", [])  # Visa de prueba, Luhn válido
    assert tool.scan_text("hola NOMBRE-REAL", ["nombre-real"])
    assert tool.scan_text("texto inocuo 1.234.567", []) == []  # monto chileno NO es fuga
