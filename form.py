import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from supabase import create_client, Client
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase en las variables de entorno.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ========== DATOS DESDE SUPABASE ==========
@st.cache_data(ttl=86400)
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id_comision, nombre_actividad, id_comision_sai, estado_inscripcion, fecha_desde, fecha_hasta"
    ).execute()
    return resp.data if resp.data else []

comisiones = obtener_comisiones()

# Construir DataFrame con columna combinada
filas = []
for c in comisiones:
    filas.append({
        "Actividad (Comisión)": f"{c['nombre_actividad']} ({c['id_comision_sai']})",
        "ID Comisión": c["id_comision"],   # lo ocultamos en la tabla
        "Comisión SAI": c["id_comision_sai"],
        "Estado inscripción": c.get("estado_inscripcion", ""),
        "Fecha inicio": pd.to_datetime(c["fecha_desde"]).strftime("%d/%m/%Y") if c["fecha_desde"] else "",
        "Fecha fin": pd.to_datetime(c["fecha_hasta"]).strftime("%d/%m/%Y") if c["fecha_hasta"] else "",
    })

df_comisiones = pd.DataFrame(filas)

# ========== TABLA AGGRID ==========
st.markdown("### 📋 Seleccioná una comisión (vista_comisiones_abiertas)")

gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(wrapText=True, autoHeight=True, resizable=True)

# Checkbox para selección única
gb.configure_selection(selection_mode="single", use_checkbox=True)

# Ocultar ID técnico
gb.configure_column("ID Comisión", hide=True)

# Ajustar columnas visibles
gb.configure_column("Actividad (Comisión)", flex=40, minWidth=400)
gb.configure_column("Comisión SAI", flex=20)
gb.configure_column("Estado inscripción", flex=20)
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)

# Paginación
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)

grid_options = gb.build()

response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=400,
    theme="balham",
    allow_unsafe_jscode=True,
    key="tabla_comisiones",
    update_mode=GridUpdateMode.SELECTION_CHANGED  # 🔑 clave para refrescar en vivo
)

selected = response.get("selected_rows", [])

# ========== MOSTRAR SELECCIÓN (debug automático) ==========
if selected:
    fila = selected[0]
    st.success("✅ Comisión seleccionada:")
    st.write(f"**Actividad:** {fila['Actividad (Comisión)']}")
    st.write(f"**Comisión SAI:** {fila['Comisión SAI']}")
    st.write(f"**Estado inscripción:** {fila['Estado inscripción']}")
    st.write(f"**Fechas:** {fila['Fecha inicio']} → {fila['Fecha fin']}")
    st.write(f"**ID interno (uuid):** {fila['ID Comisión']}")  # 🔍 uuid interno para inscribir
    st.write("### 🔎 DEBUG - Fila completa seleccionada")
    st.json(fila)
else:
    st.info("⚠️ Seleccioná una comisión para continuar.")
