import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from supabase import create_client, Client
from collections import defaultdict
import os

import webbrowser

# ========== DATOS DE PRUEBA ==========
data = pd.DataFrame([
    {
        "ID": 1,
        "Actividad": "Curso de Python",
        "URL": "https://python.org",
        "Descripción": "Aprende Python desde cero"
    },
    {
        "ID": 2,
        "Actividad": "Curso de Streamlit",
        "URL": "https://streamlit.io",
        "Descripción": "Crea apps web con Python"
    },
    {
        "ID": 3,
        "Actividad": "Documentación AgGrid",
        "URL": "https://docs.streamlit.io/library/api-reference/data/st.dataframe",
        "Descripción": "Tablas interactivas"
    }
])

st.title("🔗 Links Clickeables en AgGrid - Soluciones que SÍ funcionan")

# ========== SOLUCIÓN 1: SELECCIÓN + BOTONES EXTERNOS ==========
st.header("1️⃣ Solución: Selección + Botones externos")

gb1 = GridOptionsBuilder.from_dataframe(data)
gb1.configure_selection("single", use_checkbox=True)
gb1.configure_pagination()
gb1.configure_default_column(resizable=True, wrapText=True, autoHeight=True)

# Mostrar URL como texto plano
gb1.configure_column("URL", header_name="🌐 Enlace", width=200)

grid_options1 = gb1.build()

response1 = AgGrid(
    data,
    gridOptions=grid_options1,
    theme="alpine",
    height=200,
    use_container_width=True,
    key="grid1"
)

# Botones para filas seleccionadas
if response1["selected_rows"]:
    selected_row = response1["selected_rows"][0]
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"**Seleccionado:** {selected_row['Actividad']}")
    
    with col2:
        if st.button("🔗 Abrir Link", key="btn1"):
            st.markdown(f"[👉 {selected_row['Actividad']}]({selected_row['URL']})")
    
    with col3:
        # JavaScript para abrir en nueva pestaña
        if st.button("🌐 Nueva Pestaña", key="btn2"):
            js_code = f"""
            <script>
                window.open('{selected_row['URL']}', '_blank');
            </script>
            """
            st.components.v1.html(js_code, height=0)

st.divider()

# ========== SOLUCIÓN 2: MÚLTIPLES SELECCIONES ==========
st.header("2️⃣ Solución: Múltiples selecciones")

gb2 = GridOptionsBuilder.from_dataframe(data)
gb2.configure_selection("multiple", use_checkbox=True)
gb2.configure_pagination()
gb2.configure_default_column(resizable=True, wrapText=True, autoHeight=True)

grid_options2 = gb2.build()

response2 = AgGrid(
    data,
    gridOptions=grid_options2,
    theme="balham",
    height=200,
    use_container_width=True,
    key="grid2"
)

# Abrir múltiples links
if response2["selected_rows"]:
    st.write(f"**{len(response2['selected_rows'])} elementos seleccionados:**")
    
    cols = st.columns(min(len(response2["selected_rows"]), 4))
    
    for i, row in enumerate(response2["selected_rows"]):
        with cols[i % len(cols)]:
            if st.button(f"🔗 {row['Actividad']}", key=f"multi_btn_{i}"):
                st.markdown(f"[👉 Abrir {row['Actividad']}]({row['URL']})")

st.divider()

# ========== SOLUCIÓN 3: DOBLE CLICK (CALLBACK) ==========
st.header("3️⃣ Solución: Doble click en fila")

gb3 = GridOptionsBuilder.from_dataframe(data)
gb3.configure_pagination()
gb3.configure_default_column(resizable=True, wrapText=True, autoHeight=True)

# Configurar evento de doble click
gb3.configure_grid_options(onRowDoubleClicked=JsCode("""
    function(event) {
        // Esta función se ejecuta al hacer doble click
        console.log('Doble click en:', event.data);
    }
"""))

grid_options3 = gb3.build()

st.info("💡 **Instrucciones:** Haz doble click en cualquier fila para ver los datos")

response3 = AgGrid(
    data,
    gridOptions=grid_options3,
    allow_unsafe_jscode=True,
    theme="streamlit",
    height=200,
    use_container_width=True,
    key="grid3"
)

# Detectar cambios en la grilla (incluyendo doble clicks)
if hasattr(response3, 'event_data') and response3.event_data:
    if response3.event_data.get('type') == 'rowDoubleClicked':
        clicked_row = response3.event_data['data']
        st.success(f"🎯 **Doble click detectado!**")
        st.markdown(f"**Actividad:** {clicked_row['Actividad']}")
        st.markdown(f"**Link:** [{clicked_row['URL']}]({clicked_row['URL']})")

st.divider()

# ========== SOLUCIÓN 4: TABLA NATIVA DE STREAMLIT ==========
st.header("4️⃣ Alternativa: Tabla nativa con links")

# Crear DataFrame con links en formato Markdown
data_with_links = data.copy()
data_with_links['Link Clickeable'] = data_with_links.apply(
    lambda row: f"[🔗 {row['Actividad']}]({row['URL']})", axis=1
)

# Mostrar con st.dataframe (los links SÍ funcionan aquí)
st.dataframe(
    data_with_links[['Actividad', 'Link Clickeable', 'Descripción']],
    use_container_width=True,
    hide_index=True
)

st.success("✅ En esta tabla los links SÍ son clickeables!")

# ========== SOLUCIÓN 5: SIDEBAR PARA NAVEGACIÓN ==========
st.sidebar.header("🌐 Navegación rápida")
st.sidebar.write("Links de las actividades:")

for _, row in data.iterrows():
    if st.sidebar.button(f"🔗 {row['Actividad']}", key=f"sidebar_{row['ID']}"):
        st.sidebar.markdown(f"[👉 Ir a {row['Actividad']}]({row['URL']})")

# ========== INFORMACIÓN ADICIONAL ==========
with st.expander("ℹ️ ¿Por qué no funcionan los links en AgGrid?"):
    st.write("""
    **Razones técnicas:**
    
    1. **Seguridad:** Streamlit limita la ejecución de JavaScript por seguridad
    2. **Sandbox:** AgGrid corre en un contexto aislado
    3. **HTML estático:** Los elementos HTML se renderizan como texto
    
    **Soluciones recomendadas:**
    
    ✅ **Selección + botones externos** (más control)
    ✅ **Tabla nativa de Streamlit** (links nativos)
    ✅ **Doble click + callbacks** (más interactivo)
    ✅ **Sidebar navigation** (UX limpia)
    """)

st.info("💡 **Recomendación:** Usa la Solución 1 (selección + botones) para máximo control y UX clara.")




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

# ========== CARGA DE DATOS DESDE VISTA ==========
@st.cache_data(ttl=86400)
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id_comision_sai, organismo, id_actividad, nombre_actividad, fecha_desde, fecha_hasta, creditos, modalidad_cursada, link_externo"
    ).execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones()

# ========== CREAR DATAFRAME COMPATIBLE CON LA LÓGICA ANTIGUA ==========
df_temp = pd.DataFrame(comisiones_raw)

required_cols = ["id_comision_sai", "nombre_actividad", "fecha_desde", "fecha_hasta"]
df_temp = df_temp.dropna(subset=required_cols)

df_temp["Actividad"] = df_temp["nombre_actividad"]
df_temp["Comisión"] = df_temp["id_comision_sai"]

df_temp["fecha_desde"] = pd.to_datetime(df_temp["fecha_desde"], errors="coerce")
df_temp["fecha_hasta"] = pd.to_datetime(df_temp["fecha_hasta"], errors="coerce")
df_temp = df_temp.dropna(subset=["fecha_desde", "fecha_hasta"])

df_temp["Fecha inicio"] = df_temp["fecha_desde"].dt.strftime("%d/%m/%Y")
df_temp["Fecha fin"] = df_temp["fecha_hasta"].dt.strftime("%d/%m/%Y")
df_temp["Actividad (Comisión)"] = df_temp["nombre_actividad"] + " (" + df_temp["id_comision_sai"] + ")"
df_temp["Créditos"] = df_temp["creditos"].fillna(0).astype(int)

# ========== CONVERTIR link_externo en HTML ==========

df_temp["Ver más"] = df_temp["link_externo"]  # solo la URL


# ========== APLICAR FILTROS ==========
organismos = sorted(df_temp["organismo"].dropna().unique().tolist())
modalidades = sorted(df_temp["modalidad_cursada"].dropna().unique().tolist())
organismos.insert(0, "Todos")
modalidades.insert(0, "Todos")

st.title("FORMULARIO DE INSCRIPCIÓN DE CURSOS")

col1, col2 = st.columns(2)
with col1:
    organismo_sel = st.selectbox("Organismo", organismos, index=0)
with col2:
    modalidad_sel = st.selectbox("Modalidad", modalidades, index=0)

if organismo_sel != "Todos":
    df_temp = df_temp[df_temp["organismo"] == organismo_sel]
if modalidad_sel != "Todos":
    df_temp = df_temp[df_temp["modalidad_cursada"] == modalidad_sel]

# ========== ARMAR DF FINAL CON COLUMNAS VISIBLES ==========
df_comisiones = df_temp[[
    "Actividad (Comisión)", "Actividad", "Comisión", "Fecha inicio", "Fecha fin", "Créditos", "Ver más"
]]

# 🛠️ RESET INDEX por recomendación de foros
df_comisiones = df_comisiones.reset_index(drop=True)

# ========== CONFIGURACIÓN AGGRID ==========
gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=False, filter=False, resizable=False)
gb.configure_selection(selection_mode="single", use_checkbox=True)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)

gb.configure_column("Actividad (Comisión)", flex=50, tooltipField="Actividad (Comisión)", wrapText=True, autoHeight=True, resizable=False, minWidth=600, maxWidth=600)
gb.configure_column("Actividad", hide=True)
gb.configure_column("Comisión", hide=True)
gb.configure_column("Fecha inicio", flex=15, resizable=False, autoHeight=True)
gb.configure_column("Fecha fin", flex=15, resizable=False, autoHeight=True)
gb.configure_column("Créditos", flex=13, resizable=False, autoHeight=True)
gb.configure_column(
    "Ver más",
    header_name="Acceso",
    cellRenderer='''(params) => {
        return params.value ? `<a href="${params.value}" target="_blank">🌐 Acceder</a>` : "";
    }''',
    flex=10,
    resizable=False
)

custom_css = {
    ".ag-header": {
        "background-color": "#136ac1 !important",
        "color": "white !important",
        "font-weight": "bold !important"
    },
    ".ag-row": {
        "font-size": "14px !important"
    },
    ".ag-row:nth-child(even)": {
        "background-color": "#f5f5f5 !important"
    },
    ".ag-cell": {
        "white-space": "normal !important",
        "line-height": "1.2 !important",
        "vertical-align": "middle !important",
        "display": "flex !important",
        "align-items": "center !important",
        "justify-content": "flex-start !important"
    }
}

grid_options = gb.build()

# ========== MOSTRAR TABLA ==========
response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    update_mode="SELECTION_CHANGED",
    height=500,
    allow_unsafe_jscode=True,  # ¡Esto es fundamental!
    theme="balham",
    custom_css=custom_css,
    use_container_width=False,
    width=900
)

# ========== NUEVO: DROPDOWN DE ACTIVIDADES ==========
actividades_unicas = df_comisiones["Actividad"].unique().tolist()
actividades_unicas.insert(0, "-Seleccioná actividad-")

actividad_dropdown = st.selectbox("🔽 Elegí una actividad", actividades_unicas)

if actividad_dropdown != "-Seleccioná actividad-":
    # Buscar una comisión asociada a esa actividad
    fila = df_comisiones[df_comisiones["Actividad"] == actividad_dropdown].iloc[0]

    st.session_state["actividad_nombre"] = fila["Actividad"]
    st.session_state["comision_nombre"] = fila["Comisión"]
    st.session_state["fecha_inicio"] = fila["Fecha inicio"]
    st.session_state["fecha_fin"] = fila["Fecha fin"]

    st.markdown(
        f"""<h4>2. Validá tu CUIL para inscribirte en</h4>
        <span style="color:#b72877;font-weight:bold; font-size:1.15em;">
        {actividad_dropdown} ({fila["Comisión"]})
        </span>""",
        unsafe_allow_html=True
    )

    col_cuil, _ = st.columns([1, 1])
    with col_cuil:
        raw = st.text_input("CUIL/CUIT *", value=st.session_state.get("cuil", ""), max_chars=11)
        cuil = ''.join(filter(str.isdigit, raw))[:11]

        if st.button("VALIDAR Y CONTINUAR", type="primary"):
            if not validar_cuil(cuil):
                st.error("El CUIL/CUIT debe tener 11 dígitos válidos.")
                st.session_state["validado"] = False
                st.session_state["cuil_valido"] = False
            else:
                resp = supabase.table("agentesform").select("*").eq("cuil_cuit", cuil).execute()
                if not resp.data:
                    st.session_state["validado"] = False
                    st.session_state["cuil_valido"] = False
                    st.error("❌ No se encontró ese usuario en la base de datos.")
                else:
                    inscrip_existente = supabase.table("pruebainscripciones") \
                        .select("id") \
                        .eq("cuil_cuit", cuil) \
                        .eq("comision", fila["Comisión"]) \
                        .limit(1).execute()

                    if inscrip_existente.data:
                        st.warning("⚠️ Ya realizaste la preinscripción en esa comisión.")
                        st.session_state["validado"] = False
                        st.session_state["cuil_valido"] = False
                    else:
                        st.success("✅ Datos encontrados. Podés continuar.")
                        st.session_state["validado"] = True
                        st.session_state["cuil_valido"] = True
                        st.session_state["cuil"] = cuil
                        st.session_state["datos_agenteform"] = resp.data[0]




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
