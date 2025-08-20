import streamlit as st
import pandas as pd
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid import GridUpdateMode, DataReturnMode
from supabase import create_client, Client
from collections import defaultdict
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase.")
    st.stop()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ========== UTILIDADES ==========
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

# ARMADO DE TABLA (incluimos el UUID oculto)
filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones[id_act]:
        if (organismo_sel == "Todos" or c.get("organismo") == organismo_sel) and \
           (modalidad_sel == "Todos" or c.get("modalidad") == modalidad_sel):
            filas.append({
                "Actividad (Comisión)": f"{nombre_act} ({c.get('id_comision_sai')})",
                "Actividad": nombre_act,
                "Comisión": c.get("id_comision_sai"),
                "UUID": c.get("id"),   # 👈 lo traemos de la view
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
gb.configure_selection(selection_mode="single", use_checkbox=True)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)

# Ocultamos columnas técnicas
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("UUID", hide=True)

grid_options = gb.build()

st.markdown("#### 1. Seleccioná una comisión (checkbox):")
response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=420,
    theme="balham",
    allow_unsafe_jscode=True,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    key="grid_comisiones_view"
)

# ======== DEBUG MEJORADO ========
st.markdown("### 🐞 DEBUG AgGrid")
st.write("keys:", list(response.keys()))
st.write("selected_rows:", response.get("selected_rows"))
st.write("selected_data:", response.get("selected_data"))
st.write("grid_response.selectedItems:", (response.get("grid_response") or {}).get("selectedItems"))

# ======== EXTRACTOR ROBUSTO ========
def extraer_seleccion(resp) -> list:
    if not isinstance(resp, dict):
        return []
    # revisamos en orden
    cand = (
        resp.get("selected_rows")
        or resp.get("selected_data")
        or (resp.get("grid_response") or {}).get("selectedItems")
        or []
    )
    if cand:
        return cand
    return []

selected = extraer_seleccion(response)

st.markdown("### 🐞 DEBUG: Fila seleccionada (final)")
st.write(selected)

# ======== SI HAY SELECCIÓN ==========
if selected:
    fila = selected[0]
    actividad = fila["Actividad"]
    comision = fila["Comisión"]
    uuid_comision = fila["UUID"]   # 👈 ya lo tenés acá
    st.success(f"Seleccionaste: {actividad} - Comisión {comision} (UUID={uuid_comision})")
