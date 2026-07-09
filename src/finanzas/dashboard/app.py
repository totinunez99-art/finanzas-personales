"""Dashboard financiero — pantalla principal (Sprint 2).

La salud del sistema vive en la página Administración.
"""

from datetime import date

import streamlit as st

from finanzas.dashboard.api_client import get_json
from finanzas.dashboard.components import (
    format_amount,
    render_transactions_table,
    transaction_filters_ui,
)

st.set_page_config(page_title="Finanzas Personales", page_icon="💰", layout="wide")
st.title("💰 Finanzas Personales")

# ---------------------------------------------------------------- período
today = date.today()
months = [f"{y}-{m:02d}" for y in range(today.year, today.year - 2, -1) for m in range(12, 0, -1)]
months = [m for m in months if m <= f"{today.year}-{today.month:02d}"]
period = st.selectbox(
    "Período",
    months,
    index=0,
    format_func=lambda p: f"{p} (este mes)" if p == months[0] else p,
)

stats, error = get_json("/stats/summary", params={"period": period})
if error:
    st.error(f"Sin conexión con la API: {error}")
    st.page_link("pages/9_Administracion.py", label="Revisar salud del sistema →", icon="🔧")
    st.stop()

# ---------------------------------------------------------------- métricas
clp = next((c for c in stats["by_currency"] if c["currency"] == "CLP"), None)
col1, col2, col3, col4 = st.columns(4)
if clp:
    col1.metric("Ingresos", format_amount(clp["income"], "CLP"))
    col2.metric("Gastos", format_amount(clp["expense"], "CLP"))
    col3.metric("Saldo neto", format_amount(clp["net"], "CLP"))
else:
    col1.metric("Ingresos", "$0")
    col2.metric("Gastos", "$0")
    col3.metric("Saldo neto", "$0")
col4.metric("Movimientos", stats["total_count"])

others = [c for c in stats["by_currency"] if c["currency"] != "CLP"]
if others:
    with st.expander("Otras monedas del período"):
        for c in others:
            st.write(
                f"**{c['currency']}** — ingresos {c['income']}, gastos {c['expense']}, "
                f"neto {c['net']} ({c['count']} movs.)"
            )

# ---------------------------------------------------------------- última importación
last = stats.get("last_import")
col_info, col_btn = st.columns([3, 1])
if last:
    col_info.caption(
        f"Última importación: {last['filename']} · {last['connector']} · "
        f"{last['created_at'][:10]} · estado {last['status']}"
    )
else:
    col_info.caption("Aún no hay importaciones.")
with col_btn:
    st.page_link("pages/1_Importar.py", label="Importar nueva cartola", icon="📥")

st.divider()

# ---------------------------------------------------------------- movimientos
st.subheader("Movimientos")
params = transaction_filters_ui("home")
total = render_transactions_table(params, limit=200, compact=True)
if total > 200:
    st.caption(f"Mostrando 200 de {total}.")
    st.page_link("pages/2_Movimientos.py", label="Ver todos con más espacio →", icon="📄")
