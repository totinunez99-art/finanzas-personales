"""Regresión LOCAL contra la cartola REAL de Edwards (docs/13: la CI nunca la ve).

Requiere variables de entorno:
  EDWARDS_REAL_PDF      ruta al PDF original (golden/originals/...)
  EDWARDS_PDF_PASSWORD  su contraseña (jamás se persiste en código ni docs)
Se salta silenciosamente si faltan — en CI siempre se salta.
"""

import os

import pytest

PDF = os.environ.get("EDWARDS_REAL_PDF", "")
PASSWORD = os.environ.get("EDWARDS_PDF_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    not PDF or not PASSWORD, reason="sin cartola real local (EDWARDS_REAL_PDF/_PASSWORD)"
)


def test_cartola_real_parsea_y_cuadra() -> None:
    from finanzas.connectors.statements.registry import detect

    with open(PDF, "rb") as f:
        content = f.read()
    detection = detect(os.path.basename(PDF), content, PASSWORD)
    assert detection is not None and detection[0].name == "edwards_cc_pdf"

    result = detection[0].parse(os.path.basename(PDF), content, PASSWORD)
    assert result.validation.passed, [c for c in result.validation.checks if not c.passed]
    assert len(result.transactions) > 0
    assert result.opening_balance is not None and result.closing_balance is not None
    assert result.extraction_confidence == 1.0
