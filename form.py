
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

# ========== ALTERNATIVA: TABLA HTML + CSS PERSONALIZADO ==========
st.divider()
st.header("🆕 ALTERNATIVA: Tabla HTML con links clickeables")

# Función para crear la tabla HTML con funcionalidad de click
def create_html_table(df, df_original):
    html = """
    <style>
        .courses-table {
            border-collapse: collapse;
            margin: 25px auto;
            font-size: 14px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-width: 900px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
            background-color: white;
        }
        .courses-table thead tr {
            background-color: #136ac1;
            color: #ffffff;
            text-align: left;
            font-weight: bold;
        }
        .courses-table th,
        .courses-table td {
            padding: 16px 12px;
            border-bottom: 1px solid #e0e0e0;
            vertical-align: middle;
        }
        .courses-table th {
            font-size: 15px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .courses-table tbody tr {
            background-color: #ffffff;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .courses-table tbody tr:nth-of-type(even) {
            background-color: #f5f5f5;
        }
        .courses-table tbody tr:hover {
            background-color: #e3f2fd;
            transform: translateY(-2px);
            box-shadow: 0 2px 8px rgba(19, 106, 193, 0.2);
        }
        .courses-table tbody tr.selected {
            background-color: #bbdefb !important;
            border-left: 4px solid #136ac1;
        }
        .courses-table td:first-child {
            font-weight: 500;
            color: #2c3e50;
            max-width: 400px;
            line-height: 1.4;
        }
        .courses-table .fecha-col {
            text-align: center;
            font-weight: 500;
            color: #34495e;
        }
        .courses-table .creditos-col {
            text-align: center;
            font-weight: bold;
            color: #27ae60;
        }
        .courses-table .acceso-col {
            text-align: center;
        }
        .courses-table a {
            color: #136ac1;
            text-decoration: none;
            font-weight: bold;
            padding: 8px 16px;
            border: 2px solid #136ac1;
            border-radius: 5px;
            transition: all 0.3s ease;
            display: inline-block;
        }
        .courses-table a:hover {
            background-color: #136ac1;
            color: white;
            transform: scale(1.05);
        }
        .no-link {
            color: #bdc3c7;
            font-style: italic;
        }
        .detail-panel {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 2px solid #136ac1;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            display: none;
        }
        .detail-panel h3 {
            color: #136ac1;
            margin-top: 0;
            border-bottom: 2px solid #136ac1;
            padding-bottom: 10px;
        }
        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .detail-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .detail-label {
            font-weight: bold;
            color: #136ac1;
            margin-bottom: 5px;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .detail-value {
            color: #2c3e50;
            font-size: 14px;
            word-wrap: break-word;
        }
        @media (max-width: 768px) {
            .courses-table {
                font-size: 12px;
                min-width: auto;
            }
            .courses-table th,
            .courses-table td {
                padding: 12px 8px;
            }
            .detail-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    
    <div style="overflow-x: auto;">
        <table class="courses-table" id="coursesTable">
            <thead>
                <tr>
                    <th style="width: 45%;">Actividad (Comisión) <small style="font-weight: normal; font-size: 11px;">(Click para ver detalles)</small></th>
                    <th style="width: 15%;">Fecha Inicio</th>
                    <th style="width: 15%;">Fecha Fin</th>
                    <th style="width: 10%;">Créditos</th>
                    <th style="width: 15%;">Acceso</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Generar filas con datos completos embebidos
    if len(df) == 0:
        html += """
                <tr>
                    <td colspan="5" style="text-align: center; color: #7f8c8d; font-style: italic; padding: 30px;">
                        No se encontraron cursos con los filtros seleccionados
                    </td>
                </tr>
        """
    else:
        for idx, row in df.iterrows():
            # Buscar los datos completos del DataFrame original
            original_row = df_original[df_original["Actividad (Comisión)"] == row["Actividad (Comisión)"]].iloc[0]
            
            # Crear atributos de datos para JavaScript
            data_attrs = f'''
                data-id-comision="{original_row.get('id_comision_sai', 'N/A')}"
                data-id-actividad="{original_row.get('id_actividad', 'N/A')}"
                data-organismo="{original_row.get('organismo', 'N/A')}"
                data-modalidad="{original_row.get('modalidad_cursada', 'N/A')}"
                data-nombre-actividad="{original_row.get('nombre_actividad', 'N/A')}"
                data-fecha-desde="{original_row.get('fecha_desde', 'N/A')}"
                data-fecha-hasta="{original_row.get('fecha_hasta', 'N/A')}"
                data-creditos="{original_row.get('creditos', 'N/A')}"
                data-link-externo="{original_row.get('link_externo', 'N/A')}"
            '''
            
            html += f'<tr onclick="showDetails(this)" {data_attrs}>'
            
            # Actividad (Comisión)
            html += f'<td title="{row["Actividad (Comisión)"]}">{row["Actividad (Comisión)"]}</td>'
            
            # Fecha inicio
            html += f'<td class="fecha-col">{row["Fecha inicio"]}</td>'
            
            # Fecha fin
            html += f'<td class="fecha-col">{row["Fecha fin"]}</td>'
            
            # Créditos
            html += f'<td class="creditos-col">{row["Créditos"]}</td>'
            
            # Acceso (Ver más) - prevenir propagación del click
            if pd.notna(row["Ver más"]) and row["Ver más"]:
                html += f'<td class="acceso-col"><a href="{row["Ver más"]}" target="_blank" onclick="event.stopPropagation()">🌐 Acceder</a></td>'
            else:
                html += '<td class="acceso-col"><span class="no-link">Sin enlace</span></td>'
            
            html += "</tr>"
    
    html += """
            </tbody>
        </table>
    </div>
    
    <!-- Panel de detalles -->
    <div id="detailPanel" class="detail-panel">
        <h3>📋 Detalles del Curso Seleccionado</h3>
        <div class="detail-grid" id="detailGrid">
            <!-- Los detalles se cargan aquí con JavaScript -->
        </div>
    </div>
    
    <script>
        let selectedRow = null;
        
        function showDetails(row) {
            // Remover selección anterior
            if (selectedRow) {
                selectedRow.classList.remove('selected');
            }
            
            // Marcar nueva selección
            selectedRow = row;
            row.classList.add('selected');
            
            // Obtener datos de la fila
            const details = {
                'ID Comisión SAI': row.dataset.idComision,
                'ID Actividad': row.dataset.idActividad,
                'Nombre Actividad': row.dataset.nombreActividad,
                'Organismo': row.dataset.organismo,
                'Modalidad': row.dataset.modalidad,
                'Fecha Desde': row.dataset.fechaDesde,
                'Fecha Hasta': row.dataset.fechaHasta,
                'Créditos': row.dataset.creditos,
                'Link Externo': row.dataset.linkExterno
            };
            
            // Generar HTML para los detalles
            let detailsHTML = '';
            for (const [label, value] of Object.entries(details)) {
                let displayValue = value === 'N/A' || value === 'nan' || value === 'None' || !value ? 
                    '<span style="color: #bdc3c7; font-style: italic;">No disponible</span>' : value;
                
                // Hacer clickeable el link externo si existe
                if (label === 'Link Externo' && value && value !== 'N/A' && value !== 'nan' && value !== 'None') {
                    displayValue = `<a href="${value}" target="_blank" style="color: #136ac1; text-decoration: underline;">${value}</a>`;
                }
                
                detailsHTML += `
                    <div class="detail-item">
                        <div class="detail-label">${label}</div>
                        <div class="detail-value">${displayValue}</div>
                    </div>
                `;
            }
            
            // Mostrar el panel y actualizar contenido
            document.getElementById('detailGrid').innerHTML = detailsHTML;
            document.getElementById('detailPanel').style.display = 'block';
            
            // Scroll suave al panel de detalles
            document.getElementById('detailPanel').scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest' 
            });
        }
    </script>
    """
    
    return html

# Mostrar la tabla HTML con funcionalidad de detalles
st.markdown(create_html_table(df_comisiones, df_temp), unsafe_allow_html=True)

# Mostrar información adicional
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📚 Total de cursos", len(df_comisiones))

with col2:
    cursos_con_link = len(df_comisiones[df_comisiones["Ver más"].notna()])
    st.metric("🔗 Con enlace", cursos_con_link)

with col3:
    creditos_total = df_comisiones["Créditos"].sum()
    st.metric("⭐ Créditos totales", creditos_total)




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
