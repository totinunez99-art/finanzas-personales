"""Genera PDFs Edwards-like para el Golden Dataset (docs/13, docs/18).

Renderiza el layout medido sobre la cartola real (bandas X, encabezado doble,
flags de saldo, bloque CVQT) desde un spec YAML con datos anonimizados o
sintéticos. También emite el expected.json correspondiente (la verdad viene
del spec escrito a mano, no del parser: docs/13 §5.1).

Uso: python golden/tools/build_edwards_pdf.py <spec.yaml> <output_dir>
"""

import json
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import yaml
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

W, H = A4  # 595 x 842 pt, igual que la cartola real
ROW_STEP = 9.4
# Anclas X medidas en la cartola real (docs/18 §5):
X_FECHA, X_DETALLE, X_SUCURSAL, X_DOCTO = 23, 60, 227, 309
XR_CARGO, XR_ABONO, XR_SALDO, X_FLAG = 414, 490, 575, 584
HEADER_TOP, TABLE_TOP = 255, 279


def _fmt(n: int) -> str:
    """Formato chileno de miles con punto: 2213759 -> '2.213.759'."""
    return f"{n:,}".replace(",", ".")


def _cvqt_int(n: int) -> str:
    return f"{n:012d}"


def _y(top: float) -> float:
    return H - top


def _draw_page(
    c: canvas.Canvas,
    spec: dict,
    rows: list[dict],
    page_no: int,
    total_pages: int,
    first: bool,
    last: bool,
) -> None:
    c.setFont("Helvetica", 7)
    d = spec["period"]["desde"]
    h = spec["period"]["hasta"]
    desde = datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
    hasta = datetime.strptime(h, "%Y-%m-%d").strftime("%d/%m/%Y")
    c.drawString(150, _y(60), "Estado de Cuenta")
    c.drawString(23, _y(100), f"SR(A)(ES) {spec['holder']}")
    c.drawString(23, _y(110), spec["email"])
    c.drawString(
        23,
        _y(215),
        f"EJECUTIVO DE CUENTA : {spec['executive']} N° DE CUENTA : "
        f"XXXXXXXX{spec['account'][-4:]} MONEDA : PESOS",
    )
    c.drawString(
        23,
        _y(228),
        f"SUCURSAL : {spec['branch']} CARTOLA N° : {spec['cartola_nro']} "
        f"N° DE PAGINA : {page_no} DE {total_pages}",
    )
    c.drawString(23, _y(241), f"TELEFONO : 562000000 DESDE : {desde} HASTA : {hasta}")

    # Encabezado de tabla (doble línea, como el real)
    c.drawString(X_FECHA, _y(HEADER_TOP), "FECHA")
    c.drawString(80, _y(HEADER_TOP), "DETALLE DE TRANSACCION")
    c.drawString(237, _y(HEADER_TOP), "SUCURSAL")
    c.drawString(298, _y(HEADER_TOP), "N°")
    c.drawString(X_DOCTO, _y(HEADER_TOP), "DOCTO")
    c.drawString(344, _y(HEADER_TOP), "MONTO CHEQUES")
    c.drawString(419, _y(HEADER_TOP), "MONTO DEPOSITOS")
    c.drawString(534, _y(HEADER_TOP), "SALDO")
    c.drawString(X_FECHA, _y(HEADER_TOP + 9), "DIA/MES")
    c.drawString(344, _y(HEADER_TOP + 9), "O CARGOS")
    c.drawString(419, _y(HEADER_TOP + 9), "O ABONOS")

    top = TABLE_TOP
    if first:
        c.drawString(X_FECHA, _y(top), spec["opening_date"])
        c.drawString(X_DETALLE, _y(top), "SALDO INICIAL")
        c.drawRightString(XR_SALDO, _y(top), _fmt(spec["opening"]))
        c.drawString(X_FLAG, _y(top), "D")
        top += ROW_STEP
    for row in rows:
        c.drawString(X_FECHA, _y(top), row["date"])
        c.drawString(X_DETALLE, _y(top), row["detalle"])
        if row.get("sucursal"):
            c.drawString(X_SUCURSAL, _y(top), row["sucursal"])
        if row.get("docto"):
            c.drawString(X_DOCTO, _y(top), row["docto"])
        if "cargo" in row:
            c.drawRightString(XR_CARGO, _y(top), _fmt(row["cargo"]))
        if "abono" in row:
            c.drawRightString(XR_ABONO, _y(top), _fmt(row["abono"]))
        if "saldo" in row:
            c.drawRightString(XR_SALDO, _y(top), _fmt(row["saldo"]))
            c.drawString(X_FLAG, _y(top), "D")
        top += ROW_STEP
    if last:
        c.drawString(X_FECHA, _y(top), spec["closing_date"])
        c.drawString(X_DETALLE, _y(top), "SALDO FINAL")
        c.drawRightString(XR_SALDO, _y(top), _fmt(spec["closing"]))
        c.drawString(X_FLAG, _y(top), "D")
        top += ROW_STEP * 2
        t = spec["totals"]
        c.drawString(
            X_FECHA,
            _y(top),
            "RETENCION A 1 DIA RETENCION A MAS DE 1 DIA SALDO DISPONIBLE A LA FECHA",
        )
        top += ROW_STEP
        c.drawString(
            X_FECHA,
            _y(top),
            f"{_fmt(t.get('retencion1', 0))} {_fmt(t.get('retencionmas', 0))} "
            f"{_fmt(t['saldodisponible'])}",
        )
        top += ROW_STEP
        c.drawString(
            23,
            _y(top + 20),
            "Infórmese sobre la garantía estatal de los depósitos en www.cmfchile.cl",
        )
    c.showPage()


def build(spec_path: str, out_dir: str) -> None:
    spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    rows = spec.get("rows", [])
    per_page = spec.get("rows_per_page", 60)
    chunks = [rows[i : i + per_page] for i in range(0, len(rows), per_page)] or [[]]
    total_pages = len(chunks)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    for i, chunk in enumerate(chunks, start=1):
        _draw_page(c, spec, chunk, i, total_pages, first=(i == 1), last=(i == total_pages))
    c.save()

    reader = PdfReader(BytesIO(buffer.getvalue()))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    t = spec["totals"]
    d = spec["period"]["desde"].replace("-", "")
    h = spec["period"]["hasta"].replace("-", "")
    writer.add_metadata(
        {
            "/Author": "COLDview",
            "/Title": "COLDview Document",
            "/CVQT_NROCTACTE": spec["account"].zfill(12),
            "/CVQT_FECHADESDE": d,
            "/CVQT_FECHAHASTA": h,
            "/CVQT_CARTOLANRO": f"{int(spec['cartola_nro']):03d}",
            "/CVQT_SALDODISPONIBLE": _cvqt_int(t["saldodisponible"]),
            "/CVQT_DEPOSITOS": _cvqt_int(t.get("depositos", 0)),
            "/CVQT_CHEQUES": _cvqt_int(t.get("cheques", 0)),
            "/CVQT_OTROSABONOS": _cvqt_int(t.get("otrosabonos", 0)),
            "/CVQT_OTROSCARGOS": _cvqt_int(t.get("otroscargos", 0)),
            "/CVQT_GIROS": _cvqt_int(t.get("giros", 0)),
            "/CVQT_IMPUESTOS": _cvqt_int(t.get("impuestos", 0)),
            "/CVQT_RETENCION1DIA": _cvqt_int(t.get("retencion1", 0)),
            "/CVQT_RETENCIONMAS1DIA": _cvqt_int(t.get("retencionmas", 0)),
            "/CVQT_NOMBRE": spec["holder"],
            "/CVQT_DIRECCION": spec["email"],
        }
    )
    if spec.get("password"):
        writer.encrypt(spec["password"])

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "input.pdf", "wb") as f:
        writer.write(f)

    # expected.json desde el SPEC (verdad escrita a mano, no salida del parser)
    year_from = int(spec["period"]["desde"][:4])
    year_to = int(spec["period"]["hasta"][:4])
    expected = []
    if not spec.get("skip_expected"):
        from datetime import date as _date

        start = datetime.strptime(spec["period"]["desde"], "%Y-%m-%d").date()
        end = datetime.strptime(spec["period"]["hasta"], "%Y-%m-%d").date()
        for row in rows:
            dd, mm = int(row["date"][:2]), int(row["date"][3:5])
            posted = None
            for y in {year_from, year_to}:
                try:
                    cand = _date(y, mm, dd)
                except ValueError:
                    continue
                if start <= cand <= end:
                    posted = cand
            amount = -row["cargo"] if "cargo" in row else row["abono"]
            expected.append(
                {
                    "posted_at": posted.isoformat(),
                    "amount": str(amount),
                    "currency": "CLP",
                    "description_raw": row["detalle"],
                }
            )
        (out / "expected.json").write_text(
            json.dumps({"transactions": expected}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(f"OK: {out}/input.pdf ({total_pages} pagina(s), {len(rows)} filas)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
