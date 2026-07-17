"""Conector Banco de Chile / Edwards — Cartola Cuenta Corriente (PDF).

Diseño completo en docs/18. Todo lo específico de Edwards vive AQUÍ; las
utilidades (posicional, montos, PDF, metadata) son compartidas entre bancos.

Estrategia: metadata estructurada CVQT_* del generador COLDview como segunda
fuente de verdad + extracción posicional de palabras (las columnas cargo/abono/
saldo solo se distinguen por coordenadas). Tolerancia cero: ante ambigüedad se
lanza ParserError con página y fila; jamás se insertan datos dudosos.
"""

import re
from datetime import date, datetime
from decimal import Decimal

from finanzas.connectors.base import RawTransaction, SourceType
from finanzas.connectors.statements.base import (
    DetectionResult,
    ImportResult,
    ParserCapabilities,
    ValidationCheck,
    ValidationReport,
    confidence_from_signals,
)
from finanzas.connectors.statements.pdf_utils import (
    extract_pages_words,
    looks_like_pdf,
    read_pdf_metadata,
)
from finanzas.connectors.statements.positional import Word, column_for, group_rows
from finanzas.connectors.statements.text_utils import parse_amount, resolve_year
from finanzas.shared.errors import ParserError

_DATE_RE = re.compile(r"^\d{2}/\d{2}$")
_NUMERIC_RE = re.compile(r"^[\d.]+$")
_PAGE_RE = re.compile(r"PAGINA\s*:?\s*(\d+)\s+DE\s+(\d+)")
_CURRENCY_RE = re.compile(r"MONEDA\s*:?\s*([A-ZÁÉÍÓÚ]+)")
_MERCHANT_PREFIXES = ("PAGO:", "TRASPASO A:", "TRASPASO DE:", "APP-TRASPASO A:", "APP-TRASPASO DE:")

# Desplazamientos de banda medidos sobre cartola real (docs/18 §5):
_DETALLE_MIN_X = 55.0  # a la izquierda solo vive la fecha DIA/MES
_SUCURSAL_MARGIN = 15.0  # los valores de sucursal parten ~10pt antes del encabezado


def _cvqt_amount(raw: str) -> Decimal:
    """Totales CVQT: enteros de 12 dígitos en pesos ('000000150000' → 150000)."""
    return Decimal(int(raw))


def _cvqt_date(raw: str) -> date:
    return datetime.strptime(raw.strip(), "%Y%m%d").date()


class _Row:
    """Fila de la tabla ya clasificada por bandas."""

    def __init__(self) -> None:
        self.date_token: str | None = None
        self.detalle: list[str] = []
        self.sucursal: list[str] = []
        self.docto: str | None = None
        self.cargo: Decimal | None = None
        self.abono: Decimal | None = None
        self.saldo: Decimal | None = None

    @property
    def detalle_text(self) -> str:
        return " ".join(self.detalle)


class EdwardsCcPdfParser:
    name = "edwards_cc_pdf"
    bank = "edwards"
    version = "1.0.0"
    capabilities = ParserCapabilities(
        file_types=("pdf",),
        supports_password=True,
        provides_metadata=True,
        provides_balances=True,
        provides_account_hint=True,
    )

    # ---------------------------------------------------------------- sniff
    def sniff(
        self, filename: str, content: bytes, password: str | None = None
    ) -> DetectionResult | None:
        if not looks_like_pdf(content):
            return None
        meta = read_pdf_metadata(content, password)
        if meta is None:
            return None  # cifrado sin clave válida: el wizard ya pidió la clave antes
        cvqt_keys = sum(1 for k in meta if k.startswith("CVQT_"))
        if meta.get("Author") == "COLDview" and cvqt_keys >= 5:
            return DetectionResult(
                parser_name=self.name,
                bank=self.bank,
                confidence=0.98,
                reason=f"Generador COLDview con {cvqt_keys} campos CVQT (Banco de Chile/Edwards)",
            )
        return None

    # ---------------------------------------------------------------- parse
    def parse(self, filename: str, content: bytes, password: str | None = None) -> ImportResult:
        meta = read_pdf_metadata(content, password)
        if meta is None:
            raise ParserError("No se pudo abrir el PDF (¿contraseña?)")
        cvqt = {k[5:]: v for k, v in meta.items() if k.startswith("CVQT_")}
        if "FECHADESDE" not in cvqt or "FECHAHASTA" not in cvqt:
            raise ParserError("Metadata COLDview incompleta: falta el período de la cartola")
        period_start = _cvqt_date(cvqt["FECHADESDE"])
        period_end = _cvqt_date(cvqt["FECHAHASTA"])

        pages = extract_pages_words(content, password)
        warnings: list[str] = []
        signals: dict[str, bool] = {"metadata_cvqt_presente": True}

        transactions: list[RawTransaction] = []
        opening: Decimal | None = None
        closing: Decimal | None = None
        printed_saldos: list[tuple[int, Decimal]] = []  # (indice_tx_acumulado, saldo impreso)
        pages_declared: int | None = None
        pages_seen: list[int] = []
        continuations = 0

        for page_index, (page_width, _height, words) in enumerate(pages, start=1):
            full_text = " ".join(w.text for w in words)
            page_match = _PAGE_RE.search(full_text)
            if page_match:
                pages_seen.append(int(page_match.group(1)))
                declared = int(page_match.group(2))
                if pages_declared is not None and declared != pages_declared:
                    raise ParserError(
                        f"Página {page_index}: total de páginas inconsistente "
                        f"({declared} vs {pages_declared})"
                    )
                pages_declared = declared
            currency_match = _CURRENCY_RE.search(full_text)
            if currency_match and currency_match.group(1) != "PESOS":
                raise ParserError(
                    f"Moneda {currency_match.group(1)!r} aún no soportada (solo PESOS/CLP). "
                    "Guarda esta cartola para crear el caso golden correspondiente."
                )

            # Flags D/A con coordenadas corruptas del generador real (docs/18 §9.6)
            rows = group_rows([w for w in words if w.x0 < page_width * 1.5])

            header_anchors = self._find_header(rows)
            if header_anchors is None:
                raise ParserError(f"Página {page_index}: no se encontró el encabezado de la tabla")
            header_top, anchors = header_anchors

            in_table = True
            for row_words in rows:
                if row_words[0].top <= header_top or not in_table:
                    continue
                joined = " ".join(w.text for w in row_words)
                if row_words[0].top - header_top < 14 and not any(
                    _NUMERIC_RE.match(w.text) for w in row_words
                ):
                    continue  # segunda línea del encabezado ("DIA/MES O CARGOS O ABONOS")
                if joined.startswith("RETENCION"):
                    in_table = False  # fin de la tabla: resúmenes y mensajes del pie
                    continue
                row = self._classify_row(row_words, anchors, page_index)
                if row.detalle_text == "SALDO INICIAL":
                    opening = self._require(row.saldo, "SALDO INICIAL sin monto", page_index)
                elif row.detalle_text == "SALDO FINAL":
                    closing = self._require(row.saldo, "SALDO FINAL sin monto", page_index)
                    in_table = False
                elif row.date_token is not None:
                    transactions.append(
                        self._to_transaction(
                            row, period_start, period_end, cvqt, page_index, len(transactions)
                        )
                    )
                    if row.saldo is not None:
                        printed_saldos.append((len(transactions), row.saldo))
                elif row.detalle and row.cargo is None and row.abono is None:
                    # Continuación de descripción (no observado en muestras: docs/18 §9.4)
                    if not transactions:
                        raise ParserError(f"Página {page_index}: fila huérfana: {joined!r}")
                    prev = transactions[-1]
                    transactions[-1] = RawTransaction(
                        **{**prev.__dict__, "description_raw": f"{prev.description_raw} {joined}"}
                    )
                    continuations += 1
                else:
                    raise ParserError(f"Página {page_index}: fila no reconocida: {joined!r}")

        return self._build_result(
            cvqt,
            period_start,
            period_end,
            transactions,
            opening,
            closing,
            printed_saldos,
            pages_declared,
            pages_seen,
            continuations,
            warnings,
            signals,
        )

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _require(value: Decimal | None, message: str, page: int) -> Decimal:
        if value is None:
            raise ParserError(f"Página {page}: {message}")
        return value

    @staticmethod
    def _find_header(rows: list[list[Word]]) -> tuple[float, dict[str, float]] | None:
        for row in rows:
            texts = [w.text for w in row]
            if "FECHA" in texts and "SALDO" in texts and texts.count("MONTO") >= 2:
                montos = [w for w in row if w.text == "MONTO"]
                anchors = {
                    "sucursal": next(w.x0 for w in row if w.text == "SUCURSAL"),
                    "docto": next((w.x0 for w in row if w.text.startswith("DOCTO")), 300.0),
                    "cargo": montos[0].x0,
                    "abono": montos[1].x0,
                    "saldo": next(w.x0 for w in row if w.text == "SALDO"),
                }
                return row[0].top, anchors
        return None

    def _classify_row(self, row_words: list[Word], anchors: dict[str, float], page: int) -> _Row:
        numeric_anchors = {k: anchors[k] for k in ("docto", "cargo", "abono", "saldo")}
        row = _Row()
        for w in row_words:
            if _DATE_RE.match(w.text) and w.x0 < _DETALLE_MIN_X:
                row.date_token = w.text
            elif _NUMERIC_RE.match(w.text) and w.center >= anchors["docto"] - 20:
                column = column_for(w.center, numeric_anchors)
                if column == "docto":
                    row.docto = w.text
                elif column in ("cargo", "abono", "saldo"):
                    value = parse_amount(w.text)
                    if getattr(row, column) is not None:
                        raise ParserError(
                            f"Página {page}: dos valores en la columna {column}: {w.text!r}"
                        )
                    setattr(row, column, value)
            elif w.text in ("D", "A") and w.x0 > anchors["saldo"]:
                continue  # flag de saldo (coordenadas corruptas del generador, docs/18 §9.6)
            elif w.x0 >= anchors["sucursal"] - _SUCURSAL_MARGIN:
                row.sucursal.append(w.text)
            else:
                row.detalle.append(w.text)
        return row

    def _to_transaction(
        self,
        row: _Row,
        period_start: date,
        period_end: date,
        cvqt: dict[str, str],
        page: int,
        index: int,
    ) -> RawTransaction:
        assert row.date_token is not None
        day, month = int(row.date_token[:2]), int(row.date_token[3:5])
        posted_at = resolve_year(day, month, period_start, period_end)
        if row.cargo is not None and row.abono is not None:
            raise ParserError(
                f"Página {page}: fila con cargo Y abono simultáneos: {row.detalle_text!r}"
            )
        if row.cargo is None and row.abono is None:
            raise ParserError(f"Página {page}: fila sin monto: {row.detalle_text!r}")
        amount = -row.cargo if row.cargo is not None else row.abono
        assert amount is not None
        detalle = row.detalle_text
        return RawTransaction(
            account_hint=cvqt.get("NROCTACTE", "").lstrip("0"),
            posted_at=posted_at,
            amount=amount,
            currency="CLP",
            description_raw=detalle,
            source=SourceType.STATEMENT,
            source_ref=f"p{page}:t{index}",
            merchant_hint=self._merchant_hint(detalle),
        )

    @staticmethod
    def _merchant_hint(detalle: str) -> str | None:
        for prefix in _MERCHANT_PREFIXES:
            if detalle.startswith(prefix):
                candidate = detalle[len(prefix) :].strip()
                return candidate[:120] or None
        return None

    def _build_result(
        self,
        cvqt: dict[str, str],
        period_start: date,
        period_end: date,
        transactions: list[RawTransaction],
        opening: Decimal | None,
        closing: Decimal | None,
        printed_saldos: list[tuple[int, Decimal]],
        pages_declared: int | None,
        pages_seen: list[int],
        continuations: int,
        warnings: list[str],
        signals: dict[str, bool],
    ) -> ImportResult:
        if opening is None or closing is None:
            raise ParserError("La cartola no contiene SALDO INICIAL y/o SALDO FINAL")

        checks: list[ValidationCheck] = []
        total_abonos = sum((t.amount for t in transactions if t.amount > 0), Decimal(0))
        total_cargos = sum((-t.amount for t in transactions if t.amount < 0), Decimal(0))

        computed_closing = opening + total_abonos - total_cargos
        checks.append(
            ValidationCheck(
                "cuadratura_global",
                computed_closing == closing,
                expected=str(closing),
                actual=str(computed_closing),
            )
        )

        meta_abonos = _cvqt_amount(cvqt.get("DEPOSITOS", "0")) + _cvqt_amount(
            cvqt.get("OTROSABONOS", "0")
        )
        meta_cargos = (
            _cvqt_amount(cvqt.get("OTROSCARGOS", "0"))
            + _cvqt_amount(cvqt.get("CHEQUES", "0"))
            + _cvqt_amount(cvqt.get("GIROS", "0"))
            + _cvqt_amount(cvqt.get("IMPUESTOS", "0"))
        )
        checks.append(
            ValidationCheck(
                "abonos_vs_metadata",
                total_abonos == meta_abonos,
                expected=str(meta_abonos),
                actual=str(total_abonos),
            )
        )
        checks.append(
            ValidationCheck(
                "cargos_vs_metadata",
                total_cargos == meta_cargos,
                expected=str(meta_cargos),
                actual=str(total_cargos),
            )
        )

        retenciones = _cvqt_amount(cvqt.get("RETENCION1DIA", "0")) + _cvqt_amount(
            cvqt.get("RETENCIONMAS1DIA", "0")
        )
        saldo_meta = _cvqt_amount(cvqt.get("SALDODISPONIBLE", "0"))
        if retenciones == 0:
            checks.append(
                ValidationCheck(
                    "saldo_final_vs_metadata",
                    closing == saldo_meta,
                    expected=str(saldo_meta),
                    actual=str(closing),
                )
            )
        else:
            warnings.append(
                f"Retenciones por {retenciones}: saldo disponible ({saldo_meta}) no comparable "
                "con saldo final; verificación omitida (caso aún sin muestra real)"
            )

        # Encadenado diario: el saldo impreso al final de cada día debe coincidir.
        chain_ok = True
        for tx_count, printed in printed_saldos:
            partial = opening + sum((t.amount for t in transactions[:tx_count]), Decimal(0))
            if partial != printed:
                chain_ok = False
                break
        checks.append(
            ValidationCheck(
                "encadenado_diario",
                chain_ok,
                expected="saldos impresos por día",
                actual="OK" if chain_ok else "desviación detectada",
            )
        )

        pages_ok = pages_declared is not None and sorted(pages_seen) == list(
            range(1, pages_declared + 1)
        )
        checks.append(
            ValidationCheck(
                "paginas_completas",
                pages_ok,
                expected=str(pages_declared),
                actual=str(len(pages_seen)),
            )
        )

        signals["sin_continuaciones_inferidas"] = continuations == 0
        signals["encadenado_diario"] = chain_ok
        if continuations:
            warnings.append(
                f"{continuations} línea(s) de continuación inferida(s): layout no observado "
                "en muestras; revisar descripciones largas"
            )

        report = ValidationReport(checks=tuple(checks))
        if not report.passed:
            failed = "; ".join(
                f"{c.name} (esperado {c.expected}, observado {c.actual})"
                for c in report.checks
                if not c.passed
            )
            raise ParserError(
                f"Validación de integridad fallida: {failed}. "
                "La importación se cancela: ningún movimiento fue insertado."
            )
        return ImportResult(
            transactions=transactions,
            parser_version=self.version,
            detected_format=self.name,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening,
            closing_balance=closing,
            metadata={
                "account": cvqt.get("NROCTACTE", "").lstrip("0"),
                "cartola_nro": cvqt.get("CARTOLANRO", "").lstrip("0"),
                "retenciones": str(retenciones),
                "brand": "Banco de Chile / Edwards (COLDview)",
            },
            validation=report,
            warnings=warnings,
            extraction_confidence=confidence_from_signals(signals),
            quality_signals=signals,
        )
