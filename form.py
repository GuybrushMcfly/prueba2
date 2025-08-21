import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from supabase import create_client, Client
from collections import defaultdict
import os
import streamlit.components.v1 as components

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ No se encontraron las credenciales de Supabase en las variables de entorno.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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


# ========== TÍTULO GENERAL ==========
st.markdown("""
    <h1 style="color: #136ac1; text-align: center; font-size: 28px; margin-bottom: 0px;">
        PREINSCRIPCIÓN EN ACTIVIDADES DE CAPACITACIÓN
    </h1>
    <h4 style="text-align: center; font-size: 16px; margin-top: 5px; margin-bottom: 40px;">
        En solo 4 simples pasos:
    </h4>
""", unsafe_allow_html=True)



# ========== FUNCIIONES ==========


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

def verificar_formulario_cuil(supabase: Client, cuil: str) -> bool:
    try:
        response = supabase.rpc("verificar_formulario_cuil", {"cuil_input": cuil}).execute()
        return response.data[0].get("existe", False)
    except Exception as e:
        st.error("Error al verificar el CUIL en la base de datos.")
        return False

def verificar_formulario_historial(supabase: Client, cuil: str, id_actividad: str) -> bool:
    try:
        response = supabase.rpc("verificar_formulario_historial", {
            "cuil_input": cuil,
            "id_actividad_input": id_actividad
        }).execute()

        if isinstance(response.data, list) and response.data:
            return response.data[0].get("existe", False)
        return False
   # except Exception as e:
       # st.error("Error al verificar el historial del agente.")
       # return False

def verificar_formulario_comision(supabase: Client, cuil: str, comision_id: str) -> bool:
    try:
        response = supabase.rpc("verificar_formulario_comision", {
            "cuil_input": cuil,
            "comision_id_input": comision_id
        }).execute()

        if isinstance(response.data, list) and response.data:
            return response.data[0].get("existe", False)
        return False
    #except Exception as e:
        #st.error("Error al verificar si ya está inscripto en la comisión.")
        #return False


def obtener_datos_agente(supabase: Client, cuil: str) -> dict:
    try:
        response = supabase.table("agentes") \
            .select("*") \
            .eq("cuil", cuil) \
            .limit(1) \
            .execute()

        if response.data:
            return response.data[0]
        return {}
    except Exception as e:
        st.error(f"Error al obtener datos del agente: {e}")
        return {}



# ========== CARGA DE DATOS DESDE VISTA ==========
#@st.cache_data(ttl=86400)
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id_comision_sai, organismo, id_actividad, nombre_actividad, fecha_desde, fecha_hasta, fecha_cierre, creditos, modalidad_cursada, link_externo, apto_tramo"
    ).execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones()

# ========== CREAR DATAFRAME ==========
df_temp = pd.DataFrame(comisiones_raw)

# Convertir fechas
df_temp["fecha_desde"] = pd.to_datetime(df_temp["fecha_desde"], errors="coerce")
df_temp["fecha_hasta"] = pd.to_datetime(df_temp["fecha_hasta"], errors="coerce")
df_temp["fecha_cierre"] = pd.to_datetime(df_temp["fecha_cierre"], errors="coerce")

# Filtrar registros válidos
required_cols = ["id_comision_sai", "nombre_actividad", "fecha_desde", "fecha_hasta"]
df_temp = df_temp.dropna(subset=required_cols)

# Crear campos nuevos
df_temp["Actividad"] = df_temp["nombre_actividad"]
df_temp["Comisión"] = df_temp["id_comision_sai"]
df_temp["Fecha inicio"] = df_temp["fecha_desde"].dt.strftime("%d/%m/%Y")
df_temp["Fecha fin"] = df_temp["fecha_hasta"].dt.strftime("%d/%m/%Y")
df_temp["Fecha cierre"] = df_temp["fecha_cierre"].dt.strftime("%d/%m/%Y")
df_temp["Actividad dropdown"] = (
    df_temp["nombre_actividad"]
    + " (" + df_temp["Fecha inicio"] + " al " + df_temp["Fecha fin"] + ")"
)
df_temp["Actividad (Comisión)"] = df_temp["Actividad dropdown"]
df_temp["Créditos"] = df_temp["creditos"].fillna(0).astype(int)
def clasificar_duracion(creditos):
    if 1 <= creditos < 10:
        return "BREVE (hasta 10 hs)"
    elif 10 <= creditos < 20:
        return "INTERMEDIA (entre 10 y 20 hs)"
    elif creditos >= 20:
        return "PROLONGADA (más de 20 hs)"
    return "SIN CLASIFICAR"
df_temp["Duración"] = df_temp["Créditos"].apply(clasificar_duracion)
df_temp["Modalidad"] = df_temp["modalidad_cursada"]
df_temp["Apto tramo"] = df_temp["apto_tramo"].fillna("No")
df_temp["Ver más"] = df_temp["link_externo"]  # solo URL


st.markdown("#### 1) Revisá la oferta de actividades disponibles.")



# ========== FILTROS VISUALES ==========
organismos = sorted(df_temp["organismo"].dropna().unique().tolist())
modalidades = sorted(df_temp["Modalidad"].dropna().unique().tolist())
duraciones = sorted(df_temp["Duración"].dropna().unique().tolist())

organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")
duraciones.insert(0, "Todas")

col1, col2, col3 = st.columns(3)
with col1:
    organismo_sel = st.selectbox("Organismo", organismos, index=0)
with col2:
    modalidad_sel = st.selectbox("Modalidad", modalidades, index=0)
with col3:
    duracion_sel = st.selectbox("Duración", duraciones, index=0)


# Aplicar filtros
df_filtrado = df_temp.copy()
if organismo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["organismo"] == organismo_sel]
if modalidad_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Modalidad"] == modalidad_sel]
if duracion_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Duración"] == duracion_sel]


# ========== TABLA HTML ==========
df_comisiones = df_filtrado[[
    "Actividad (Comisión)", "Fecha inicio", "Fecha fin", "Fecha cierre", "Créditos", "Modalidad", "Apto tramo", "Ver más"
]].reset_index(drop=True)

def create_html_table(df):
    table_id = f"coursesTable_{hash(str(df.values.tobytes())) % 10000}"

    if df.empty:
        st.warning("No se encontraron cursos con los filtros seleccionados. Probá cambiar los filtros para ver otras actividades disponibles.")
        return ""

    html = f"""
    <style>
        .courses-table {{
            width: 90%;
            margin: 0 auto;
            border-collapse: collapse;
            font-size: 14px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
            background-color: white;
        }}
        .courses-table thead tr {{
            background-color: #136ac1;
            color: #ffffff;
            text-align: left;
            font-weight: bold;
        }}
        .courses-table th, .courses-table td {{
            padding: 14px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .courses-table tbody tr {{
            background-color: #ffffff;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        .courses-table tbody tr:hover {{
            background-color: #e3f2fd;
            transform: translateY(-2px);
            box-shadow: 0 2px 8px rgba(19, 106, 193, 0.2);
        }}
        .courses-table tbody tr.selected {{
            background-color: #bbdefb !important;
            border-left: 4px solid #136ac1;
        }}
        .courses-table .fecha-col,
        .courses-table .creditos-col,
        .courses-table .acceso-col {{
            text-align: center;
        }}
        .courses-table a {{
            color: #136ac1;
            text-decoration: none;
            font-weight: bold;
            padding: 6px 12px;
            border: 2px solid #136ac1;
            border-radius: 5px;
            transition: all 0.3s ease;
            display: inline-block;
        }}
        .courses-table a:hover {{
            background-color: #136ac1;
            color: white;
            transform: scale(1.05);
        }}
        .no-link {{
            color: #bdc3c7;
            font-style: italic;
        }}
    </style>

    <div style="overflow-x: auto; margin-bottom: 0;">
        <table class="courses-table" id="{table_id}">
            <thead>
                <tr>
                    <th>Actividad (Comisión)</th>
                    <th>F. Inicio</th>
                    <th>F. Fin</th>
                    <th>Cierre Inscrip.</th>
                    <th>Créditos</th>
                    <th>Modalidad</th>
                    <th>Apto Tramo</th>
                    <th>Acceso</th>
                </tr>
            </thead>
            <tbody>
    """

    for _, row in df.iterrows():
        onclick_code = f"selectActivity('{row['Actividad (Comisión)']}', this)"
        html += f'<tr onclick="{onclick_code}">'
        html += f'<td>{row["Actividad (Comisión)"]}</td>'
        html += f'<td class="fecha-col">{row["Fecha inicio"]}</td>'
        html += f'<td class="fecha-col">{row["Fecha fin"]}</td>'
        html += f'<td class="fecha-col">{row["Fecha cierre"]}</td>'
        html += f'<td class="creditos-col">{row["Créditos"]}</td>'
        html += f'<td>{row["Modalidad"]}</td>'
        html += f'<td>{row["Apto tramo"]}</td>'
        if pd.notna(row["Ver más"]) and row["Ver más"]:
            html += f'<td class="acceso-col"><a href="{row["Ver más"]}" target="_blank" onclick="event.stopPropagation()">🌐 Acceder</a></td>'
        else:
            html += '<td class="acceso-col"><span class="no-link">Sin enlace</span></td>'
        html += '</tr>'

    html += """
            </tbody>
        </table>
    </div>

    <script>
        let selectedRow = null;
        function selectActivity(activityName, row) {
            if (selectedRow) selectedRow.classList.remove('selected');
            selectedRow = row;
            row.classList.add('selected');
            sessionStorage.setItem('selected_activity', activityName);
            window.parent.postMessage({
                type: 'setQueryParams',
                data: { "selected_activity": activityName }
            }, '*');
        }
    </script>
    """
    return html

# Renderizado de la tabla
#st.markdown(create_html_table(df_comisiones), unsafe_allow_html=True)
#components.html(create_html_table(df_comisiones), height=600, scrolling=True)


# ========== RENDER CON FUNCIONALIDADES ADICIONALES ==========
html_code = create_html_table(df_comisiones)

# Agregamos scripts de DataTables
html_code += """
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>

<script>
    $(document).ready(function() {
        const table = $("table").first();
        table.DataTable({
            pageLength: 10,
            dom: '<"top"f<"length-menu"l>>rt<"bottom"ip><"clear">',
            language: {
                search: "",
                searchPlaceholder: "🔍 Buscar...",
                lengthMenu: "Mostrar _MENU_ registros por página",
                zeroRecords: "No se encontraron resultados",
                info: "Mostrando página _PAGE_ de _PAGES_",
                infoEmpty: "No hay registros disponibles",
                infoFiltered: "(filtrado de _MAX_ registros totales)",
                paginate: {
                    previous: "Anterior",
                    next: "Siguiente"
                }
            }
        });

        // Reordenar elementos
        $(".dataTables_filter").css({
            "float": "left",
            "margin-bottom": "10px"
        });
        $(".dataTables_filter input").css({
            "width": "300px"
        });
        $(".dataTables_length").css({
            "float": "right"
        });
    });
</script>
"""


# ================== Mostrar tabla con búsqueda + paginación ==================
st.markdown("""
<div style="margin-bottom: 0px;">
""", unsafe_allow_html=True)

components.html(html_code, height=600, scrolling=True)


# Reducir el espacio entre la tabla y el título del paso 2
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)





# Formato: ACTIVIDAD (dd/mm/yyyy al dd/mm/yyyy)
df_temp["Actividad dropdown"] = (
    df_temp["nombre_actividad"]
    + " (" + df_temp["Fecha inicio"] + " al " + df_temp["Fecha fin"] + ")"
)

# Usar el mismo campo para la tabla
df_temp["Actividad (Comisión)"] = df_temp["Actividad dropdown"]


# ================= PASO 2: Selección de actividad =================
st.markdown("#### 2) Seleccioná la actividad en la cual querés preinscribirte.")
dropdown_list = ["-Seleccioná una actividad para preinscribirte-"] + df_temp["Actividad dropdown"].tolist()
actividad_seleccionada = st.selectbox("Actividad disponible", dropdown_list)

# Detectar cambio en selección (guardamos la última selección previa)
if "actividad_anterior" not in st.session_state:
    st.session_state["actividad_anterior"] = ""

# Si se seleccionó una nueva actividad distinta a la anterior
if actividad_seleccionada != st.session_state["actividad_anterior"]:
    st.session_state["actividad_anterior"] = actividad_seleccionada
    st.session_state["cuil_valido"] = False
    st.session_state["validado"] = False
    st.session_state["cuil"] = ""
    st.session_state["datos_agenteform"] = {}




if actividad_seleccionada != "-Seleccioná una actividad para preinscribirte-":
    fila = df_temp[df_temp["Actividad dropdown"] == actividad_seleccionada].iloc[0]

    # Guardar info en session_state
    st.session_state["actividad_nombre"] = fila["Actividad"]
    st.session_state["comision_nombre"] = fila["Comisión"]
    st.session_state["fecha_inicio"] = fila["Fecha inicio"]
    st.session_state["fecha_fin"] = fila["Fecha fin"]

    # Mostrar detalles de la comisión
    st.markdown(f"""
        <div style="background-color: #f0f8ff; padding: 15px; border-left: 5px solid #136ac1; border-radius: 5px; margin-top: 10px;">
            <strong>📘 Actividad:</strong> {fila["Actividad"]}<br>
            <strong>🆔 Comisión:</strong> {fila["Comisión"]}<br>
            <strong>📅 Fechas:</strong> {fila["Fecha inicio"]} al {fila["Fecha fin"]}<br>
            <strong>📅 Cierre Inscripción:</strong> {fila["Fecha cierre"]}<br>
            <strong>⭐ Créditos:</strong> {fila["Créditos"]}<br>
            <strong>🎓 Modalidad:</strong> {fila["Modalidad"]}<br>
            <strong>🎯 Apto tramo:</strong> {fila["Apto tramo"]}
        </div>
    """, unsafe_allow_html=True)

    # ================= PASO 3: Validación de CUIL =================
    st.markdown("#### 3) Ingresá tu número de CUIL y validalo con el botón.")
    cuil_input = st.text_input("CUIL (11 dígitos)", max_chars=11)

    if st.button("Validar CUIL"):
        if not validar_cuil(cuil_input):
            st.session_state["cuil_valido"] = False
            st.session_state["validado"] = True
            st.session_state["motivo_bloqueo"] = "cuil_invalido"
            st.error("CUIL/CUIT inválido. Verificá que tenga 11 dígitos y sea correcto.")
        else:
            existe = verificar_formulario_cuil(supabase, cuil_input)
            if not existe:
                st.session_state["cuil_valido"] = False
                st.session_state["validado"] = True
                st.session_state["motivo_bloqueo"] = "no_encontrado"
                st.error("⚠️ El CUIL/CUIT no corresponde a un agente activo.")
            else:
                actividad_id = fila["id_actividad"]
        
                ya_aprobo = verificar_formulario_historial(supabase, cuil_input, actividad_id)
                if ya_aprobo:
                    st.session_state["cuil_valido"] = False
                    st.session_state["validado"] = True
                    st.session_state["motivo_bloqueo"] = "ya_aprobo"
                    st.warning("⚠️ Ya realizaste esta actividad y fue APROBADA.")
                else:
                    comision_id = fila["Comisión"]
                    ya_inscripto = verificar_formulario_comision(supabase, cuil_input, comision_id)
                    if ya_inscripto:
                        st.session_state["cuil_valido"] = False
                        st.session_state["validado"] = True
                        st.session_state["motivo_bloqueo"] = "ya_inscripto"
                        st.warning("⚠️ Ya estás inscripto en esta comisión. No hace falta que vuelvas a inscribirte.")
                    else:
                        st.session_state["cuil"] = cuil_input
                        st.session_state["cuil_valido"] = True
                        st.session_state["validado"] = True
                        st.session_state["motivo_bloqueo"] = ""
                        st.success("✅ CUIL/CUILT válido. Podés continuar con la preinscripción.")

# ================= PASO 4: Título SOLO si corresponde mostrar el formulario =================
if (
    st.session_state.get("validado", False)
    and st.session_state.get("cuil_valido", False)
    and not st.session_state.get("inscripcion_exitosa", False)
):
    st.markdown("#### 4) Completá los datos requeridos y finalizá con el botón de preinscripción.")

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

elif st.session_state.get("validado", False):
    if not st.session_state.get("cuil_valido", True):
        motivo = st.session_state.get("motivo_bloqueo", "")
    #    if motivo == "ya_aprobo":
    #        st.warning("⚠️ Ya realizaste esta actividad y fue APROBADA. No podés volver a inscribirte.")
    #    elif motivo == "ya_inscripto":
    #        st.warning("⚠️ Ya estás inscripto en esta comisión. No hace falta que vuelvas a inscribirte.")
        if motivo == "no_encontrado":
            st.error("❌ No se encontró a la persona en la base de datos. Revisá tu CUIL/CUIT e intentá nuevamente. Si el problema persiste, comunicate a capacitacion@indec.gob.ar.")
        elif motivo == "cuil_invalido":
            st.error("❌ CUIL/CUIT inválido. Verificá que tenga 11 dígitos y sea correcto.")
        else:
            st.info("ℹ️ No podés continuar con la inscripción.")



#else:
#    st.info("Seleccioná una comisión y validá tu CUIL para continuar.")

st.markdown("</div>", unsafe_allow_html=True)
