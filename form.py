# ================== IMPORTACIONES ==================
import streamlit as st
import pandas as pd
import time
import random
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

# ========== RESET GLOBAL (post inscripción) ==========
if st.session_state.get("inscripcion_exitosa", False):
    st.balloons()
    st.success("✅ ¡Preinscripción exitosa! Tus datos fueron enviados correctamente.")
    time.sleep(1.5)
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

# ========== ESTILOS PERSONALIZADOS ==========
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

# ========== FUNCIONES ==========
def validar_cuil(cuil: str) -> bool:
    if not cuil.isdigit() or len(cuil) != 11:
        return False
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(cuil[i]) * mult[i] for i in range(10))
    verificador = 11 - (total % 11)
    if verificador == 11: verificador = 0
    elif verificador == 10: verificador = 9
    return verificador == int(cuil[-1])

def verificar_formulario_cuil(supabase: Client, cuil: str) -> bool:
    try:
        response = supabase.rpc("verificar_formulario_cuil", {"cuil_input": cuil}).execute()
        return response.data[0].get("existe", False)
    except Exception:
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
    except Exception:
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
    except Exception:
        return False

def obtener_datos_para_formulario(supabase: Client, cuil: str) -> dict:
    try:
        response = supabase.rpc("obtener_datos_para_formulario", {"cuil_input": cuil}).execute()
        if response.data and isinstance(response.data, list):
            return response.data[0]  # Devuelve un dict
        return {}
    except Exception as e:
        st.error(f"Error al obtener los datos del formulario: {e}")
        return {}

# ========== CARGA DE DATOS DESDE VISTA ==========
def obtener_comisiones():
    resp = supabase.table("vista_comisiones_abiertas").select(
        "id, id_comision_sai, organismo, id_actividad, nombre_actividad, "
        "fecha_desde, fecha_hasta, fecha_cierre, creditos, modalidad_cursada, "
        "link_externo, apto_tramo"
    ).execute()
    return resp.data if resp.data else []

comisiones_raw = obtener_comisiones()

# ========== CREAR DATAFRAME ==========
df_temp = pd.DataFrame(comisiones_raw)

# Conversión de fechas
df_temp["fecha_desde"] = pd.to_datetime(df_temp["fecha_desde"], errors="coerce")
df_temp["fecha_hasta"] = pd.to_datetime(df_temp["fecha_hasta"], errors="coerce")
df_temp["fecha_cierre"] = pd.to_datetime(df_temp["fecha_cierre"], errors="coerce")

# Campos obligatorios
required_cols = ["id_comision_sai", "nombre_actividad", "fecha_desde", "fecha_hasta"]
df_temp = df_temp.dropna(subset=required_cols)

# Campos visuales
df_temp["Actividad"] = df_temp["nombre_actividad"]
df_temp["Comisión"] = df_temp["id_comision_sai"]
df_temp["Fecha inicio"] = df_temp["fecha_desde"].dt.strftime("%d/%m/%Y")
df_temp["Fecha fin"] = df_temp["fecha_hasta"].dt.strftime("%d/%m/%Y")
df_temp["Fecha cierre"] = df_temp["fecha_cierre"].dt.strftime("%d/%m/%Y")
df_temp["Actividad dropdown"] = (
    df_temp["nombre_actividad"] + " (" + df_temp["Fecha inicio"] + " al " + df_temp["Fecha fin"] + ")"
)
df_temp["Actividad (Comisión)"] = df_temp["nombre_actividad"] + " (" + df_temp["id_comision_sai"] + ")"
df_temp["Créditos"] = df_temp["creditos"].fillna(0).astype(int)

def clasificar_duracion(creditos):
    if 1 <= creditos < 10: return "BREVE (hasta 10 hs)"
    elif 10 <= creditos < 20: return "INTERMEDIA (entre 10 y 20 hs)"
    elif creditos >= 20: return "PROLONGADA (más de 20 hs)"
    return "SIN CLASIFICAR"

df_temp["Duración"] = df_temp["Créditos"].apply(clasificar_duracion)
df_temp["Modalidad"] = df_temp["modalidad_cursada"]
df_temp["Apto tramo"] = df_temp["apto_tramo"].fillna("No")
df_temp["Ver más"] = df_temp["link_externo"]  # solo URL

# ========== PASO 1: FILTROS ==========
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)
    st.markdown("##### 1) Revisá la oferta de actividades disponibles.")

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

    # Recalcular columna combinada como Actividad (Comisión)
    df_temp["Actividad (Comisión)"] = df_temp["nombre_actividad"] + " (" + df_temp["id_comision_sai"] + ")"

    df_comisiones = df_filtrado[[
        "Actividad (Comisión)", "Fecha inicio", "Fecha fin", "Fecha cierre",
        "Créditos", "Modalidad", "Apto tramo", "Ver más"
    ]].reset_index(drop=True)

    def create_html_table(df):
        if df.empty:
            st.warning("No se encontraron cursos con los filtros seleccionados.")
            return ""

        table_id = f"coursesTable_{hash(str(df.values.tobytes())) % 10000}"

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
        }}
        .courses-table tbody tr.selected {{
            background-color: #bbdefb !important;
            border-left: 4px solid #136ac1;
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
            html += f'<tr onclick="{onclick_code}">' \
                    + f'<td>{row["Actividad (Comisión)"]}</td>' \
                    + f'<td>{row["Fecha inicio"]}</td>' \
                    + f'<td>{row["Fecha fin"]}</td>' \
                    + f'<td>{row["Fecha cierre"]}</td>' \
                    + f'<td>{row["Créditos"]}</td>' \
                    + f'<td>{row["Modalidad"]}</td>' \
                    + f'<td>{row["Apto tramo"]}</td>'

            if pd.notna(row["Ver más"]) and row["Ver más"]:
                html += f'<td><a href="{row["Ver más"]}" target="_blank" onclick="event.stopPropagation()">Acceder</a></td>'
            else:
                html += '<td><span class="no-link">Sin enlace</span></td>'

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

    html_code = create_html_table(df_comisiones)

    # DataTables
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
                search: "", searchPlaceholder: "🔍 Buscar...",
                lengthMenu: "Mostrar _MENU_ registros por página",
                zeroRecords: "No se encontraron resultados",
                info: "Mostrando página _PAGE_ de _PAGES_",
                infoEmpty: "No hay registros disponibles",
                infoFiltered: "(filtrado de _MAX_ registros totales)",
                paginate: { previous: "Anterior", next: "Siguiente" }
            }
        });
        $(".dataTables_filter").css({ "float": "left", "margin-bottom": "10px" });
        $(".dataTables_filter input").css({ "width": "300px" });
        $(".dataTables_length").css({ "float": "right" });
    });
    </script>
    """

    altura_dinamica = min(600, 100 + (len(df_comisiones) * 50))
    components.html(html_code, height=altura_dinamica, scrolling=True)

    # ========== TARJETAS DESTACADAS ==========
    st.markdown("---")
    st.subheader("🌟 Actividades destacadas")

    tarjetas = df_comisiones.head(6).to_dict(orient="records")

    st.markdown("""
    <style>
    .card-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 25px;
        margin-top: 20px;
    }
    .card {
        background-color: #f9f9f9;
        padding: 20px;
        border-left: 5px solid #136ac1;
        border-radius: 10px;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 220px;
    }
    .card:hover {
        transform: scale(1.03);
        box-shadow: 0 8px 18px rgba(0,0,0,0.15);
    }
    .card h4 {
        margin-top: 0;
        font-size: 16px;
        color: #136ac1;
    }
    .card p {
        margin: 6px 0;
        font-size: 14px;
    }
    </style>
    <div class="card-grid">
    """, unsafe_allow_html=True)

    html_tarjetas = '<div class="card-grid">'
    
    for item in tarjetas:
        html_tarjetas += f"""
        <div class="card">
            <h4>{item['Actividad (Comisión)']}</h4>
            <p><b>📅 Fechas:</b> {item['Fecha inicio']} al {item['Fecha fin']}</p>
            <p><b>🎓 Modalidad:</b> {item['Modalidad']}</p>
            <p><b>⭐ Créditos:</b> {item['Créditos']}</p>
        </div>
        """
    
    html_tarjetas += '</div>'
    st.markdown(html_tarjetas, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    




# ========== PASO 2: Selección de actividad ==========
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)
    st.markdown("##### 2) Seleccioná la actividad en la cual querés preinscribirte.")

    # Actividad (Comisión) ya está en formato "nombre (ID)"
    dropdown_list = ["-Seleccioná una actividad para preinscribirte-"] + df_temp["Actividad (Comisión)"].tolist()

    # Leer valor desde query params o session_state
    selected_from_query = st.query_params.get("selected_activity", [None])[0]
    initial_index = 0

    # Si hay valor en query param, usarlo
    if selected_from_query in dropdown_list:
        initial_index = dropdown_list.index(selected_from_query)
    else:
        selected_from_query = None
        initial_index = 0

    # 🔁 Mostrar dropdown con clave variable para forzar su reinicio completo
    clave_selectbox = f"actividad_key_{random.randint(0, 999999)}" if st.session_state.get("__reset_placeholder") else "actividad_key_default"
    actividad_seleccionada = st.selectbox("Actividad disponible", dropdown_list, index=initial_index, key=clave_selectbox)

    # 🔐 Asegurarse de que el valor sea válido
    if actividad_seleccionada not in dropdown_list:
        actividad_seleccionada = dropdown_list[0]

    # 🔁 Reinicio visual después de cerrar éxito
    if st.session_state.get("__reset_placeholder", False):
        st.session_state["__reset_placeholder"] = False
        st.session_state["actividad_anterior"] = "-Seleccioná una actividad para preinscribirte-"

    # 🧼 Detectar si cambió la selección
    if "actividad_anterior" not in st.session_state:
        st.session_state["actividad_anterior"] = ""

    if actividad_seleccionada != st.session_state["actividad_anterior"]:
        st.session_state["actividad_anterior"] = actividad_seleccionada
        st.session_state["cuil_valido"] = False
        st.session_state["validado"] = False
        st.session_state["cuil"] = ""
        st.session_state["datos_agenteform"] = {}

    # ========== MOSTRAR DETALLES DE LA COMISIÓN ==========
    if actividad_seleccionada != "-Seleccioná una actividad para preinscribirte-":
        fila = df_temp[df_temp["Actividad (Comisión)"] == actividad_seleccionada].iloc[0]

        # Guardar en session_state para uso posterior
        st.session_state["actividad_nombre"] = fila["Actividad"]
        st.session_state["comision_nombre"] = fila["Comisión"]
        st.session_state["fecha_inicio"] = fila["Fecha inicio"]
        st.session_state["fecha_fin"] = fila["Fecha fin"]
        st.session_state["comision_id"] = fila["id"]
        st.session_state["id_actividad"] = fila["id_actividad"]

        # Mostrar
        st.markdown(f"""
        <div style="background-color: #f0f8ff; padding: 15px; border-left: 5px solid #136ac1; border-radius: 5px;">
          <b>🟦 Actividad:</b> {fila['nombre_actividad']}<br>
          <b>🆔 Comisión:</b> {fila['id_comision_sai']}<br>
          <b>🧬 UUID Comisión:</b> <code>{fila['id']}</code><br>
          <b>📅 Fechas:</b> {fila['fecha_desde']} al {fila['fecha_hasta']}<br>
          <b>📌 Cierre Inscripción:</b> {fila['fecha_cierre']}<br>
          <b>⭐ Créditos:</b> {fila['creditos']}<br>
          <b>🎓 Modalidad:</b> {fila['modalidad_cursada']}<br>
          <b>❓ Apto tramo:</b> {fila['apto_tramo']}<br>
        </div>
        """, unsafe_allow_html=True)



    st.markdown('</div>', unsafe_allow_html=True)



# ========== PASO 3: Validación de CUIL ==========
with st.container():
    st.markdown('<div class="paso-container">', unsafe_allow_html=True)

    if actividad_seleccionada != "-Seleccioná una actividad para preinscribirte-":
        st.markdown("##### 3) Ingresá tu número de CUIL y validalo con el botón.")

        cuil_input = st.text_input("CUIL (11 dígitos)", max_chars=11, key="cuil_input")

        if st.button("Validar CUIL", key="validar_cuil_btn"):

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
                except:
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
                except:
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
                except:
                    return False

            def obtener_datos_para_formulario(supabase: Client, cuil: str) -> dict:
                try:
                    response = supabase.rpc("obtener_datos_para_formulario", {"cuil_input": cuil}).execute()
                    if response.data and isinstance(response.data, list):
                        return response.data[0]
                    return {}
                except:
                    return {}

            if not validar_cuil(cuil_input):
                st.session_state["cuil_valido"] = False
                st.session_state["validado"] = True
                st.session_state["motivo_bloqueo"] = "cuil_invalido"
                st.error("CUIL/CUIT inválido. Verificá que tenga 11 dígitos y sea correcto.")

            else:
                existe = verificar_formulario_cuil(supabase, cuil_input)

                # 🔍 DEBUG OPCIONAL
                st.markdown("---")
                st.subheader("🧪 DEBUG DE VALIDACIÓN DE CUIL")
                st.write("🔍 CUIL ingresado:", cuil_input)
                st.write("🔍 UUID comisión seleccionada:", st.session_state.get("comision_id"))
            
                resultado = verificar_formulario_comision(supabase, cuil_input, st.session_state.get("comision_id"))
                st.write("✅ ¿Ya está inscripto según Supabase?", resultado)

                
                if not existe:
                    st.session_state["cuil_valido"] = False
                    st.session_state["validado"] = True
                    st.session_state["motivo_bloqueo"] = "no_encontrado"
                    st.error("⚠️ El CUIL/CUIT no corresponde a un agente activo.")
                else:
                    id_actividad = st.session_state.get("id_actividad", "")
                    ya_aprobo = verificar_formulario_historial(supabase, cuil_input, id_actividad)

                    if ya_aprobo:
                        st.session_state["cuil_valido"] = False
                        st.session_state["validado"] = True
                        st.session_state["motivo_bloqueo"] = "ya_aprobo"
                        st.warning("⚠️ Ya realizaste esta actividad y fue APROBADA.")
                    else:
                        #comision_id = st.session_state.get("comision_nombre", "")
                        comision_id = st.session_state.get("comision_id", "")  # ✅ Esto es el UUID correcto
                        ya_inscripto = verificar_formulario_comision(supabase, cuil_input, comision_id)

                        if ya_inscripto:
                            st.session_state["cuil_valido"] = False
                            st.session_state["validado"] = True
                            st.session_state["motivo_bloqueo"] = "ya_inscripto"
                            st.warning("⚠️ Ya estás inscripto en esta comisión.")
                        else:
                            st.session_state["cuil"] = cuil_input
                            st.session_state["cuil_valido"] = True
                            st.session_state["validado"] = True
                            st.session_state["motivo_bloqueo"] = ""

                            st.success("✅ CUIL/CUIT válido. Podés continuar con la preinscripción.")

                            datos = obtener_datos_para_formulario(supabase, cuil_input)
                            st.session_state["datos_agenteform"] = datos

                            if datos:
                                st.markdown("---")
                                st.markdown("### 🧾 Datos obtenidos del agente")
                                for campo, valor in datos.items():
                                    st.markdown(f"**{campo.replace('_', ' ').capitalize()}:** {valor if valor else '-'}")
                                st.markdown("---")

# ========== PASO 4: Formulario de inscripción ==========
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
        st.markdown("Completá los siguientes campos para finalizar tu preinscripción:")

        # --- CAMPOS: Nivel educativo + Título
        col1, col2 = st.columns(2)
        niveles_educativos = [
            "-Seleccioná último nivel completo-", "PRIMARIO", "SECUNDARIO",
            "TERCIARIO", "UNIVERSITARIO", "POSGRADO"
        ]
        valor_nivel = datos_agente.get("nivel_educativo", "")
        indice_nivel = niveles_educativos.index(valor_nivel) if valor_nivel in niveles_educativos else 0

        with col1:
            nivel_educativo = st.selectbox("Nivel educativo", niveles_educativos, index=indice_nivel, key="nivel_educativo")

        with col2:
            titulo_valor = datos_agente.get("titulo", "").upper() if datos_agente.get("titulo") else ""
            titulo = st.text_input("Título", value=titulo_valor, key="titulo").upper()

        # --- TAREAS DESARROLLADAS
        tareas = st.text_area("Tareas desarrolladas", height=100, key="tareas_desarrolladas").lower()

        # --- MAIL ALTERNATIVO
        correo_oficial = datos_agente.get("email", "")
        st.markdown(f"📧 Te vamos a contactar al correo registrado: **{correo_oficial}**")
        email_alternativo = st.text_input("Correo alternativo (opcional)", key="email_alternativo")
        if email_alternativo and "@" not in email_alternativo:
            st.warning("📧 El correo alternativo no tiene un formato válido.")

        # --- BOTÓN FINAL DE ENVÍO
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

                result = supabase.table("cursos_inscripciones").insert(datos_inscripcion).execute()

                if result.data:
                    st.session_state["nombre_actividad_exito"] = st.session_state.get("actividad_nombre")
                    st.session_state["inscripcion_exitosa"] = True

                    st.balloons()
                    st.success("✅ ¡Preinscripción exitosa!")

                    # 🔁 Forzar limpieza total en próximo run
                    st.session_state["resetear_todo"] = True
                    st.rerun()
                else:
                    st.error("❌ Ocurrió un error al guardar la inscripción.")

    st.markdown('</div>', unsafe_allow_html=True)



