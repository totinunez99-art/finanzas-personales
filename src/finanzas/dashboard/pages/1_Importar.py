"""Import Wizard — UI (docs/14): arrastrar → detectar → previsualizar → confirmar."""

import streamlit as st

from finanzas.dashboard.api_client import get_json, post_file, post_json

st.set_page_config(page_title="Importar cartola", page_icon="📥", layout="wide")
st.title("📥 Importar cartola")

# ---------------------------------------------------------------- cuentas
accounts, error = get_json("/accounts")
if error:
    st.error(f"Sin conexión con la API: {error}")
    st.stop()

with st.expander("Crear cuenta nueva", expanded=not accounts), st.form("nueva_cuenta"):
    name = st.text_input("Nombre", placeholder="Cuenta Corriente")
    bank = st.text_input("Banco", value="bancochile")
    col1, col2 = st.columns(2)
    account_type = col1.selectbox(
        "Tipo", ["checking", "credit_card", "savings", "credit_line", "cash"]
    )
    currency = col2.selectbox("Moneda", ["CLP", "USD", "UF"])
    if st.form_submit_button("Crear"):
        _, create_error = post_json(
            "/accounts",
            {"name": name, "bank": bank, "type": account_type, "currency": currency},
        )
        if create_error:
            st.error(create_error)
        else:
            st.success("Cuenta creada")
            st.rerun()

if not accounts:
    st.info("Crea una cuenta para poder importar.")
    st.stop()

account_labels = {f"{a['name']} ({a['bank']}, {a['currency']})": a["id"] for a in accounts}
selected = st.selectbox("Cuenta destino", list(account_labels.keys()))
account_id = account_labels[selected]

# ---------------------------------------------------------------- archivo
uploaded = st.file_uploader(
    "Arrastra tu cartola aquí",
    type=["csv", "xlsx", "pdf"],
    help="Formatos compatibles: cartola PDF de Banco de Chile/Edwards (con su contraseña) "
    "y CSV de referencia (fecha;descripcion;monto[;moneda]).",
)

if uploaded is None:
    st.stop()

content = uploaded.getvalue()

# ---------------------------------------------------------------- contraseña (PDF protegido)
# La clave vive solo en el estado de esta página y en el request; jamás se almacena.
password = st.session_state.get("import_pdf_password", "")
request_data = {"account_id": account_id}
if password:
    request_data["password"] = password

# ---------------------------------------------------------------- preview
preview, error = post_file("/imports/preview", uploaded.name, content, request_data)
if error:
    st.error(f"El archivo no se pudo procesar: {error}")
    st.stop()

if preview.get("password_required"):
    st.warning(preview["message"])
    st.text_input(
        "Contraseña del PDF",
        type="password",
        key="import_pdf_password",
        help="Se usa una sola vez para leer el archivo. No se guarda en ninguna parte.",
    )
    st.stop()  # al escribirla, Streamlit re-ejecuta y el preview se reintenta con la clave

if not preview["recognized"]:
    st.warning(preview["message"])
    st.stop()

st.success(
    f"Reconocido: **{preview['bank']}** · parser `{preview['parser_name']}` "
    f"v{preview.get('parser_version', '?')} — {preview['detection_reason']}"
)

confidence = preview.get("extraction_confidence")
checks = preview.get("validation", [])
if checks or confidence is not None:
    with st.expander(
        f"Validación de integridad: {sum(1 for c in checks if c['passed'])}/{len(checks)} "
        f"chequeos OK · confianza de extracción {confidence if confidence is not None else '—'}",
        expanded=any(not c["passed"] for c in checks),
    ):
        for c in checks:
            icon = "✅" if c["passed"] else "❌"
            detail = (
                f" (esperado {c['expected']}, observado {c['actual']})" if c["expected"] else ""
            )
            st.write(f"{icon} {c['name']}{detail}")

col_a, col_b, col_c = st.columns(3)
col_a.metric("Movimientos en el archivo", preview["total_rows"])
col_b.metric("Ya existentes (se omitirán)", preview["duplicates_in_db"])
col_c.metric("Nuevos a importar", preview["total_rows"] - preview["duplicates_in_db"])

if preview["file_already_imported"]:
    st.error("Este archivo EXACTO ya fue importado en esta cuenta. Confirmar no tendrá efecto.")

for warning in preview.get("warnings", []):
    st.warning(warning)

st.subheader(f"Vista previa (primeros {len(preview['sample'])} de {preview['total_rows']})")
st.dataframe(preview["sample"], width="stretch")

# ---------------------------------------------------------------- confirmar
st.caption("Nada se ha guardado todavía. Cerrar esta página cancela la importación.")
if st.button(
    "✅ Confirmar importación",
    type="primary",
    disabled=preview["file_already_imported"],
):
    batch, import_error = post_file("/imports", uploaded.name, content, request_data)
    if import_error:
        st.error(import_error)
    else:
        st.success(
            f"Importación completa: {batch['rows_inserted']} nuevos, "
            f"{batch['rows_duplicated']} duplicados omitidos "
            f"(estado: {batch['status']})."
        )
        st.page_link("pages/2_Movimientos.py", label="Ver movimientos →", icon="📄")
