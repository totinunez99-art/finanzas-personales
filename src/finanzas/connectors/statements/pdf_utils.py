"""Utilidades de PDF a nivel de conectores (conocimiento de formato, NO de banco).

El núcleo las usa vía la dependencia permitida core→connectors para el flujo de
contraseña del wizard (docs/18 §8, fase A). La contraseña jamás se loguea ni persiste.
"""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def looks_like_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


def is_encrypted_pdf(content: bytes) -> bool:
    if not looks_like_pdf(content):
        return False
    try:
        return PdfReader(BytesIO(content)).is_encrypted
    except PdfReadError:
        return False


def password_opens(content: bytes, password: str) -> bool:
    """True si la contraseña abre el documento. No conserva nada."""
    try:
        reader = PdfReader(BytesIO(content))
        if not reader.is_encrypted:
            return True
        return bool(reader.decrypt(password))
    except PdfReadError:
        return False
