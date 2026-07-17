"""Dashboard financiero inteligente — pantalla principal (Sprint 3, Bloque 1).

Responde preguntas financieras; lo técnico vive en Administración.
Regla anti-engaño: sin base de comparación => se dice, no se inventa un delta.
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

# ---------------------------------------------------------------- filtros globales
today = date.today()
months = [f"{y}-{m:02d}" for y in range(today.year, today.year - 2, -1) for m in range(12, 0, -1)]
months = [m for m in months if m <= f"{today.year}-{today.month:02d}"]

accounts, acc_error = get_json("/accounts")
if acc_error:
    st.error(f"Sin conexión con la API: {acc_error}")
    st.page_link("pages/9_Administracion.py", label="Revisar salud del sistema →", icon="🔧")
    st.stop()

col_period, col_account = st.columns([1, 2])
period = col_period.selectbox(
    "Período",
    months,
    index=0,
    format_func=lambda p: f"{p} (este mes)" if p == months[0] else p,
)
account_options = {"Todas las cuentas": None} | {
    f"{a['name']} ({a['currency']})": a["id"] for a in (accounts or [])
}
account_choice = col_account.selectbox(
    "Cuenta",
    list(account_options.keys()),
    help="Si tienes datos demo y reales, elige tu cuenta real para no mezclarlos.",
)
params: dict[str, str] = {"period": period}
if account_options[account_choice]:
    params["account_id"] = account_options[account_choice]

stats, error = get_json("/stats/summary", params=params)
if error:
    st.error(f"Sin conexión con la API: {error}")
    st.stop()

# ---------------------------------------------------------------- KPIs (CLP primero)
clp = next((c for c in stats["by_currency"] if c["currency"] == "CLP"), None)


def _delta(value: str | None, suffix: str = "% vs mes anterior") -> str | None:
    return f"{value}{suffix}" if value is not None else None


k1, k2, k3, k4 = st.columns(4)
if clp:
    k1.metric(
        "Gastos del mes",
        format_amount(clp["expense"], "CLP"),
        delta=_delta(clp["expense_delta_pct"]),
        delta_color="inverse",  # gastar más = rojo
        help="Suma de cargos (CLP). Delta solo si el mes anterior tiene datos.",
    )
    k2.metric(
        "Ingresos del mes",
        format_amount(clp["income"], "CLP"),
        delta=_delta(clp["income_delta_pct"]),
        help="Suma de abonos (CLP).",
    )
    k3.metric("Flujo neto", format_amount(clp["net"], "CLP"), help="Ingresos menos gastos.")
    k4.metric(
        "Tasa de ahorro",
        f"{clp['savings_rate_pct']}%" if clp["savings_rate_pct"] is not None else "—",
        help="Flujo neto / ingresos. '—' si no hubo ingresos en el período.",
    )
    k5, k6, k7, k8 = st.columns(4)
    k5.metric(
        "Gasto promedio diario",
        format_amount(clp["avg_daily_expense"], "CLP")
        if clp["avg_daily_expense"] is not None
        else "—",
        help=f"Gastos / {stats['days_in_scope']} días del período.",
    )
    k6.metric(
        "Movimientos",
        clp["count"],
        delta=f"{clp['count_delta']:+d} vs mes anterior"
        if clp["count_delta"] is not None
        else None,
        delta_color="off",
    )
    k7.metric("Comparado con", stats["previous_period"])
    last = stats.get("last_import")
    k8.metric(
        "Última importación",
        last["created_at"][:10] if last else "—",
        help=(f"{last['filename']} · {last['connector']} · {last['status']}" if last else None),
    )
else:
    st.info("Sin movimientos CLP en este período. Importa una cartola para empezar.")
    st.page_link("pages/1_Importar.py", label="Importar cartola", icon="📥")

others = [c for c in stats["by_currency"] if c["currency"] != "CLP"]
if others:
    with st.expander("Otras monedas del período (no se mezclan con CLP)"):
        for c in others:
            st.write(
                f"**{c['currency']}** — ingresos {c['income']}, gastos {c['expense']}, "
                f"neto {c['net']} ({c['count']} movs.)"
            )

st.divider()

# ---------------------------------------------------------------- Insights
st.subheader("💡 Insights")
insights, ins_error = get_json("/stats/insights", params=params)
if ins_error:
    st.warning(f"Insights no disponibles: {ins_error}")
elif not insights:
    st.caption(
        "Sin observaciones para este período: aún no hay evidencia suficiente "
        "(cada insight exige umbrales mínimos de datos — no inventamos conclusiones)."
    )
else:
    renderer = {"warning": st.warning, "notable": st.info, "info": st.info}
    for insight in insights:
        show = renderer.get(insight["severity"], st.info)
        show(f"**{insight['title']}**  \n{insight['description']}")
        with st.expander("¿Cómo se calculó?", expanded=False):
            st.write(insight["explanation"])
            st.json(insight["data"])

st.divider()

# ---------------------------------------------------------------- movimientos
st.subheader("Movimientos")
filter_params = transaction_filters_ui("home")
if account_options[account_choice]:
    filter_params["account_id"] = account_options[account_choice]
total = render_transactions_table(filter_params, limit=200, compact=True)
if total > 200:
    st.caption(f"Mostrando 200 de {total}.")
    st.page_link("pages/2_Movimientos.py", label="Ver todos con más espacio →", icon="📄")
