import streamlit as st
import pandas as pd
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid import GridUpdateMode, DataReturnMode
from supabase import create_client, Client
from collections import defaultdict
from io import BytesIO
from fpdf import FPDF
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase.")
    st.stop()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ========== UTILIDADES ==========
def validar_cuil(cuil: str) -> bool:
    if not cuil.isdigit() or len(cuil) != 11:
        return False
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(cuil[i]) * mult[i] for i in range(10))
    verificador = 11 - (total % 11)
    verificador = 0 if verificador == 11 else (9 if verificador == 10 else verificador)
    return verificador == int(cuil[-1])

def format_fecha(f):
    if f:
        try:
            return pd.to_datetime(f).strftime("%d/%m/%Y")
        except Exception:
            return f
    return ""

@st.cache_data(ttl=86400)
def obtener_comisiones_abiertas():
    resp = supabase.table("vista_comisiones_abiertas").select("*").execute()
    return resp.data if resp.data else []

# ========== UI ==========
st.set_page_config(layout="wide")
st.title("FORMULARIO DE INSCRIPCIÓN A CAPACITACIONES")

# ========== CARGA Y AGRUPAMIENTO ==========
comisiones_raw = obtener_comisiones_abiertas()
actividades_unicas = {}
comisiones = defaultdict(list)
for c in comisiones_raw:
    act_id = c.get("id_actividad")
    act_nombre = c.get("nombre_actividad")
    if act_id and act_nombre:
        actividades_unicas[act_id] = act_nombre
        comisiones[act_id].append(c)

# FILTROS
organismos = sorted({c.get("organismo") for c in comisiones_raw if c.get("organismo")})
modalidades = sorted({c.get("modalidad") for c in comisiones_raw if c.get("modalidad")})
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

col1, col2 = st.columns(2)
organismo_sel = col1.selectbox("Organismo", organismos, index=0)
modalidad_sel = col2.selectbox("Modalidad", modalidades, index=0)

# ARMADO DE TABLA
filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones[id_act]:
        if (organismo_sel == "Todos" or c.get("organismo") == organismo_sel) and \
           (modalidad_sel == "Todos" or c.get("modalidad") == modalidad_sel):
            filas.append({
                "Actividad (Comisión)": f"{nombre_act} ({c.get('id_comision_sai')})",
                "Actividad": nombre_act,
                "Comisión": c.get("id_comision_sai"),
                "UUID": c.get("id_comision"),   # 👈 ahora usamos el UUID real
                "Fecha inicio": format_fecha(c.get("fecha_desde")),
                "Fecha fin": format_fecha(c.get("fecha_hasta")),
                "Créditos": c.get("creditos", ""),
            })

df_comisiones = pd.DataFrame(filas).reset_index(drop=True)

if df_comisiones.empty:
    st.warning("No hay comisiones disponibles con los filtros seleccionados.")
    st.stop()

# ========== AGGRID ==========
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True, filter=False, resizable=False)
pre_sel = [0] if len(df_comisiones) > 0 else []
gb.configure_selection(selection_mode="single", use_checkbox=True, pre_selected_rows=pre_sel)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)

gb.configure_column("Actividad (Comisión)", flex=60, tooltipField="Actividad (Comisión)", minWidth=600)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("UUID", hide=True)  # ocultamos el UUID pero lo tenemos en la data
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=10)

grid_options = gb.build()
grid_options["rowSelection"] = "single"
grid_options["suppressRowClickSelection"] = False
grid_options["rowDeselection"] = True

st.markdown("#### 1. Seleccioná una comisión (checkbox):")
response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=420,
    theme="balham",
    allow_unsafe_jscode=True,
    update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.MODEL_CHANGED,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    key="grid_comisiones_view"
)

# ======== DEBUG COMPLETO ========
st.markdown("### 🐞 DEBUG AgGrid")
st.write("keys:", list(response.keys()))
st.write("selected_rows:", response.get("selected_rows"))
st.write("selected_data:", response.get("selected_data"))
st.write("event_data:", response.get("event_data"))
st.write("grid_state:", response.get("grid_state"))
st.write("grid_response:", response.get("grid_response"))

# ======== EXTRACTOR ROBUSTO ========
def extraer_seleccion(resp) -> list:
    if not isinstance(resp, dict):
        return []
    cand = (
        resp.get("selected_rows")
        or resp.get("selected_data")
        or (resp.get("grid_response") or {}).get("selected_rows")
        or (resp.get("grid_response") or {}).get("selected_data")
        or []
    )
    return cand if cand else []

selected = extraer_seleccion(response)

if selected:
    st.session_state["fila_sel"] = selected[0]
elif "fila_sel" in st.session_state:
    selected = [st.session_state["fila_sel"]]

st.markdown("### 🐞 DEBUG: Fila seleccionada (final)")
st.write(selected)

# ========== SI HAY SELECCIÓN ==========
if selected:
    fila = selected[0]
    actividad = fila["Actividad"]
    comision = fila["Comisión"]
    uuid_comision = fila["UUID"]
    fecha_ini = fila["Fecha inicio"]
    fecha_fin = fila["Fecha fin"]

    st.success(f"Seleccionaste: {actividad} - Comisión {comision} (UUID={uuid_comision})")

    # Campo CUIL siempre visible al seleccionar
    raw = st.text_input("CUIL/CUIT *", value=st.session_state.get("cuil", ""))
    cuil = ''.join(filter(str.isdigit, raw))[:11]

    if st.button("Validar CUIL", type="primary"):
        if not validar_cuil(cuil):
            st.error("CUIL inválido. Debe tener 11 dígitos.")
            st.stop()

        agente = supabase.table("agentes").select("*").eq("cuil", cuil).execute()
        st.write("🔎 DEBUG agente:", agente.data)
        if not agente.data:
            st.error("No se encontró ese agente.")
            st.stop()

        ya = supabase.table("cursos_inscripciones") \
            .select("id") \
            .eq("cuil", cuil) \
            .eq("comision_id", uuid_comision) \
            .limit(1).execute()
        st.write("🔎 DEBUG ya_inscripto:", ya.data)
        if ya.data:
            st.warning("Ya estás inscripto en esta comisión.")
            st.stop()

        datos = agente.data[0]
        st.success("CUIL válido. Completá tus datos para confirmar inscripción.")
        st.session_state["cuil"] = cuil

        col1, col2 = st.columns(2)
        apellido = col1.text_input("Apellido", value=datos.get("apellido", ""))
        nombre = col2.text_input("Nombre", value=datos.get("nombre", ""))
        correo = st.text_input("Correo electrónico", value=datos.get("email", ""))
        tramo = st.text_input("Tramo", value=datos.get("tramo", ""))

        if st.button("Confirmar inscripción"):
            nueva = {
                "cuil": cuil,
                "comision_id": uuid_comision,  # 👈 usamos el UUID real
                "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d"),
                "apellido": apellido,
                "nombre": nombre,
                "email": correo,
                "tramo": tramo,
            }

            st.write("📦 DEBUG INSERT cursos_inscripciones:", nueva)
            res = supabase.table("cursos_inscripciones").insert(nueva).execute()
            st.write("📬 DEBUG respuesta insert:", {"data": res.data, "error": getattr(res, "error", None)})

            if getattr(res, "error", None):
                st.error(f"❌ Error al registrar la inscripción: {res.error}")
            elif res.data:
                st.success("✅ Inscripción registrada correctamente")

                # -------- Constancia PDF --------
                def generar_constancia_pdf(nombre_completo, actividad, comision, fecha_inicio, fecha_fin):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.set_text_color(19, 106, 193)
                    pdf.cell(0, 10, "Constancia de Preinscripción", ln=True, align="C")
                    pdf.set_font("Helvetica", "", 12)
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(10)
                    pdf.multi_cell(0, 10,
                        f"{nombre_completo}, te preinscribiste exitosamente en:\n\n"
                        f"Actividad: {actividad}\n"
                        f"Comisión: {comision}\n"
                        f"Inicio: {fecha_inicio}\n"
                        f"Fin: {fecha_fin}\n\n"
                        f"Esta inscripción no garantiza vacante. "
                        f"Recibirás confirmación por correo si es otorgada.\n\n"
                        f"Fecha de registro: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                    )
                    return BytesIO(pdf.output(dest='S').encode("latin1"))

                buffer = generar_constancia_pdf(f"{nombre} {apellido}", actividad, comision, fecha_ini, fecha_fin)
                st.download_button(
                    label="📄 Descargar constancia",
                    data=buffer,
                    file_name="constancia_inscripcion.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ Ocurrió un error al registrar la inscripción.")
else:
    st.info("☝️ Seleccioná una comisión de la tabla para continuar.")
