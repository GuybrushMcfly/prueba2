import streamlit as st
import pandas as pd
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder
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

organismos = sorted({c.get("organismo") for c in comisiones_raw if c.get("organismo")})
modalidades = sorted({c.get("modalidad") for c in comisiones_raw if c.get("modalidad")})
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

col1, col2 = st.columns(2)
organismo_sel = col1.selectbox("Organismo", organismos, index=0)
modalidad_sel = col2.selectbox("Modalidad", modalidades, index=0)

filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones[id_act]:
        if (organismo_sel == "Todos" or c.get("organismo") == organismo_sel) and \
           (modalidad_sel == "Todos" or c.get("modalidad") == modalidad_sel):
            filas.append({
                "Actividad (Comisión)": f"{nombre_act} ({c.get('id_comision_sai')})",
                "Actividad": nombre_act,
                "Comisión": c.get("id_comision_sai"),
                "UUID": c.get("id_comision"),  # UUID real
                "Fecha inicio": format_fecha(c.get("fecha_desde")),
                "Fecha fin": format_fecha(c.get("fecha_hasta")),
                "Créditos": c.get("creditos", ""),
            })

df_comisiones = pd.DataFrame(filas)
df_comisiones = df_comisiones.sort_values(by="Actividad (Comisión)").reset_index(drop=True)  # Evita "reordenamientos"

if df_comisiones.empty:
    st.warning("No hay comisiones disponibles con los filtros seleccionados.")
    st.stop()

# ========== AGGRID ==========
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True, filter=False, resizable=False)
gb.configure_selection(selection_mode="single", use_checkbox=True)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
gb.configure_column("Actividad (Comisión)", flex=60, tooltipField="Actividad (Comisión)", minWidth=600)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("UUID", hide=True)
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=10)
grid_options = gb.build()

st.markdown("#### 1. Seleccioná una comisión (checkbox):")

response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=420,
    theme="balham",
    allow_unsafe_jscode=True
)

# ========== EXTRACTOR SELECCIÓN ==========
selected = response.get("selected_rows", [])
if isinstance(selected, pd.DataFrame):
    selected = selected.to_dict("records")

if selected:
    st.session_state["fila_sel"] = selected[0]
elif "fila_sel" in st.session_state:
    selected = [st.session_state["fila_sel"]]

st.markdown("### 🐞 DEBUG: Fila seleccionada (final)")
st.write(selected)

# ========== SI HAY SELECCIÓN ==========
if selected:
    fila = selected[0]
    st.success(f"Seleccionaste: {fila['Actividad']} - Comisión {fila['Comisión']} (UUID={fila['UUID']})")
else:
    st.info("☝️ Seleccioná una comisión de la tabla para continuar.")
