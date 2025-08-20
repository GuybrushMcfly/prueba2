import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder
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

# ========== DATOS DESDE VIEW ==========
@st.cache_data(ttl=86400)
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id_comision, organismo, id_actividad, nombre_actividad, fecha_inicio, fecha_fin, creditos, modalidad"
    ).execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones()

# ========== ORGANIZACIÓN ==========
actividades_unicas = {}
for c in comisiones_raw:
    if c["id_actividad"] and c["nombre_actividad"]:
        actividades_unicas[c["id_actividad"]] = c["nombre_actividad"]

comisiones = defaultdict(list)
for c in comisiones_raw:
    if c["id_actividad"]:
        comisiones[c["id_actividad"]].append({
            "id": c["id_comision"],
            "nombre": c["nombre_actividad"],
            "fecha_inicio": c["fecha_inicio"],
            "fecha_fin": c["fecha_fin"],
            "organismo": c["organismo"],
            "creditos": c["creditos"],
            "modalidad": c["modalidad"],
        })

def format_fecha(f):
    if f:
        try:
            return pd.to_datetime(f).strftime("%d/%m/%Y")
        except Exception:
            return f
    return ""

# ========== FILTROS ==========
organismos = sorted({c["organismo"] for c in comisiones_raw if c["organismo"]})
modalidades = sorted({c["modalidad"] for c in comisiones_raw if c["modalidad"]})
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

st.title("FORMULARIO DE INSCRIPCIÓN DE CURSOS")
col1, col2 = st.columns(2)
with col1:
    organismo_sel = st.selectbox("Organismo", organismos, index=0)
with col2:
    modalidad_sel = st.selectbox("Modalidad", modalidades, index=0)

st.markdown("#### 1. Seleccioná una comisión en la tabla (usá el checkbox):")

# ========== ARMADO DE FILAS ==========
filas = []
for id_act, nombre_act in actividades_unicas.items():
    coms = comisiones.get(id_act, [])
    if coms:
        for c in coms:
            if (organismo_sel == "Todos" or c["organismo"] == organismo_sel) and \
               (modalidad_sel == "Todos" or c["modalidad"] == modalidad_sel):
                filas.append({
                    "Actividad (Comisión)": f"{nombre_act} ({c['id']})",
                    "Actividad": nombre_act,
                    "Comisión": c["id"],
                    "Fecha inicio": format_fecha(c["fecha_inicio"]),
                    "Fecha fin": format_fecha(c["fecha_fin"]),
                    "Créditos": c["creditos"],
                })
    else:
        filas.append({
            "Actividad (Comisión)": f"{nombre_act} (Sin comisiones)",
            "Actividad": nombre_act,
            "Comisión": "Sin comisiones",
            "Fecha inicio": "",
            "Fecha fin": "",
            "Créditos": "",
        })

# ========== AGGRID ==========
df_comisiones = pd.DataFrame(filas)
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=False, filter=False, resizable=False)
gb.configure_selection(selection_mode="single", use_checkbox=True)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
gb.configure_column("Actividad (Comisión)", flex=50, wrapText=True, autoHeight=True, tooltipField="Actividad (Comisión)", filter=False, resizable=False, minWidth=600, maxWidth=600)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=13)

grid_options = gb.build()

response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=500,
    allow_unsafe_jscode=True,
    theme="balham",
    use_container_width=True
)

selected = response["selected_rows"]
if isinstance(selected, pd.DataFrame):
    selected = selected.to_dict("records")

if selected:
    st.subheader("📋 Datos seleccionados")
    st.json(selected[0])
