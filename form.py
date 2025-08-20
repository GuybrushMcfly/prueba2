import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
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
        "id_comision_sai, organismo, id_actividad, nombre_actividad, fecha_desde, fecha_hasta, creditos, modalidad"
    ).execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones()

actividades_unicas = {}
for c in comisiones_raw:
    if c["id_actividad"] and c["nombre_actividad"]:
        actividades_unicas[c["id_actividad"]] = c["nombre_actividad"]

comisiones = defaultdict(list)
for c in comisiones_raw:
    if c["id_actividad"]:
        comisiones[c["id_actividad"]].append({
            "id_comision_sai": c["id_comision_sai"],
            "nombre": c["nombre_actividad"],
            "fecha_inicio": c["fecha_desde"],
            "fecha_fin": c["fecha_hasta"],
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

st.markdown("#### 1. Seleccioná una comisión en la tabla (clic en la fila):")

filas = []
for id_act, nombre_act in actividades_unicas.items():
    coms = comisiones.get(id_act, [])
    if coms:
        for c in coms:
            if (organismo_sel == "Todos" or c["organismo"] == organismo_sel) and \
               (modalidad_sel == "Todos" or c["modalidad"] == modalidad_sel):
                filas.append({
                    "Actividad (Comisión)": f"{nombre_act} ({c['id_comision_sai']})",
                    "Actividad": nombre_act,
                    "Comisión": c["id_comision_sai"],
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

df_comisiones = pd.DataFrame(filas)

gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_selection(
    selection_mode="single", 
    use_checkbox=False, 
    pre_selected_rows=[],
    suppressRowClickSelection=False,  # IMPORTANTE: Permitir selección por clic
    rowMultiSelectWithClick=False     # IMPORTANTE: No permitir multi-selección con clic
)

# CONFIGURACIÓN CRUCIAL PARA SELECCIÓN POR CLIC - SOLO UNA VEZ
gb.configure_grid_options(
    enableCellTextSelection=True,
    ensureDomOrder=True,
    suppressRowClickSelection=False,  # Asegurar que los clics seleccionen
    onRowClicked="""function(params) {
        // Forzar la selección al hacer clic en cualquier parte de la fila
        params.node.setSelected(true, false);
        // Disparar evento de cambio de selección
        params.api.dispatchEvent({type: 'selectionChanged'});
    }""",
    onSelectionChanged="""function(params) {
        // Este evento asegura que Streamlit detecte el cambio
        console.log('Selection changed');
    }"""
)


gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
gb.configure_column("Actividad (Comisión)", flex=50, wrapText=True, autoHeight=True, tooltipField="Actividad (Comisión)", filter=False, resizable=False, minWidth=600, maxWidth=600)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("Fecha inicio", flex=15, filter=False, resizable=False, autoHeight=True)
gb.configure_column("Fecha fin", flex=15, filter=False, resizable=False, autoHeight=True)
gb.configure_column("Créditos", flex=13, filter=False, resizable=False, autoHeight=True)

custom_css = {
    ".ag-header": {"background-color": "#136ac1 !important", "color": "white !important", "font-weight": "bold !important"},
    ".ag-row": {"font-size": "14px !important", "cursor": "pointer"},  # Cursor pointer para indicar que es clickeable
    ".ag-row:hover": {"background-color": "#e6f3ff !important"},  # Efecto hover visual
    ".ag-row:nth-child(even)": {"background-color": "#f5f5f5 !important"},
    ".ag-row-selected": {"background-color": "#d4edda !important"},  # Color para fila seleccionada
    ".ag-cell": {
        "white-space": "normal !important",
        "line-height": "1.2 !important",
        "vertical-align": "middle !important",
        "display": "flex !important",
        "align-items": "center !important",
        "justify-content": "flex-start !important"
    },
}


# ======================================
# 🧪 1. TABLA SIMULADA
# ======================================
# ===============================
# DATOS DE PRUEBA
# ===============================
df_simulada = pd.DataFrame([
    {
        "Actividad (Comisión)": "Curso de Python (CPY-001)",
        "Actividad": "Curso de Python",
        "Comisión": "CPY-001",
        "Fecha inicio": "01/09/2025",
        "Fecha fin": "15/09/2025",
        "Créditos": 10
    },
    {
        "Actividad (Comisión)": "Curso de SQL (CSQ-002)",
        "Actividad": "Curso de SQL",
        "Comisión": "CSQ-002",
        "Fecha inicio": "10/09/2025",
        "Fecha fin": "20/09/2025",
        "Créditos": 8
    }
])

st.markdown("### 🧪 Tabla de prueba (simulada)")

# ===============================
# CONFIGURACIÓN DE AGGRID
# ===============================
gb = GridOptionsBuilder.from_dataframe(df_simulada)
gb.configure_default_column(wrapText=True, autoHeight=True, resizable=True)

# Checkbox de selección única
gb.configure_selection(selection_mode="single", use_checkbox=True)

# Ocultar columnas internas
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)

# Formato de columnas visibles
gb.configure_column("Actividad (Comisión)", flex=50, minWidth=500, tooltipField="Actividad (Comisión)")
gb.configure_column("Fecha inicio", flex=15)
gb.configure_column("Fecha fin", flex=15)
gb.configure_column("Créditos", flex=10)

# Configurar paginación
gb.configure_pagination(paginationAutoPageSize=True)

# Estilos visuales
custom_css = {
    ".ag-header": {
        "background-color": "#136ac1 !important",
        "color": "white !important",
        "font-weight": "bold !important"
    },
    ".ag-cell": {
        "white-space": "normal !important",
        "line-height": "1.3 !important"
    }
}

# ===============================
# MOSTRAR TABLA
# ===============================
response = AgGrid(
    df_simulada,
    gridOptions=gb.build(),
    theme="balham",
    height=300,
    custom_css=custom_css,
    allow_unsafe_jscode=True,
    key="tabla_simulada"
)

selected = response.get("selected_rows", [])

# ===============================
# BOTÓN PARA MOSTRAR SELECCIÓN
# ===============================
if st.button("📥 Ver selección de tabla simulada"):
    st.write("🔍 Datos crudos seleccionados:", selected)
    if selected and isinstance(selected[0], dict) and selected[0].get("Comisión"):
        fila = selected[0]
        st.success("✅ Fila seleccionada en tabla simulada:")
        st.write(f"**Actividad:** {fila['Actividad']}")
        st.write(f"**Comisión:** {fila['Comisión']}")
        st.write(f"**Fechas:** {fila['Fecha inicio']} → {fila['Fecha fin']}")
        st.write(f"**Créditos:** {fila['Créditos']}")
    else:
        st.warning("⚠️ No seleccionaste ninguna fila en la tabla simulada.")


# === Mostrar tabla con selección ===
response = AgGrid(
    df_comisiones,
    gridOptions=gb.build(),
    height=500,
    allow_unsafe_jscode=True,
    theme="balham",
    custom_css=custom_css,
    use_container_width=True,
    update_mode='SELECTION_CHANGED',
    key='comisiones_grid'
)

selected = response.get("selected_rows", [])

# === Si se seleccionó una fila válida ===
if selected and isinstance(selected[0], dict):
    fila = selected[0]
    actividad = fila.get("Actividad", "")
    comision = fila.get("Comisión", "")
    st.markdown(f"**Actividad seleccionada:** {actividad} ({comision})")
    
    # Guardar en session_state
    st.session_state["actividad_nombre"] = actividad
    st.session_state["comision_nombre"] = comision
    st.session_state["fecha_inicio"] = fila.get("Fecha inicio", "")
    st.session_state["fecha_fin"] = fila.get("Fecha fin", "")

    cuil = st.text_input("Ingresá tu CUIL/CUIT")
    if st.button("Validar CUIL"):
        if validar_cuil(cuil):
            st.session_state["cuil"] = cuil
            st.session_state["cuil_valido"] = True
            st.session_state["validado"] = True
            st.success("CUIL válido")
        else:
            st.session_state["cuil_valido"] = False
            st.error("CUIL inválido. Debe tener 11 dígitos válidos.")
else:
    st.info("Seleccioná una fila haciendo clic para continuar.")




# ========== FORMULARIO SOLO SI EL CUIL ES VÁLIDO Y EXISTE ==========
if (
    st.session_state.get("validado", False)
    and st.session_state.get("cuil_valido", False)
    and not st.session_state.get("inscripcion_exitosa", False)
):
    st.markdown("#### 3. Completá tus datos personales")

    datos_agente = st.session_state.get("datos_agenteform", {})

    niveles_educativos = ["", "PRIMARIO", "SECUNDARIO", "TERCIARIO", "UNIVERSITARIO", "POSGRADO"]
    situaciones_revista = [
        "", "PLANTA PERMANENTE", "PLANTA TRANSITORIA",
        "CONTRATOS DEC. 1109/17", "CONTRATOS DEC. 1421/02 (48)"
    ]
    agrupamientos = ["", "PROF", "GRAL"]
    niveles = ["", "A", "B", "C"]
    tramos = ["", "INICIAL", "INTERMEDIO", "AVANZADO"]
    sexos = ["", "F", "M", "X"]

    if datos_agente.get("fecha_nacimiento"):
        try:
            fecha_nac_valor = pd.to_datetime(datos_agente["fecha_nacimiento"]).date()
        except:
            fecha_nac_valor = date(1980, 1, 1)
    else:
        fecha_nac_valor = date(1980, 1, 1)

    col_ap, col_nom = st.columns(2)
    with col_ap:
        apellido = st.text_input("Apellido *", value=datos_agente.get("apellido", ""), key="apellido")
    with col_nom:
        nombre = st.text_input("Nombre *", value=datos_agente.get("nombre", ""), key="nombre")

    col_fec, col_sex = st.columns(2)
    with col_fec:
        fecha_nacimiento = st.date_input("Fecha de nacimiento *", value=fecha_nac_valor, key="fecha_nacimiento")
    with col_sex:
        sexo = st.selectbox("Sexo", sexos, index=sexos.index(datos_agente.get("sexo", "")) if datos_agente.get("sexo", "") in sexos else 0, key="sexo")

    col_niv_edu, col_tit = st.columns(2)
    with col_niv_edu:
        nivel_educativo = st.selectbox("Nivel educativo", niveles_educativos, index=niveles_educativos.index(datos_agente.get("nivel_educativo", "")) if datos_agente.get("nivel_educativo", "") in niveles_educativos else 0, key="nivel_educativo")
    with col_tit:
        titulo = st.text_input("Título", value=datos_agente.get("titulo", ""), key="titulo")

    col_sit, col_vacia = st.columns(2)
    with col_sit:
        situacion_revista = st.selectbox("Situación de revista", situaciones_revista, index=situaciones_revista.index(datos_agente.get("situacion_revista", "")) if datos_agente.get("situacion_revista", "") in situaciones_revista else 0, key="situacion_revista")

    col_nivel, col_grado = st.columns(2)
    with col_nivel:
        nivel = st.selectbox("Nivel", niveles, index=niveles.index(datos_agente.get("nivel", "")) if datos_agente.get("nivel", "") in niveles else 0, key="nivel")
    with col_grado:
        grado = st.text_input("Grado", value=datos_agente.get("grado", ""), key="grado")

    col_agrup, col_tramo = st.columns(2)
    with col_agrup:
        agrupamiento = st.selectbox("Agrupamiento", agrupamientos, index=agrupamientos.index(datos_agente.get("agrupamiento", "")) if datos_agente.get("agrupamiento", "") in agrupamientos else 0, key="agrupamiento")
    with col_tramo:
        tramo = st.selectbox("Tramo", tramos, index=tramos.index(datos_agente.get("tramo", "")) if datos_agente.get("tramo", "") in tramos else 0, key="tramo")

    dependencia_simple = st.text_input("Dependencia simple", value=datos_agente.get("dependencia_simple", ""), key="dependencia_simple")
    correo = st.text_input("Correo", value=datos_agente.get("correo", ""), key="correo")

    # --- Enviar inscripción ---
    if st.button("ENVIAR INSCRIPCIÓN"):
        apellido_nombre = f"{apellido}, {nombre}"
        datos_inscripcion = {
            "cuil_cuit": st.session_state.get("cuil", ""),
            "apellido": apellido,
            "nombre": nombre,
            "apellido_nombre": apellido_nombre,
            "fecha_nacimiento": fecha_nacimiento.strftime("%Y-%m-%d"),
            "nivel_educativo": nivel_educativo,
            "titulo": titulo,
            "situacion_revista": situacion_revista,
            "agrupamiento": agrupamiento,
            "nivel": nivel,
            "grado": grado,
            "tramo": tramo,
            "dependencia_simple": dependencia_simple,
            "correo": correo,
            "sexo": sexo,
            "actividad": st.session_state.get("actividad_nombre", ""),
            "comision": st.session_state.get("comision_nombre", ""),
            "fecha_inicio": st.session_state.get("fecha_inicio", ""),
            "fecha_fin": st.session_state.get("fecha_fin", "")
        }
        result = supabase.table("pruebainscripciones").insert(datos_inscripcion).execute()
        if result.data:
            st.success("¡Inscripción guardada correctamente en pruebainscripciones!")
            st.balloons()
            st.session_state["inscripcion_exitosa"] = True
        
            # Limpiar selección de comisión
            st.session_state["last_comision_id"] = None
            st.session_state["comision_nombre"] = ""
            st.session_state["actividad_nombre"] = ""
            st.session_state["fecha_inicio"] = ""
            st.session_state["fecha_fin"] = ""

            # --- Generar constancia PDF ---

            def generar_constancia_pdf(nombre, actividad, comision, fecha_inicio, fecha_fin):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
            
                # ===== Estilo del encabezado =====
                pdf.set_font("Helvetica", style='B', size=14)
                pdf.set_text_color(19, 106, 193)  # Azul institucional
                pdf.cell(0, 10, txt="Constancia de preinscripcion", ln=True, align="C")
                pdf.ln(10)
            
                # ===== Restaurar fuente y color normales =====
                pdf.set_font("Helvetica", size=11)
                pdf.set_text_color(0, 0, 0)
            
                # ===== Limpiar caracteres problemáticos =====
                nombre_limpio = ''.join(c for c in str(nombre) if ord(c) < 256)
                actividad_limpia = ''.join(c for c in str(actividad) if ord(c) < 256)
                comision_limpia = ''.join(c for c in str(comision) if ord(c) < 256)
                fecha_inicio_limpia = ''.join(c for c in str(fecha_inicio) if ord(c) < 256)
                fecha_fin_limpia = ''.join(c for c in str(fecha_fin) if ord(c) < 256)
            
                # ===== Contenido =====
                contenido = (
                    f"{nombre_limpio}, te registraste exitosamente en la actividad detallada a continuacion:\n\n"
                    f"Actividad: {actividad_limpia}\n"
                    f"Comision: {comision_limpia}\n"
                    f"Fecha de inicio: {fecha_inicio_limpia}\n"
                    f"Fecha de fin: {fecha_fin_limpia}\n\n"
                    f"IMPORTANTE: Esta inscripcion NO implica asignacion automatica de vacante. "
                    f"Antes del inicio, en caso de ser otorgada, recibiras un correo con la confirmacion.\n\n"
                    f"Fecha de registro: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )
            
                pdf.multi_cell(0, 8, txt=contenido)
                
                return BytesIO(pdf.output(dest='S').encode('latin1'))


            constancia = generar_constancia_pdf(
                nombre=f"{st.session_state.get('nombre', '')} {st.session_state.get('apellido', '')}",
                actividad=st.session_state.get("actividad_nombre", ""),
                comision=st.session_state.get("comision_nombre", ""),
                fecha_inicio=st.session_state.get("fecha_inicio", ""),
                fecha_fin=st.session_state.get("fecha_fin", "")
            )

            st.download_button(
                label="📄 Descargar constancia de inscripción",
                data=constancia,
                file_name="constancia_inscripcion.pdf",
                mime="application/pdf"
            )

            # Esperar un poco para que pueda descargar
            time.sleep(6)
            st.rerun()

        else:
            st.error("Ocurrió un error al guardar la inscripción.")

# --- Tabla de inscripciones solo tras inscribir exitosamente ---
if st.session_state.get("inscripcion_exitosa", False):
    st.markdown("### Últimas inscripciones")
    inscripciones = supabase.table("pruebainscripciones") \
        .select("apellido_nombre, actividad, comision, fecha_inicio, fecha_fin") \
        .eq("cuil_cuit", st.session_state.get("cuil", "")) \
        .order("fecha_inscripcion", desc=True) \
        .limit(10).execute()
    df_insc = pd.DataFrame(inscripciones.data)
    if not df_insc.empty:
        st.table(df_insc)
    else:
        st.info("No se encontraron inscripciones para este usuario.")

elif st.session_state.get("validado", False) and not st.session_state.get("cuil_valido", True):
    st.error("No existe esa persona en la base de datos. No podés continuar.")

#else:
#    st.info("Seleccioná una comisión y validá tu CUIL para continuar.")

st.markdown("</div>", unsafe_allow_html=True)
