"""Componentes compartidos del dashboard (home y página Movimientos usan la
misma tabla con filtros: una sola implementación)."""

from typing import Any

import streamlit as st

from finanzas.dashboard.api_client import get_json

_CLP_CURRENCIES = {"CLP"}


def format_amount(amount: str, currency: str) -> str:
    """CLP sin decimales con separador de miles chileno; otras monedas tal cual."""
    try:
        value = float(amount)
    except ValueError:
        return amount
    if currency in _CLP_CURRENCIES:
        return f"${value:,.0f}".replace(",", ".")
    return f"{value:,.2f} {currency}"


def transaction_filters_ui(key_prefix: str) -> dict[str, Any]:
    """Controles de búsqueda/filtros. Devuelve query params para la API."""
    params: dict[str, Any] = {}
    col_q, col_kind, col_from, col_to = st.columns([3, 1, 1, 1])
    q = col_q.text_input("Buscar en descripción", key=f"{key_prefix}_q")
    kind = col_kind.selectbox("Tipo", ["Todos", "cargo", "abono"], key=f"{key_prefix}_kind")
    date_from = col_from.date_input("Desde", value=None, key=f"{key_prefix}_from")
    date_to = col_to.date_input("Hasta", value=None, key=f"{key_prefix}_to")
    col_min, col_max = st.columns(2)
    amount_min = col_min.number_input(
        "Monto mínimo (magnitud)", min_value=0, value=0, step=1000, key=f"{key_prefix}_min"
    )
    amount_max = col_max.number_input(
        "Monto máximo (0 = sin tope)", min_value=0, value=0, step=1000, key=f"{key_prefix}_max"
    )

    if q:
        params["q"] = q
    if kind != "Todos":
        params["kind"] = kind
    if date_from:
        params["date_from"] = date_from.isoformat()
    if date_to:
        params["date_to"] = date_to.isoformat()
    if amount_min > 0:
        params["amount_min"] = amount_min
    if amount_max > 0:
        params["amount_max"] = amount_max
    return params


def render_transactions_table(
    params: dict[str, Any], limit: int = 500, compact: bool = False
) -> int:
    """Pinta la tabla de movimientos. Devuelve el total (para métricas/enlaces)."""
    data, error = get_json("/transactions", params={"limit": limit, **params})
    if error:
        st.error(error)
        return 0
    items = data["items"]
    if not items:
        st.info("Sin movimientos para estos filtros.")
        return int(data["total"])

    rows = [
        {
            "Fecha": t["posted_at"],
            "Descripción": t["description"],
            "Monto": format_amount(t["amount"], t["currency"]),
            "Tipo": t["kind"],
            "Categoría": t["category"] or "Sin clasificar",
            "Estado": t["status"],
        }
        for t in items
    ]
    st.dataframe(rows, use_container_width=True, height=300 if compact else 600)
    return int(data["total"])
