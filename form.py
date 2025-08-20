import streamlit as st
import pandas as pd
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from supabase import create_client, Client
from collections import defaultdict
import os
import streamlit.components.v1 as components
import plotly.graph_objects as go

# Datos de ejemplo
data = pd.DataFrame([
    {"Actividad": "Curso de Python Avanzado para Data Science", "URL": "https://python.org", "Categoría": "Programación", "Duración": "40 horas"},
    {"Actividad": "Desarrollo de Aplicaciones Web con Streamlit", "URL": "https://streamlit.io", "Categoría": "Web Development", "Duración": "25 horas"},
    {"Actividad": "Análisis de Datos con Pandas y NumPy", "URL": "https://pandas.pydata.org", "Categoría": "Data Science", "Duración": "30 horas"},
    {"Actividad": "Machine Learning con Scikit-learn", "URL": "https://scikit-learn.org", "Categoría": "AI/ML", "Duración": "50 horas"}
])

st.title("🎨 Alternativas a AgGrid para tablas estilizadas")

# ========== OPCIÓN 1: ST.DATAFRAME CON COLUMN_CONFIG (RECOMENDADA) ==========
st.header("✅ 1. st.dataframe() con column_config (Streamlit >= 1.23)")

st.info("🆕 **La mejor alternativa:** Funciona con links clickeables + personalización avanzada")

# Crear DataFrame con links
data_with_links = data.copy()

styled_df = st.dataframe(
    data,
    column_config={
        "Actividad": st.column_config.TextColumn(
            "📚 Curso",
            help="Nombre del curso disponible",
            max_chars=100,
            width="large"
        ),
        "URL": st.column_config.LinkColumn(
            "🔗 Enlace",
            help="Haz click para abrir el curso",
            display_text=r"https://.*\.(.+)",  # Regex para mostrar solo el dominio
            width="medium"
        ),
        "Categoría": st.column_config.SelectboxColumn(
            "🏷️ Categoría",
            help="Tipo de curso",
            width="medium",
            options=["Programación", "Web Development", "Data Science", "AI/ML"]
        ),
        "Duración": st.column_config.ProgressColumn(
            "⏱️ Horas",
            help="Duración del curso",
            min_value=0,
            max_value=60,
            format="%d hrs",
            width="small"
        ),
    },
    height=300,  # ✅ ALTURA PERSONALIZABLE
    use_container_width=True,
    hide_index=True
)

st.success("✅ **Ventajas:** Links clickeables + altura personalizable + buen styling")

st.divider()

# ========== OPCIÓN 2: PANDAS STYLER CON CSS ==========
st.header("🎨 2. Pandas Styler + CSS personalizado")

# Función de styling personalizado
def style_dataframe(df):
    return df.style \
        .set_properties(**{
            'background-color': '#f0f2f6',
            'color': '#262730',
            'border': '1px solid #e6e9ef',
            'padding': '12px',  # ✅ ALTURA DE CELDA
            'text-align': 'left'
        }) \
        .set_table_styles([
            # Estilo del header
            {
                'selector': 'th',
                'props': [
                    ('background-color', '#4CAF50'),
                    ('color', 'white'),
                    ('font-weight', 'bold'),
                    ('padding', '15px'),  # ✅ ALTURA DEL HEADER
                    ('border', '1px solid #45a049')
                ]
            },
            # Hover effect
            {
                'selector': 'tbody tr:hover',
                'props': [('background-color', '#e8f5e8')]
            },
            # Styling general de la tabla
            {
                'selector': '',
                'props': [
                    ('border-collapse', 'collapse'),
                    ('margin', '25px 0'),
                    ('font-size', '16px'),  # ✅ TAMAÑO DE FUENTE
                    ('min-width', '400px')
                ]
            }
        ])

# Aplicar styling
styled_data = style_dataframe(data)
st.dataframe(styled_data, height=300, use_container_width=True)

# Código CSS personalizado adicional
st.markdown("""
<style>
    /* CSS personalizado para tablas */
    .stDataFrame > div {
        border: 2px solid #4CAF50;
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

st.success("✅ **Ventajas:** CSS completamente personalizable + altura ajustable")

st.divider()

# ========== OPCIÓN 3: PLOTLY TABLE (MUY ESTILIZADO) ==========
st.header("🚀 3. Plotly Table (súper profesional)")

fig = go.Figure(data=[go.Table(
    columnwidth=[300, 150, 120, 100],  # ✅ ANCHO DE COLUMNAS
    header=dict(
        values=list(data.columns),
        fill_color='#4CAF50',
        font=dict(color='white', size=16),
        align='center',
        height=50  # ✅ ALTURA DEL HEADER
    ),
    cells=dict(
        values=[data[col] for col in data.columns],
        fill_color=[['#f0f2f6', '#ffffff'] * len(data)],  # Colores alternados
        font=dict(color='#262730', size=14),
        align='left',
        height=40  # ✅ ALTURA DE FILAS
    )
)])

fig.update_layout(
    title="📊 Tabla con Plotly - Súper Profesional",
    title_x=0.5,
    height=400,  # ✅ ALTURA TOTAL
    margin=dict(l=0, r=0, t=50, b=0)
)

st.plotly_chart(fig, use_container_width=True)
st.warning("⚠️ **Limitación:** Los links no son clickeables en Plotly Table")

st.divider()

# ========== OPCIÓN 4: HTML PERSONALIZADO ==========
st.header("🛠️ 4. HTML + CSS personalizado completo")

# Generar HTML personalizado
def create_html_table(df):
    html = """
    <style>
        .custom-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 16px;
            font-family: 'Arial', sans-serif;
            min-width: 400px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }
        .custom-table thead tr {
            background-color: #4CAF50;
            color: #ffffff;
            text-align: left;
        }
        .custom-table th,
        .custom-table td {
            padding: 18px 15px;  /* ✅ ALTURA PERSONALIZABLE */
            border-bottom: 1px solid #dddddd;
        }
        .custom-table tbody tr {
            background-color: #f3f3f3;
        }
        .custom-table tbody tr:nth-of-type(even) {
            background-color: #f9f9f9;
        }
        .custom-table tbody tr:hover {
            background-color: #e8f5e8;
            transform: scale(1.02);
            transition: all 0.3s ease;
        }
        .custom-table a {
            color: #4CAF50;
            text-decoration: none;
            font-weight: bold;
        }
        .custom-table a:hover {
            text-decoration: underline;
        }
    </style>
    
    <table class="custom-table">
        <thead>
            <tr>
    """
    
    # Headers
    for col in df.columns:
        if col == "URL":
            html += f"<th>🔗 Enlace</th>"
        else:
            html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    
    # Rows
    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            if col == "URL":
                html += f'<td><a href="{row[col]}" target="_blank">🌐 Abrir</a></td>'
            else:
                html += f"<td>{row[col]}</td>"
        html += "</tr>"
    
    html += "</tbody></table>"
    return html

st.markdown(create_html_table(data), unsafe_allow_html=True)
st.success("✅ **Ventajas:** Control total sobre CSS + links clickeables + animaciones")

st.divider()

# ========== OPCIÓN 5: STREAMLIT ELEMENTS (EXPERIMENTAL) ==========
st.header("🧪 5. Alternativa: streamlit-elements")

st.code("""
# Instalar: pip install streamlit-elements
from streamlit_elements import elements, mui

with elements("demo"):
    mui.DataGrid(
        rows=data.to_dict('records'),
        columns=[
            {"field": "Actividad", "headerName": "Curso", "width": 300},
            {"field": "URL", "headerName": "Enlace", "width": 200},
        ],
        autoHeight=True,
        rowHeight=60,  # ✅ ALTURA PERSONALIZABLE
    )
""")

st.info("📦 **Requiere instalación:** `pip install streamlit-elements`")

# ========== COMPARACIÓN FINAL ==========
st.header("📊 Comparación de alternativas")

comparison_data = pd.DataFrame([
    {"Método": "st.dataframe + column_config", "Links clickeables": "✅", "Altura personalizable": "✅", "CSS avanzado": "⚠️ Limitado", "Facilidad": "🟢 Fácil"},
    {"Método": "Pandas Styler", "Links clickeables": "❌", "Altura personalizable": "✅", "CSS avanzado": "✅", "Facilidad": "🟡 Medio"},
    {"Método": "Plotly Table", "Links clickeables": "❌", "Altura personalizable": "✅", "CSS avanzado": "✅", "Facilidad": "🟡 Medio"},
    {"Método": "HTML personalizado", "Links clickeables": "✅", "Altura personalizable": "✅", "CSS avanzado": "✅", "Facilidad": "🔴 Difícil"},
    {"Método": "streamlit-elements", "Links clickeables": "✅", "Altura personalizable": "✅", "CSS avanzado": "✅", "Facilidad": "🔴 Difícil"},
    {"Método": "AgGrid", "Links clickeables": "❌", "Altura personalizable": "✅", "CSS avanzado": "✅", "Facilidad": "🟡 Medio"}
])

st.dataframe(
    comparison_data,
    column_config={
        "Links clickeables": st.column_config.TextColumn("🔗 Links"),
        "CSS avanzado": st.column_config.TextColumn("🎨 CSS"),
        "Facilidad": st.column_config.TextColumn("⚙️ Facilidad")
    },
    hide_index=True,
    use_container_width=True
)

# ========== RECOMENDACIÓN ==========
st.success("""
## 🎯 **Mi recomendación para tu caso:**

### 🥇 **1ra opción: st.dataframe() + column_config**
- ✅ Links clickeables nativos
- ✅ Altura personalizable
- ✅ Styling decente
- ✅ Fácil de implementar
- ✅ Mantenible

### 🥈 **2da opción: HTML personalizado**
- ✅ Control total sobre diseño
- ✅ Links clickeables
- ✅ CSS completamente personalizable
- ⚠️ Más trabajo de desarrollo

**¿Por qué no seguir con AgGrid?** Si ya tienes el flujo funcionando con AgGrid + botones externos, puede que sea mejor dejarlo así. Pero si quieres links directos en las celdas, `st.dataframe()` es tu mejor opción.
""")



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
