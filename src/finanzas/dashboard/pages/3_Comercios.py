"""Comercios — enseña al sistema y mira cómo aprende (Sprint 3 B2, docs/21)."""

import streamlit as st

from finanzas.dashboard.api_client import get_json, post_json

st.set_page_config(page_title="Comercios", page_icon="🏪", layout="wide")
st.title("🏪 Comercios")
st.caption(
    "Cada corrección tuya se convierte en una regla permanente: el sistema "
    "la aplicará en todas las importaciones futuras."
)

if st.button(
    "🔄 Resolver comercios ahora", help="Aplica reglas y conocimiento a todos los movimientos"
):
    stats, error = post_json("/merchants/backfill", {})
    if error:
        st.error(error)
    else:
        st.success(
            f"Resueltos: {stats['resolved']} nuevos · {stats['provenance_set']} con "
            f"procedencia registrada · {stats['unresolved']} sin evidencia suficiente · "
            f"{stats['untouched_user']} protegidos (corregidos por ti)."
        )

st.divider()
st.subheader("Enséñame: descripciones sin comercio identificado")
groups, error = get_json("/merchants/unresolved")
if error:
    st.error(error)
    st.stop()

if not groups:
    st.success("Todo movimiento con gasto tiene comercio identificado. Nada que enseñar.")
else:
    st.caption("Ordenado por impacto. Escribe el comercio real y presiona Enter.")
    for group in groups[:15]:
        col_desc, col_input = st.columns([3, 2])
        col_desc.write(
            f"`{group['pattern'][:60]}`  \n{group['count']} movimiento(s) · ${group['total']}"
        )
        taught = col_input.text_input(
            "Comercio real",
            key=f"teach_{group['pattern'][:40]}",
            label_visibility="collapsed",
            placeholder="ej: COPEC",
        )
        if taught:
            result, teach_error = post_json(
                "/merchants/teach", {"pattern": group["pattern"], "merchant": taught}
            )
            if teach_error:
                col_input.error(teach_error)
            else:
                col_input.success(f"Aprendido: aplicado a {result['applied_to']} movimiento(s)")

st.divider()
st.subheader("Conocimiento acumulado")
rules, error = get_json("/merchants/rules")
if error:
    st.warning(error)
elif rules:
    origen = {"user": "Enseñada por ti", "promoted": "Promovida", "system_seed": "Semilla"}
    st.dataframe(
        [
            {
                "Patrón": r["pattern"][:50],
                "Comercio": r["merchant"],
                "Origen": origen.get(r["origin"], r["origin"]),
                "Aciertos": r["hits"],
            }
            for r in rules
        ],
        width="stretch",
    )
