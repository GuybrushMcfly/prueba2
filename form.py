import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder
from supabase import create_client, Client
from collections import defaultdict
import time
from io import BytesIO
from fpdf import FPDF
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase en las variables de entorno.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ========== UTILIDAD ==========
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

def format_fecha(f):
    if f:
        try:
            return pd.to_datetime(f).strftime("%d/%m/%Y")
        except Exception:
            return f
    return ""

# ========== CARGA DE COMISIONES DESDE VIEW ==========
@st.cache_data(ttl=86400)
def obtener_comisiones_abiertas():
    resp = supabase.table("vista_comisiones_abiertas").select("*").execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones_abiertas()

# Agrupamiento por actividad
actividades_unicas = {}
comisiones = defaultdict(list)
for c in comisiones_raw:
    act_id = c.get("id_actividad")
    act_nombre = c.get("nombre_actividad")
    if act_id and act_nombre:
        actividades_unicas[act_id] = act_nombre
        comisiones[act_id].append({
            "id": c["id_comision_sai"],
            "nombre": act_nombre,
            "fecha_inicio": c["fecha_desde"],
            "fecha_fin": c["fecha_hasta"],
            "organismo": c["organismo"],
            "creditos": c["creditos"],
            "modalidad": c["modalidad_cursada"],
        })

# ========== UI ==========
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    .block-container { max-width: 100vw !important; padding-left: 2vw; padding-right: 2vw; }
    </style>
""", unsafe_allow_html=True)

st.title("FORMULARIO DE INSCRIPCIÓN A CAPACITACIONES")

# FILTROS
organismos = sorted({c["organismo"] for c in comisiones_raw if c["organismo"]})
modalidades = sorted({c["modalidad_cursada"] for c in comisiones_raw if c["modalidad_cursada"]})
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

col1, col2 = st.columns(2)
with col1:
    organismo_sel = st.selectbox("Organismo", organismos, index=0)
with col2:
    modalidad_sel = st.selectbox("Modalidad", modalidades, index=0)

# ARMADO DE FILAS PARA AGGRID
filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones.get(id_act, []):
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

df_comisiones = pd.DataFrame(filas)

# AGGRID CONFIG
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True, resizable=False)
gb.configure_selection("single", use_checkbox=True)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("Actividad (Comisión)", minWidth=600, maxWidth=600, wrapText=True)
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=10)

grid_options = gb.build()
custom_css = {
    ".ag-header": {"background-color": "#136ac1 !important", "color": "white !important", "font-weight": "bold !important"},
    ".ag-row": {"font-size": "14px !important"},
    ".ag-row:nth-child(even)": {"background-color": "#f5f5f5 !important"},
    ".ag-cell": {
        "white-space": "normal !important",
        "line-height": "1.2 !important",
        "vertical-align": "middle !important"
    }
}

response = AgGrid(df_comisiones, gridOptions=grid_options, custom_css=custom_css, theme="balham", height=500)

# SELECCIÓN DE COMISIÓN
selected = response["selected_rows"]
if selected:
    fila = selected[0]
    act = fila["Actividad"]
    com = fila["Comisión"]
    f_ini = fila["Fecha inicio"]
    f_fin = fila["Fecha fin"]

    st.markdown(f"""
    <h4>2. Validá tu CUIL para inscribirte en</h4>
    <span style="color:#b72877;font-weight:bold; font-size:1.15em;">
        {act} ({com})
    </span>
    """, unsafe_allow_html=True)

    raw = st.text_input("CUIL/CUIT *", max_chars=11)
    cuil = ''.join(filter(str.isdigit, raw))[:11]

    if st.button("VALIDAR Y CONTINUAR", type="primary"):
        if not validar_cuil(cuil):
            st.error("El CUIL debe tener 11 dígitos.")
            st.stop()
        agente = supabase.table("agentes").select("*").eq("cuil", cuil).execute()
        if not agente.data:
            st.error("❌ No se encontró ese agente.")
            st.stop()

        # Chequear si ya existe inscripción
        existe = supabase.table("cursos_inscripciones") \
            .select("id").eq("cuil", cuil).eq("id_comision_sai", com).limit(1).execute()
        if existe.data:
            st.warning("⚠️ Ya estás inscripto en esta comisión.")
            st.stop()

        datos = agente.data[0]

        # Formulario
        st.markdown("### 3. Confirmá o completá tus datos")
        col1, col2 = st.columns(2)
        with col1:
            apellido = st.text_input("Apellido", value=datos.get("apellido", ""))
        with col2:
            nombre = st.text_input("Nombre", value=datos.get("nombre", ""))

        col1, col2 = st.columns(2)
        with col1:
            correo = st.text_input("Correo", value=datos.get("email", ""))
        with col2:
            tramo = st.text_input("Tramo", value=datos.get("tramo", ""))

        if st.button("CONFIRMAR INSCRIPCIÓN", type="primary"):
            nueva = {
                "cuil": cuil,
                "apellido": apellido,
                "nombre": nombre,
                "correo": correo,
                "tramo": tramo,
                "id_comision_sai": com,
                "nombre_actividad": act,
                "fecha_desde": datetime.strptime(f_ini, "%d/%m/%Y").strftime("%Y-%m-%d"),
                "fecha_hasta": datetime.strptime(f_fin, "%d/%m/%Y").strftime("%Y-%m-%d"),
            }
            res = supabase.table("cursos_inscripciones").insert(nueva).execute()
            if res.data:
                st.success("✅ Inscripción registrada correctamente")
            else:
                st.error("❌ Error al registrar la inscripción")
