import streamlit as st
import pandas as pd
from datetime import date, datetime  # ← Una sola línea para ambos
from st_aggrid import AgGrid, GridOptionsBuilder
from supabase import create_client, Client
from collections import defaultdict
import time
import io
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
        max-width: 80vw !important;
        padding-left: 2vw;
        padding-right: 2vw;
    }
    </style>
""", unsafe_allow_html=True)

# ========== DATOS DESDE SUPABASE ==========
@st.cache_data(ttl=86400)  # 1 día = 86400 segundos
def obtener_comisiones():
    resp = supabase.table("comisiones").select(
        "id_comision, organismo, id_actividad, nombre_actividad, fecha_inicio, fecha_fin, creditos, modalidad"
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


# --- 1. Filtros únicos ---
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

# --- 2. Filtrado y armado de filas ---
filas = []
for id_act, nombre_act in actividades_unicas.items():
    coms = comisiones.get(id_act, [])
    if coms:
        for c in coms:
            if (organismo_sel == "Todos" or c["organismo"] == organismo_sel) and \
               (modalidad_sel == "Todos" or c["modalidad"] == modalidad_sel):
                filas.append({
                    "Actividad (Comisión)": f"{nombre_act} ({c['id']})",  # visual
                    "Actividad": nombre_act,        # para session_state
                    "Comisión": c["id"],            # para session_state
                    "Fecha inicio": format_fecha(c["fecha_inicio"]),
                    "Fecha fin": format_fecha(c["fecha_fin"]),
                    "Créditos": c["creditos"],
                })
    else:
        filas.append({
            "Actividad (Comisión)": f"{nombre_act} (Sin comisiones)",  # visual
            "Actividad": nombre_act,
            "Comisión": "Sin comisiones",
            "Fecha inicio": "",
            "Fecha fin": "",
            "Créditos": "",
        })

df_comisiones = pd.DataFrame(filas)

# ========== AGGRID CONFIGURACIÓN ==========
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=False, filter=False, resizable=False)
#gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True, filter=False, resizable=False)

gb.configure_selection(selection_mode="single", use_checkbox=True)


# Configurar paginación
gb.configure_pagination(
    paginationAutoPageSize=False,
    paginationPageSize=15
)

# Mostrar solo "Actividad (Comisión)"
gb.configure_column("Actividad (Comisión)", flex=50, wrapText=True, autoHeight=True,
                    tooltipField="Actividad (Comisión)", filter=False, resizable=False,
                    minWidth=600, maxWidth=600)

# Ocultar columnas internas necesarias para lógica
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)

# Otras columnas visibles
gb.configure_column("Fecha inicio", flex=15, filter=False, resizable=False, autoHeight=True)
gb.configure_column("Fecha fin", flex=15, filter=False, resizable=False, autoHeight=True)
gb.configure_column("Créditos", flex=13, filter=False, resizable=False, autoHeight=True)


# Configuraciones adicionales para controlar el comportamiento
gb.configure_grid_options(
    suppressSizeToFit=False,
    suppressColumnVirtualisation=False,
    domLayout='normal',
    localeText={
        # Paginación
        'page': 'Página',
        'more': 'Más',
        'to': 'a',
        'of': 'de',
        'next': 'Siguiente',
        'last': 'Último',
        'first': 'Primero',
        'previous': 'Anterior',
        'loadingOoo': 'Cargando...',
        # Selector de filas por página
        'pageSizeSelectorLabel': 'Filas por página:',
        # Otros textos útiles
        'noRowsToShow': 'No hay datos para mostrar',
        'selectAll': 'Seleccionar todo',
        'selectAllFiltered': 'Seleccionar todo (filtrado)',
        'searchOoo': 'Buscar...',
        'blanks': 'En blanco',
        'filterOoo': 'Filtrar...',
        'applyFilter': 'Aplicar filtro',
        'equals': 'Igual a',
        'notEqual': 'No igual a',
        'lessThan': 'Menor que',
        'greaterThan': 'Mayor que',
        'contains': 'Contiene',
        'notContains': 'No contiene',
        'startsWith': 'Empieza con',
        'endsWith': 'Termina con'
    }
)

custom_css = {
    ".ag-header": {"background-color": "#136ac1 !important", "color": "white !important", "font-weight": "bold !important"},
    ".ag-row": {"font-size": "14px !important"},
    ".ag-row:nth-child(even)": {"background-color": "#f5f5f5 !important"},
    ".ag-cell": {
        "white-space": "normal !important",
        "line-height": "1.2 !important",
        "vertical-align": "middle !important",
        "display": "flex !important",
        "align-items": "center !important",
        "justify-content": "flex-start !important"
    },


}

grid_options = gb.build()

response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=500,
    allow_unsafe_jscode=True,
    theme="balham",
    custom_css=custom_css,
    use_container_width=False,
    width=900  # Asegúrate de que el ancho total esté fijo
)

selected = response["selected_rows"]
if isinstance(selected, pd.DataFrame):
    selected = selected.to_dict("records")

# =======================
# CONTROLAR REINICIO FLAG
# =======================
comision_id = None
if selected and selected[0].get("Comisión") != "Sin comisiones":
    fila = selected[0]
    st.session_state["actividad_nombre"] = fila.get("Actividad", "")
    st.session_state["comision_nombre"] = fila.get("Comisión", "")
    st.session_state["fecha_inicio"] = fila.get("Fecha inicio", "")
    st.session_state["fecha_fin"] = fila.get("Fecha fin", "")

    actividad_nombre = st.session_state["actividad_nombre"]
    comision_nombre = st.session_state["comision_nombre"]
    fecha_inicio = st.session_state["fecha_inicio"]
    fecha_fin = st.session_state["fecha_fin"]

    comision_id = f"{actividad_nombre}|{comision_nombre}|{fecha_inicio}|{fecha_fin}"
    # Reiniciar flags si cambiás de comisión
    if st.session_state.get("last_comision_id") != comision_id:
        st.session_state["validado"] = False
        st.session_state["cuil_valido"] = False
        st.session_state["inscripcion_exitosa"] = False
        st.session_state["last_comision_id"] = comision_id
        for k in ["cuil", "nombres", "apellidos", "nivel", "grado", "agrupamiento", "tramo"]:
            st.session_state.pop(k, None)

    st.markdown(
        f"""
        <h4>2. Validá tu CUIL para inscribirte en</h4>
        <span style="color:#b72877;font-weight:bold; font-size:1.15em;">
            {actividad_nombre} ({comision_nombre})
        </span>
        """,
        unsafe_allow_html=True
    )

    col_cuil, _ = st.columns([1, 1])
    with col_cuil:
        raw = st.text_input("CUIL/CUIT *", value=st.session_state.get("cuil", ""), max_chars=11)
        cuil = ''.join(filter(str.isdigit, raw))[:11]

    # Validación de CUIL y consulta a agentesform
    if st.button("VALIDAR Y CONTINUAR", type="primary"):
        if not validar_cuil(cuil):
            st.error("El CUIL/CUIT debe tener 11 dígitos válidos.")
            st.session_state["validado"] = False
            st.session_state["cuil_valido"] = False
        else:
            resp = supabase.table("agentesform").select("*").eq("cuil_cuit", cuil).execute()
            if resp.data and len(resp.data) == 0:
                st.session_state["validado"] = False
                st.session_state["cuil_valido"] = False
                st.error(
                    "❌ No se encontró ese usuario en la base de datos. "
                    "Verificá los datos ingresados o comunicate con la Dirección de Capacitación."
                )
            else:
                comision = st.session_state.get("comision_nombre", "")
                inscrip_existente = supabase.table("pruebainscripciones") \
                    .select("id") \
                    .eq("cuil_cuit", cuil) \
                    .eq("comision", comision) \
                    .limit(1) \
                    .execute()
    
                if inscrip_existente.data and len(inscrip_existente.data) > 0:
                    st.session_state["validado"] = False
                    st.session_state["cuil_valido"] = False
                    st.warning("⚠️ Ya realizaste la preinscripción en esa comisión. No es necesario volver a inscribirse.")
                else:
                    st.session_state["validado"] = True
                    st.session_state["cuil_valido"] = True
                    st.session_state["cuil"] = cuil
                    st.session_state["datos_agenteform"] = resp.data[0]
                    st.success("¡Datos encontrados! Revisá y completá tus datos si es necesario.")
    
    # Atención: estos bloques NO deben estar indentados dentro del if anterior,
    # van alineados al if st.button(...) (fuera del else y fuera del botón):
    
    elif selected and selected[0].get("Comisión") == "Sin comisiones":
        st.warning("No hay comisiones disponibles para esta actividad.")
    else:
        st.info("Seleccioná una comisión para continuar.")


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
