"""Detección de PDFs cifrados (fase A del wizard, docs/18 §8)."""

from io import BytesIO

from pypdf import PdfWriter

from finanzas.connectors.statements.pdf_utils import (
    is_encrypted_pdf,
    looks_like_pdf,
    password_opens,
)


def _pdf_bytes(password: str | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if password:
        writer.encrypt(password)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_no_pdf_no_es_cifrado() -> None:
    assert not looks_like_pdf(b"fecha;descripcion;monto\n")
    assert not is_encrypted_pdf(b"fecha;descripcion;monto\n")


def test_pdf_sin_clave() -> None:
    content = _pdf_bytes()
    assert looks_like_pdf(content)
    assert not is_encrypted_pdf(content)
    assert password_opens(content, "cualquiera")  # sin cifrado, cualquier clave "abre"


def test_pdf_cifrado_y_verificacion_de_clave() -> None:
    content = _pdf_bytes(password="s3creta")
    assert is_encrypted_pdf(content)
    assert password_opens(content, "s3creta")
    assert not password_opens(content, "incorrecta")


def test_pdf_corrupto_no_explota() -> None:
    assert not is_encrypted_pdf(b"%PDF-1.4 basura truncada")
