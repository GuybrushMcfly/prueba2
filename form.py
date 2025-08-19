import streamlit as st
import pandas as pd
from datetime import datetime, date
from st_aggrid import AgGrid, GridOptionsBuilder
from supabase import create_client, Client
from collections import defaultdict
from io import BytesIO
from fpdf import FPDF
import os

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
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
        except:
            return f
    return ""

@st.cache_data(ttl=86400)
def obtener_comisiones_abiertas():
    resp = supabase.table("vista_comisiones_abiertas").select("*").execute()
    return resp.data if resp.data else []

# ========== CARGA Y AGRUPAMIENTO ==========
comisiones_raw = obtener_comisiones_abiertas()
actividades_unicas = {}
comisiones = defaultdict(list)
for c in comisiones_raw:
    act_id = c["id_actividad"]
    act_nombre = c["nombre_actividad"]
    actividades_unicas[act_id] = act_nombre
    comisiones[act_id].append(c)

# ========== UI ==========
st.set_page_config(layout="wide")
st.title("FORMULARIO DE INSCRIPCIÓN A CAPACITACIONES")

# FILTROS
organismos = sorted({c["organismo"] for c in comisiones_raw if c["organismo"]})
modalidades = sorted({c["modalidad"] for c in comisiones_raw if c["modalidad"]})
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

col1, col2 = st.columns(2)
organismo_sel = col1.selectbox("Organismo", organismos)
modalidad_sel = col2.selectbox("Modalidad", modalidades)

# ARMADO DE TABLA
filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones[id_act]:
        if (organismo_sel == "Todos" or c["organismo"] == organismo_sel) and \
           (modalidad_sel == "Todos" or c["modalidad"] == modalidad_sel):
            filas.append({
                "Actividad (Comisión)": f"{nombre_act} ({c['id_comision_sai']})",
                "Actividad": nombre_act,
                "Comisión": c["id_comision_sai"],
                "Fecha inicio": format_fecha(c["fecha_desde"]),
                "Fecha fin": format_fecha(c["fecha_hasta"]),
                "Créditos": c.get("creditos", "")
            })

df_comisiones = pd.DataFrame(filas)

# CONFIGURAR AGGRID
if not df_comisiones.empty:
    gb = GridOptionsBuilder.from_dataframe(df_comisiones)
    gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True)
    gb.configure_selection("single", use_checkbox=True)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    gb.configure_column("Actividad", hide=True)
    gb.configure_column("Comisión", hide=True)
    grid_options = gb.build()

    st.markdown("#### 1. Seleccioná una comisión:")
    response = AgGrid(df_comisiones, gridOptions=grid_options, theme="balham", height=300)
    selected = response["selected_rows"]
else:
    st.warning("⚠️ No hay comisiones disponibles con esos filtros.")
    selected = []

# ========== SI HAY SELECCIÓN ==========
if selected:
    fila = selected[0]
    actividad = fila["Actividad"]
    comision = fila["Comisión"]
    fecha_ini = fila["Fecha inicio"]
    fecha_fin = fila["Fecha fin"]

    st.markdown(f"#### 2. Ingresá tu CUIL para inscribirte en:")
    st.markdown(f"**{actividad}**  \n_Comisión {comision}_")

    raw = st.text_input("CUIL/CUIT *")
    cuil = ''.join(filter(str.isdigit, raw))[:11]

    if st.button("Validar CUIL"):
        if not validar_cuil(cuil):
            st.error("CUIL inválido. Debe tener 11 dígitos.")
            st.stop()

        agente = supabase.table("agentes").select("*").eq("cuil", cuil).execute()
        if not agente.data:
            st.error("No se encontró ese agente.")
            st.stop()

        ya_inscripto = supabase.table("cursos_inscripciones") \
            .select("id") \
            .eq("cuil", cuil).eq("id_comision_sai", comision).limit(1).execute()
        if ya_inscripto.data:
            st.warning("Ya estás inscripto en esta comisión.")
            st.stop()

        datos = agente.data[0]
        st.success("CUIL válido. Completá tus datos para confirmar inscripción.")

        col1, col2 = st.columns(2)
        apellido = col1.text_input("Apellido", value=datos.get("apellido", ""))
        nombre = col2.text_input("Nombre", value=datos.get("nombre", ""))
        correo = st.text_input("Correo electrónico", value=datos.get("email", ""))
        tramo = st.text_input("Tramo", value=datos.get("tramo", ""))

        if st.button("Confirmar inscripción"):
            nueva = {
                "cuil": cuil,
                "apellido": apellido,
                "nombre": nombre,
                "correo": correo,
                "tramo": tramo,
                "id_comision_sai": comision,
                "nombre_actividad": actividad,
                "fecha_desde": datetime.strptime(fecha_ini, "%d/%m/%Y").strftime("%Y-%m-%d"),
                "fecha_hasta": datetime.strptime(fecha_fin, "%d/%m/%Y").strftime("%Y-%m-%d"),
            }
            res = supabase.table("cursos_inscripciones").insert(nueva).execute()
            if res.data:
                st.success("✅ Inscripción registrada correctamente")

                # Constancia PDF
                def generar_constancia_pdf(nombre, actividad, comision, fecha_inicio, fecha_fin):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.set_text_color(19, 106, 193)
                    pdf.cell(0, 10, "Constancia de Preinscripción", ln=True, align="C")
                    pdf.set_font("Helvetica", "", 12)
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(10)
                    pdf.multi_cell(0, 10,
                        f"{nombre}, te preinscribiste exitosamente en:\n\n"
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
