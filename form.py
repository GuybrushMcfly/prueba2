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
        max-width: 90vw !important;
        padding-left: 2vw;
        padding-right: 2vw;
    }

    .paso-container {
        margin-top: -20px;
        margin-bottom: 5px;
    }

    .tabla-container {
        margin-top: -50px;
        margin-bottom: 20px;
    }

    .element-container:has(.stSelectbox) {
        margin-bottom: 0rem !important;
    }

    .dataTables_wrapper + div {
        margin-top: -80px !important;
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

@st.dialog("✅ ¡Preinscripción exitosa!", width="small", dismissible=False)
def dialogo_exito():
    actividad = st.session_state.get("nombre_actividad_exito", "-")
    st.markdown("### ✅ ¡Preinscripción exitosa!")
    st.markdown("Te preinscribiste correctamente en la actividad:")
    st.markdown(f"📘 **{actividad}**")

    if st.button("Cerrar", key="cerrar_dialogo_exito"):
        # Limpiar completamente el session_state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Forzar recarga completa
        st.query_params.clear()
        st.rerun()

# ========== FUNCIONES ==========
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
    except Exception as e:
        return False

def verificar_formulario_comision(supabase: Client, cuil: str, comision_id: str) -> bool:
    try:
        response = supabase.rpc("verificar_formulario_comision", {
            "cuil_input": cuil,
            "comision_id_input": comision_id
        }).execute()

        if isinstance(response.data, list) and response.data:
            return response.data[0].get("existe", False)
        return False
    except Exception as e:
        return False

def obtener_datos_para_formulario(supabase: Client, cuil: str) -> dict:
    try:
        response = supabase.rpc("obtener_datos_para_formulario", {
            "cuil_input": cuil
        }).execute()

        if response.data and isinstance(response.data, list):
            return response.data[0]  # Devuelve un dict con todos los campos
        else:
            return {}
    except Exception as e:
        st.error(f"Error al obtener los datos del formulario: {e}")
        return {}

# ========== CARGA DE DATOS DESDE VISTA ==========
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id, id_comision_sai, organismo, id_actividad, nombre_actividad, fecha_desde, fecha_hasta, fecha_cierre, creditos, modalidad_cursada, link_externo, apto_tramo"
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

# ========== PASO 1: FILTROS ==========
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)
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

    st.markdown('</div>', unsafe_allow_html=True)

# ========== TABLA CON ALTURA FIJA ==========
with st.container():
    st.markdown('<div class="tabla-container">', unsafe_allow_html=True)
    
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
                font-size: 12px;
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
                padding: 10px 8px;
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
                box-shadow: 0 4px 12px rgba(19, 106, 193, 0.3);
                z-index: 1;
                position: relative;
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
                padding: 4px 8px;
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
                        <th>Inicio</th>
                        <th>Fin</th>
                        <th>Cierre</th>
                        <th>Créditos</th>
                        <th>Modalidad</th>
                        <th>Tramo</th>
                        <th>INAP</th>
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
                #html += f'<td class="acceso-col"><a href="{row["Ver más"]}" target="_blank" onclick="event.stopPropagation()">🌐 Acceder</a></td>'
                html += f'<td class="acceso-col"><a href="{row["Ver más"]}" target="_blank" onclick="event.stopPropagation()">Acceder</a></td>'
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
                    type: 'streamlit:setQueryParams',
                    queryParams: { "selected_activity": activityName }
                }, '*');
            }
        </script>
        """
        return html

    # Agregamos scripts de DataTables
    html_code = create_html_table(df_comisiones)
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

    # Calcular altura dinámica
    num_filas = len(df_comisiones)
    altura_dinamica = min(600, 100 + (num_filas * 50))

    components.html(html_code, height=altura_dinamica, scrolling=True)

    st.markdown('</div>', unsafe_allow_html=True)

# Formato: ACTIVIDAD (dd/mm/yyyy al dd/mm/yyyy)
df_temp["Actividad dropdown"] = (
    df_temp["nombre_actividad"]
    + " (" + df_temp["Fecha inicio"] + " al " + df_temp["Fecha fin"] + ")"
)

# Usar el mismo campo para la tabla
df_temp["Actividad (Comisión)"] = df_temp["Actividad dropdown"]

# ================= PASO 2: Selección de actividad =================
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)
    st.markdown("#### 2) Seleccioná la actividad en la cual querés preinscribirte.")
    
    # Manejar parámetros de consulta para selección inicial
    selected_from_query = st.query_params.get("selected_activity", None)
    initial_index = 0
    
    dropdown_list = ["-Seleccioná una actividad para preinscribirte-"] + df_temp["Actividad dropdown"].tolist()
    
    if selected_from_query:
        try:
            initial_index = dropdown_list.index(selected_from_query)
        except ValueError:
            initial_index = 0
    
    actividad_seleccionada = st.selectbox("Actividad disponible", dropdown_list, index=initial_index)

    # Detectar cambio en selección
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
        st.session_state["comision_id"] = fila["id"]

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
    st.markdown('</div>', unsafe_allow_html=True)

# ================= PASO 3: Validación de CUIL =================
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)
    if actividad_seleccionada != "-Seleccioná una actividad para preinscribirte-":
        st.markdown("#### 3) Ingresá tu número de CUIL y validalo con el botón.")
        cuil_input = st.text_input("CUIL (11 dígitos)", max_chars=11, key="cuil_input")

        if st.button("Validar CUIL", key="validar_cuil_btn"):
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

                            # 🔍 Obtener datos del agente desde función RPC y guardarlos en sesión
                            datos = obtener_datos_para_formulario(supabase, cuil_input)
                            st.session_state["datos_agenteform"] = datos

                            # 🧾 Mostrar datos obtenidos (solo visual)
                            if datos:
                                st.markdown("---")
                                st.markdown("### 🧾 Datos obtenidos del agente")
                                for campo, valor in datos.items():
                                    st.markdown(f"**{campo.replace('_', ' ').capitalize()}:** {valor if valor else '-'}")
                                st.markdown("---")

# ================= PASO 4: Formulario de inscripción =================
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)

    if (
        st.session_state.get("validado", False)
        and st.session_state.get("cuil_valido", False)
        and not st.session_state.get("inscripcion_exitosa", False)
    ):
        datos_agente = st.session_state.get("datos_agenteform", {})
        nombre_agente = f"{datos_agente.get('nombre', '')} {datos_agente.get('apellido', '')}".strip()

        st.markdown(f"### 👤 {nombre_agente}")
        st.markdown("Necesitamos que completes los siguientes campos para continuar con tu preinscripción.")

        # --- CAMPOS: Nivel educativo + Título
        col1, col2 = st.columns(2)

        niveles_educativos = ["-Seleccioná último nivel completo-", "PRIMARIO", "SECUNDARIO", "TERCIARIO", "UNIVERSITARIO", "POSGRADO"]
        valor_nivel = datos_agente.get("nivel_educativo", "")
        indice_nivel = niveles_educativos.index(valor_nivel) if valor_nivel in niveles_educativos else 0

        with col1:
            nivel_educativo = st.selectbox("Nivel educativo", niveles_educativos, index=indice_nivel, key="nivel_educativo")

        with col2:
            titulo_valor = datos_agente.get("titulo", "").upper() if datos_agente.get("titulo") else ""
            titulo = st.text_input("Título", value=titulo_valor, key="titulo").upper()

        # --- TAREAS
        tareas = st.text_area("Tareas desarrolladas", height=100, key="tareas_desarrolladas").lower()

        # --- MAIL ALTERNATIVO
        correo_oficial = datos_agente.get("email", "")
        st.markdown(f"Te vamos a enviar cualquier notificación al correo: **{correo_oficial}**")

        email_alternativo = st.text_input("Correo alternativo (opcional)", key="email_alternativo")
        if email_alternativo and "@" not in email_alternativo:
            st.warning("📧 El correo alternativo no tiene un formato válido.")

        # --- BOTÓN DE ENVÍO
        if st.button("ENVIAR INSCRIPCIÓN", key="enviar_inscripcion"):
            if email_alternativo and "@" not in email_alternativo:
                st.error("⚠️ El correo alternativo no es válido.")
            else:
                # Cálculo de edad
                fecha_nacimiento = datos_agente.get("fecha_nacimiento")
                edad = None
                if fecha_nacimiento:
                    try:
                        fecha_nac = pd.to_datetime(fecha_nacimiento)
                        hoy = pd.Timestamp.today()
                        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
                    except:
                        edad = None
        
                datos_inscripcion = {
                    "comision_id": st.session_state.get("comision_id"),
                    "cuil": st.session_state.get("cuil", ""),
                    "fecha_inscripcion": date.today().isoformat(),
                    "estado_inscripcion": "Nueva",
                    "vacante": False,
                    "nivel_educativo": nivel_educativo if nivel_educativo != "-Seleccioná último nivel completo-" else None,
                    "titulo": titulo,
                    "tareas_desarrolladas": tareas,
                    "email": correo_oficial,
                    "email_alternativo": email_alternativo,
                    "fecha_nacimiento": fecha_nacimiento,
                    "edad_inscripcion": edad,
                    "sexo": datos_agente.get("sexo"),
                    "situacion_revista": datos_agente.get("situacion_revista"),
                    "nivel": datos_agente.get("nivel"),
                    "grado": datos_agente.get("grado"),
                    "agrupamiento": datos_agente.get("agrupamiento"),
                    "tramo": datos_agente.get("tramo"),
                    "id_dependencia_simple": datos_agente.get("id_dependencia_simple"),
                    "id_dependencia_general": datos_agente.get("id_dependencia_general")
                }
        
                # Intentar insertar en Supabase
                result = supabase.table("cursos_inscripciones").insert(datos_inscripcion).execute()
                if result.data:
                    st.session_state["nombre_actividad_exito"] = fila["Actividad"]
                    dialogo_exito()
                else:
                    st.error("❌ Ocurrió un error al guardar la inscripción.")

    st.markdown('</div>', unsafe_allow_html=True)
