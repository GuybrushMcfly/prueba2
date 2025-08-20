import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder
from supabase import create_client, Client
from collections import defaultdict
import time
from fpdf import FPDF
from io import BytesIO
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase en las variables de entorno.")
    st.stop()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ========== VALIDACIÓN DE CUIL ==========
def validar_cuil(cuil: str) -> bool:
    if not cuil.isdigit() or len(cuil) != 11:
        return False
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(cuil[i]) * mult[i] for i in range(10))
    verificador = 11 - (total % 11)
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    return verificador == int(cuil[-1])

# ========== DATOS DESDE LA VIEW ==========
@st.cache_data(ttl=86400)
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select("*").execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones()

# ========== PROCESAMIENTO ==========
actividades_unicas = {}
comisiones = defaultdict(list)
for c in comisiones_raw:
    act_id = c.get("id_actividad")
    act_nombre = c.get("nombre_actividad")
    if act_id and act_nombre:
        actividades_unicas[act_id] = act_nombre
        comisiones[act_id].append(c)

def format_fecha(f):
    try:
        return pd.to_datetime(f).strftime("%d/%m/%Y") if f else ""
    except:
        return f

organismos = sorted({c.get("organismo") for c in comisiones_raw if c.get("organismo")})
modalidades = sorted({c.get("modalidad") for c in comisiones_raw if c.get("modalidad")})
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

st.set_page_config(layout="wide")
st.title("FORMULARIO DE INSCRIPCIÓN DE CURSOS")
col1, col2 = st.columns(2)
organismo_sel = col1.selectbox("Organismo", organismos)
modalidad_sel = col2.selectbox("Modalidad", modalidades)

st.markdown("#### 1. Seleccioná una comisión en la tabla (usá el checkbox):")

filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones.get(id_act, []):
        if (organismo_sel == "Todos" or c.get("organismo") == organismo_sel) and \
           (modalidad_sel == "Todos" or c.get("modalidad") == modalidad_sel):
            filas.append({
                "Actividad (Comisión)": f"{nombre_act} ({c.get('id_comision_sai')})",
                "Actividad": nombre_act,
                "Comisión": c.get("id_comision_sai"),
                "UUID": c.get("id_comision"),
                "Fecha inicio": format_fecha(c.get("fecha_desde")),
                "Fecha fin": format_fecha(c.get("fecha_hasta")),
                "Créditos": c.get("creditos") or "",
            })

if not filas:
    st.warning("No hay comisiones disponibles.")
    st.stop()

df_comisiones = pd.DataFrame(filas)

# ========== AGGRID ==========
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True, filter=False, resizable=True)
gb.configure_selection(selection_mode="single", use_checkbox=True)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
gb.configure_column("Actividad (Comisión)", flex=60, tooltipField="Actividad (Comisión)", minWidth=600)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("UUID", hide=True)
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=10)

response = AgGrid(
    df_comisiones,
    gridOptions=gb.build(),
    height=420,
    theme="balham",
    allow_unsafe_jscode=True
)

selected = response.get("selected_rows", [])
if isinstance(selected, pd.DataFrame):
    selected = selected.to_dict("records")

st.markdown("### 🔜 DEBUG - Fila seleccionada")
st.write(selected)
