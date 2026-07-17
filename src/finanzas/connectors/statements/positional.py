"""Motor posicional REUTILIZABLE para tablas de cartolas PDF (bloque 2, P1).

Patrón general de cartolas chilenas: columnas sin líneas guía, montos
alineados a la derecha que desbordan el ancho del encabezado (docs/18 §9.5).
extract_table de pdfplumber es inservible aquí; la unidad es la palabra con
coordenadas. Nada de este módulo conoce bancos específicos.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    x1: float
    top: float

    @property
    def center(self) -> float:
        return (self.x0 + self.x1) / 2


def group_rows(words: list[Word], tolerance: float = 2.5) -> list[list[Word]]:
    """Agrupa palabras en filas por su coordenada vertical (top), ordenadas
    de arriba hacia abajo y de izquierda a derecha dentro de cada fila."""
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if rows and abs(rows[-1][0].top - word.top) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: w.x0)
    return rows


def column_for(center: float, anchors: dict[str, float]) -> str | None:
    """Columna de un valor numérico right-aligned: el ancla (x0 del encabezado)
    más a la DERECHA que quede a la izquierda del centro del valor.

    Regla validada contra cartola real Edwards (docs/18): los valores
    desbordan a la derecha de su encabezado pero su centro nunca alcanza el
    inicio del encabezado siguiente.
    """
    best_name: str | None = None
    best_x = float("-inf")
    for name, x0 in anchors.items():
        if x0 <= center and x0 > best_x:
            best_name, best_x = name, x0
    return best_name
