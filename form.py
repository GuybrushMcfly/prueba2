import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder
from supabase import create_client, Client
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase en las variables de entorno.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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

# ========== CONFIGURACIÓN DE PÁGINA ==========
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    .block-container {
        max-width: 100vw !important;
        padding-left: 2vw;
        padding-right: 2vw;
    }
    </style>
""", unsafe_allow_html=True)

# ========== DATOS DESDE SUPABASE ==========
@st.cache_data(ttl=86400)  # 1 día
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id_comision, organismo, id_actividad, nombre_actividad, fecha_inicio, fecha_fin, creditos, modalidad"
    ).execute()
    return resp.data if resp.data else []

# --- OBTENER DATOS ---
comisiones_raw = obtener_comisiones()

# --- FORMATEAR PARA PANDAS ---
filas = []
for c in comisiones_raw:
    filas.append({
        "Actividad (Comisión)": f"{c['nombre_actividad']} ({c['id_comision']})",
        "Actividad": c["nombre_actividad"],
        "Comisión": c["id_comision"],
        "Fecha inicio": pd.to_datetime(c["fecha_inicio"]).strftime("%d/%m/%Y") if c["fecha_inicio"] else "",
        "Fecha fin": pd.to_datetime(c["fecha_fin"]).strftime("%d/%m/%Y") if c["fecha_fin"] else "",
        "Créditos": c["creditos"],
        "Organismo": c["organismo"],
        "Modalidad": c["modalidad"],
    })

df_comisiones = pd.DataFrame(filas)

# ========== TABLA AGGRID ==========
st.markdown("### 📋 Seleccioná una comisión para inscribirte")

gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_selection(selection_mode="single", use_checkbox=True)  # ✅ Checkbox
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)

# Mostrar solo columnas relevantes
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)

# Actividad visible
gb.configure_column("Actividad (Comisión)", flex=50, minWidth=500, tooltipField="Actividad (Comisión)")
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=10)

grid_options = gb.build()

response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=400,
    theme="balham",
    allow_unsafe_jscode=True,
    key="tabla_comisiones"
)

selected = response.get("selected_rows", [])

# ========== MOSTRAR SELECCIÓN ==========
if selected and isinstance(selected[0], dict):
    fila = selected[0]
    st.success("✅ Comisión seleccionada:")
    st.write(f"**Actividad:** {fila['Actividad']}")
    st.write(f"**Comisión:** {fila['Comisión']}")
    st.write(f"**Fechas:** {fila['Fecha inicio']} → {fila['Fecha fin']}")
    st.write(f"**Créditos:** {fila['Créditos']}")
else:
    st.info("⚠️ Seleccioná una comisión para continuar.")
