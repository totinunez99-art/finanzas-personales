"""Movimientos — vista completa con filtros e historial de importaciones."""

import streamlit as st

from finanzas.dashboard.api_client import get_json
from finanzas.dashboard.components import render_transactions_table, transaction_filters_ui

st.set_page_config(page_title="Movimientos", page_icon="📄", layout="wide")
st.title("📄 Movimientos")

accounts, error = get_json("/accounts")
if error:
    st.error(f"Sin conexión con la API: {error}")
    st.stop()

params = transaction_filters_ui("movs")
if accounts:
    options = {"Todas las cuentas": None} | {
        f"{a['name']} ({a['currency']})": a["id"] for a in accounts
    }
    choice = st.selectbox("Cuenta", list(options.keys()))
    if options[choice]:
        params["account_id"] = options[choice]

total = render_transactions_table(params, limit=1000)
st.metric("Total con estos filtros", total)

st.divider()
st.subheader("Importaciones recientes")
batches, error = get_json("/imports")
if error:
    st.warning(error)
elif batches:
    st.dataframe(
        [
            {
                "Fecha": b["created_at"][:19].replace("T", " "),
                "Archivo": b["filename"],
                "Conector": b["connector"],
                "Leídas": b["rows_read"],
                "Insertadas": b["rows_inserted"],
                "Duplicadas": b["rows_duplicated"],
                "Estado": b["status"],
            }
            for b in batches
        ],
        use_container_width=True,
    )
else:
    st.caption("Sin importaciones aún.")
