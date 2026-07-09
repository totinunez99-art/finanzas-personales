"""Administración — salud del sistema (antes era la pantalla principal)."""

import streamlit as st

from finanzas.dashboard.api_client import api_base_url, get_json

st.set_page_config(page_title="Administración", page_icon="🔧", layout="wide")
st.title("🔧 Administración — Salud del sistema")
st.caption(f"API: {api_base_url()}")

health, health_error = get_json("/health")

if health_error or health is None:
    st.error(f"No hay conexión con la API: {health_error}")
    st.stop()

col_api, col_db, col_migration, col_version = st.columns(4)
col_api.metric("API", "OK" if health.get("status") == "ok" else "DEGRADADA")
col_db.metric("Base de datos", "OK" if health.get("db") else "ERROR")
col_migration.metric("Migración", str(health.get("migration") or "—"))
col_version.metric("Versión", str(health.get("version") or "—"))

st.divider()
st.subheader("Jobs del worker")

summary, summary_error = get_json("/metrics/summary")
if summary_error or summary is None:
    st.warning(f"Sin métricas: {summary_error}")
else:
    jobs = summary.get("jobs", [])
    if jobs:
        st.dataframe(jobs, use_container_width=True)
    else:
        st.info("Sin ejecuciones de jobs aún. El heartbeat corre cada 5 minutos.")

    st.metric("Eventos de dominio", summary.get("domain_events_total", 0))

    flags = summary.get("flags_non_default", {})
    if flags:
        st.subheader("Flags con valor no-default")
        st.json(flags)
