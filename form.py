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
@st.cache_data(ttl=86400)
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id_comision, nombre_actividad, id_comision_sai, fecha_desde, fecha_hasta"
    ).execute()
    return resp.data if resp.data else []

comisiones = obtener_comisiones()

# Construir DataFrame con columna combinada
filas = []
for c in comisiones:
    filas.append({
        "Actividad (Comisión)": f"{c['nombre_actividad']} ({c['id_comision_sai']})",
        "Actividad": c["nombre_actividad"],
        "Comisión": c["id_comision_sai"],
        "Fecha inicio": pd.to_datetime(c["fecha_desde"]).strftime("%d/%m/%Y") if c["fecha_desde"] else "",
        "Fecha fin": pd.to_datetime(c["fecha_hasta"]).strftime("%d/%m/%Y") if c["fecha_hasta"] else "",
    })

df_comisiones = pd.DataFrame(filas)
st.dataframe(df_comisiones)


# ========== TABLA AGGRID ==========
st.markdown("### 📋 Seleccioná una comisión (vista_comisiones_abiertas)")

gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_selection(selection_mode="single", use_checkbox=True)  # ✅ Checkbox
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)

# Ocultar ID técnico
gb.configure_column("ID Comisión", hide=True)

# Ajustar columnas visibles
gb.configure_column("Actividad (Comisión)", flex=40, minWidth=400)
gb.configure_column("Comisión SAI", flex=20)
gb.configure_column("Estado inscripción", flex=15)
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)

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
    st.write(f"**Comisión SAI:** {fila['Comisión SAI']}")
    st.write(f"**Estado:** {fila['Estado inscripción']}")
    st.write(f"**Fechas:** {fila['Fecha inicio']} → {fila['Fecha fin']}")
else:
    st.info("⚠️ Seleccioná una comisión para continuar.")
