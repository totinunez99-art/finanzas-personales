"""Utilidades de PDF a nivel de conectores: REUTILIZABLES entre bancos.

Conocimiento de formato, NO de banco.

El núcleo las usa vía la dependencia permitida core→connectors para el flujo de
contraseña del wizard (docs/18 §8, fase A). La contraseña jamás se loguea ni persiste.
"""

from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finanzas.connectors.statements.positional import Word

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


def read_pdf_metadata(content: bytes, password: str | None = None) -> dict[str, str] | None:
    """Metadata del documento (pypdf). None si el PDF no abre con esa clave.
    Reutilizable: los COLDview de Banco de Chile/Edwards traen claves CVQT_*."""
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and (not password or not reader.decrypt(password)):
            return None
        raw: dict[str, object] = dict(reader.metadata or {})
        return {str(k).lstrip("/"): str(v).strip() for k, v in raw.items()}
    except Exception:
        return None


def extract_pages_words(
    content: bytes, password: str | None = None
) -> "list[tuple[float, float, list[Word]]]":
    """Palabras con coordenadas por página: [(ancho, alto, [Word,...]), ...].
    Requiere pdfplumber (import tardío: solo los parsers PDF lo pagan)."""
    import pdfplumber

    from finanzas.connectors.statements.positional import Word

    pages: list[tuple[float, float, list[Word]]] = []
    with pdfplumber.open(BytesIO(content), password=password or "") as pdf:
        for page in pdf.pages:
            words = [
                Word(text=w["text"], x0=float(w["x0"]), x1=float(w["x1"]), top=float(w["top"]))
                for w in page.extract_words()
            ]
            pages.append((float(page.width), float(page.height), words))
    return pages
