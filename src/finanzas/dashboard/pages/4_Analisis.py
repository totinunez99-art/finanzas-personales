"""Centro de Inteligencia Financiera: respuestas, no gráficos (S3-B4, docs/23).

Cada sección responde UNA pregunta. Si un visual no responde una decisión
financiera, no existe.
"""

from datetime import date

import streamlit as st

from finanzas.dashboard.api_client import get_json

st.set_page_config(page_title="Análisis", page_icon="🧠", layout="wide")
st.title("🧠 Análisis financiero")

today = date.today()
months = [f"{y}-{m:02d}" for y in range(today.year, today.year - 2, -1) for m in range(12, 0, -1)]
months = [m for m in months if m <= f"{today.year}-{today.month:02d}"]
col_p, col_a = st.columns([1, 2])
period = col_p.selectbox("Período", months, index=0)

accounts, _ = get_json("/accounts")
options = {"Todas las cuentas": None} | {
    f"{a['name']} ({a['currency']})": a["id"] for a in (accounts or [])
}
choice = col_a.selectbox("Cuenta", list(options.keys()))
params = {"period": period}
if options[choice]:
    params["account_id"] = options[choice]

data, error = get_json("/stats/analytics", params=params)
if error:
    st.error(error)
    st.stop()

st.caption(
    f"Solo flujo operacional: pagos de tarjeta, traspasos propios y reversos están "
    f"excluidos (docs/23). Gasto operacional del período: ${data['total_operational_expense']}."
)

st.subheader("¿Dónde gasto más? — categorías y su % del gasto")
if data["categories"]:
    st.dataframe(
        [
            {"Categoría": c["category"], "Total": f"${c['total']}", "% del gasto": f"{c['pct']}%"}
            for c in data["categories"]
        ],
        width="stretch",
    )
    chart = {c["category"]: float(c["pct"]) for c in data["categories"][:8]}
    st.bar_chart(chart, horizontal=True)  # responde: proporción del gasto por categoría
else:
    st.info("Sin gastos operacionales en el período.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("¿Qué comercios reciben más dinero mío?")
    if data["merchants"]:
        st.dataframe(
            [
                {"Comercio": m["merchant"], "Total": f"${m['total']}", "Veces": m["count"]}
                for m in data["merchants"]
            ],
            width="stretch",
        )
    else:
        st.caption("Sin comercios identificados aún — enséñale en la página Comercios.")
with col2:
    st.subheader("¿Cuáles fueron mis mayores gastos?")
    if data["top_expenses"]:
        st.dataframe(
            [
                {
                    "Fecha": t["date"],
                    "Descripción": t["description"],
                    "Comercio": t["merchant"],
                    "Monto": f"${t['amount']}",
                }
                for t in data["top_expenses"]
            ],
            width="stretch",
        )

col3, col4 = st.columns(2)
with col3:
    st.subheader("¿Qué gastos crecieron más? (vs mes anterior)")
    if data["grew"]:
        st.dataframe(
            [
                {
                    "Categoría": d["category"],
                    "Actual": f"${d['current']}",
                    "Anterior": f"${d['previous']}",
                    "Δ%": f"+{d['delta_pct']}%",
                }
                for d in data["grew"]
            ],
            width="stretch",
        )
    else:
        st.caption("Sin categorías al alza (o sin base de comparación).")
with col4:
    st.subheader("¿Qué gastos disminuyeron?")
    if data["declined"]:
        st.dataframe(
            [
                {
                    "Categoría": d["category"],
                    "Actual": f"${d['current']}",
                    "Anterior": f"${d['previous']}",
                    "Δ%": f"{d['delta_pct']}%",
                }
                for d in data["declined"]
            ],
            width="stretch",
        )
    else:
        st.caption("Sin categorías a la baja (o sin base de comparación).")

st.subheader("¿Cuál es mi flujo de caja del período?")
if data["daily"]:
    st.line_chart(
        {d["date"]: float(d["cumulative_net"]) for d in data["daily"]}
    )  # responde: ¿me estoy quedando corto a mitad de mes?
    if data["most_expensive_day"]:
        med = data["most_expensive_day"]
        st.caption(f"Día más caro: {med['date']} con ${med['expense']} en cargos.")

col5, col6 = st.columns(2)
with col5:
    st.subheader("¿Qué semanas fueron más costosas?")
    if data["weekly"]:
        st.bar_chart({w["week"]: float(w["expense"]) for w in data["weekly"]})
with col6:
    st.subheader("¿Qué comercios aparecen por primera vez?")
    if data["new_merchants"]:
        st.dataframe(
            [
                {"Comercio": n["merchant"], "Primera vez": n["first_seen"]}
                for n in data["new_merchants"]
            ],
            width="stretch",
        )
    else:
        st.caption("Ningún comercio nuevo este período.")

st.subheader("¿Qué gastos parecen anormales?")
if data["anomalies"]:
    st.warning(f"{len(data['anomalies'])} cargo(s) sobre el umbral de anomalía:")
    st.dataframe(
        [
            {
                "Fecha": a["date"],
                "Descripción": a["description"],
                "Monto": f"${a['amount']}",
                "Umbral": f"${a['threshold']}",
            }
            for a in data["anomalies"]
        ],
        width="stretch",
    )
elif data["anomalies_note"]:
    st.caption(data["anomalies_note"])
else:
    st.success("Ningún cargo supera el umbral de anomalía del período.")

with st.expander("¿Cómo se calcula todo esto?"):
    st.json(data["method_notes"])
