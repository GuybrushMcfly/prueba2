import streamlit as st
import pandas as pd
from datetime import date
from st_aggrid import AgGrid, GridOptionsBuilder
from supabase import create_client, Client
from collections import defaultdict

# ========== CONEXIÓN A SUPABASE ==========
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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
        max-width: 70vw !important;
        padding-left: 2vw;
        padding-right: 2vw;
    }
    </style>
""", unsafe_allow_html=True)

# ========== DATOS DESDE SUPABASE ==========
resp_com = supabase.table("comisiones").select(
    "id_comision, organismo, id_actividad, nombre_actividad, fecha_inicio, fecha_fin, creditos, modalidad"
).execute()
comisiones_raw = resp_com.data if resp_com.data else []

# Sacar el listado único de actividades (por id_actividad + nombre_actividad)
actividades_unicas = {}
for c in comisiones_raw:
    if c["id_actividad"] and c["nombre_actividad"]:
        actividades_unicas[c["id_actividad"]] = c["nombre_actividad"]

# Organizar comisiones por actividad
comisiones = defaultdict(list)
for c in comisiones_raw:
    if c["id_actividad"]:
        comisiones[c["id_actividad"]].append({
            "id": c["id_comision"],
            "nombre": c["nombre_actividad"],  # Podrías también usar otro campo como nombre de la comisión si tuvieras uno.
            "fecha_inicio": c["fecha_inicio"],
            "fecha_fin": c["fecha_fin"],
            "organismo": c["organismo"],
            "creditos": c["creditos"],
            "modalidad": c["modalidad"],
        })

# ========== TABLA DE COMISIONES PARA SELECCIÓN ==========
def format_fecha(f):
    if f:
        try:
            return pd.to_datetime(f).strftime("%d/%m/%Y")
        except Exception:
            return f
    return ""

filas = []
for id_act, nombre_act in actividades_unicas.items():
    for c in comisiones.get(id_act, []):
        filas.append({
            "Actividad": nombre_act,
            "Comisión": c["id"],
            "Fecha inicio": format_fecha(c["fecha_inicio"]),
            "Fecha fin": format_fecha(c["fecha_fin"]),
            "Organismo": c["organismo"],
            "Créditos": c["creditos"],
            "Modalidad": c["modalidad"],
        })
    if not comisiones.get(id_act):
        filas.append({
            "Actividad": nombre_act,
            "Comisión": "Sin comisiones",
            "Fecha inicio": "",
            "Fecha fin": "",
            "Organismo": "",
            "Créditos": "",
            "Modalidad": "",
        })
df_comisiones = pd.DataFrame(filas)

# ========== TABLA AGGRID ==========
st.title("FORMULARIO DE INSCRIPCIÓN DE CURSOS")
st.markdown("#### 1. Seleccioná una comisión en la tabla:")

gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True)
gb.configure_column("Actividad", width=220, wrapText=True, autoHeight=True)
gb.configure_column("Comisión", width=160)
gb.configure_column("Fecha inicio", width=110)
gb.configure_column("Fecha fin", width=110)
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
    ".ag-cell": {   # esto fuerza que el texto haga wrap y ajuste el alto
        "white-space": "normal !important",
        "line-height": "1.2 !important"
    },
}
grid_options = gb.build()
response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=290,
    allow_unsafe_jscode=True,
    theme="balham",
    custom_css=custom_css,
    use_container_width=True
)

selected = response["selected_rows"]
if isinstance(selected, pd.DataFrame):
    selected = selected.to_dict("records")

if selected:
    fila = selected[0]
    actividad_nombre = fila["Actividad"]
    comision_nombre = fila["Comisión"]
    fecha_inicio = fila["Fecha inicio"]
    fecha_fin = fila["Fecha fin"]

    comision_id = f"{actividad_nombre}|{comision_nombre}|{fecha_inicio}|{fecha_fin}"
    if st.session_state.get("last_comision_id") != comision_id:
        st.session_state["validado"] = False
        st.session_state["last_comision_id"] = comision_id
        for k in ["cuil", "nombres", "apellidos", "nivel", "grado", "agrupamiento", "tramo"]:
            st.session_state.pop(k, None)

    st.markdown(f"#### 2. Validá tu CUIL para inscribirte en **{actividad_nombre}** - {comision_nombre}")
    col_cuil, _ = st.columns([1, 1])
    with col_cuil:
        raw = st.text_input("CUIL/CUIT *", value=st.session_state.get("cuil", ""), max_chars=11)
        cuil = ''.join(filter(str.isdigit, raw))[:11]

    if st.button("VALIDAR Y CONTINUAR", type="primary"):
        if not validar_cuil(cuil):
            st.error("El CUIL/CUIT debe tener 11 dígitos válidos.")
        else:
            st.session_state.update({
                "validado": True,
                "cuil": cuil,
                "actividad_nombre": actividad_nombre,
                "comision_nombre": comision_nombre,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            })

# ========== BLOQUE 2: DATOS PERSONALES ==========
if st.session_state.get("validado", False):
    st.markdown("#### 3. Completá tus datos personales")

    # Simular carga desde "base de agentes" (esto lo podés adaptar a buscar en otra tabla)
    datos_agente = {
        "cuil": st.session_state.get("cuil", ""),
        "apellidos": st.session_state.get("apellidos", "ROSENZVEIG"),
        "nombres": st.session_state.get("nombres", "MARCELO ADRIAN"),
        "fecha_nac": "1961-10-26",
        "genero": "",
        "nivel_educ": "UNIVERSITARIO",
        "titulo": "LIC. EN PSICOLOGIA",
        "sit_revista": "PLANTA PERMANENTE",
        "nivel": "B",
        "grado": "8",
        "agrupamiento": "PROF",
        "tramo": "INTERMEDIO",
        "tareas": "",
        "dependencia": dependencias[0],
        "correo_indec": "",
        "correo_alt": "",
    }

    # Apellido/s y Nombre/s en la misma fila
    col_ap, col_nom = st.columns(2)
    with col_ap:
        apellidos = st.text_input("APELLIDO/S *", value=datos_agente["apellidos"], key="apellidos")
    with col_nom:
        nombres = st.text_input("NOMBRE/S *", value=datos_agente["nombres"], key="nombres_detalle")

    # Fecha de nacimiento y Género en la misma fila
    col_fec, col_gen = st.columns(2)
    with col_fec:
        fecha_nac = st.date_input("FECHA DE NACIMIENTO *", value=date(1961, 10, 26), key="fecha_nac")
    with col_gen:
        genero = st.selectbox("GÉNERO *", ["-Seleccioná-"] + generos, key="genero")

    # Nivel educativo y Título en la misma fila
    col_niv_edu, col_tit = st.columns(2)
    with col_niv_edu:
        nivel_educ = st.selectbox("NIVEL EDUCATIVO *", niveles_educativos, index=niveles_educativos.index(datos_agente["nivel_educ"]), key="nivel_educ")
    with col_tit:
        titulo = st.text_input("ÚLTIMO TÍTULO ALCANZADO *", value=datos_agente["titulo"], key="titulo")

    # Situación de revista (SOLO EN LA PRIMERA COLUMNA, la segunda queda vacía)
    col_sit, col_vacia = st.columns(2)
    with col_sit:
        situacion = st.selectbox("SITUACIÓN DE REVISTA *", situaciones_revista, index=situaciones_revista.index(datos_agente["sit_revista"]), key="situacion_revista")

    # NIVEL y GRADO en la misma fila
    col_nivel, col_grado = st.columns(2)
    # AGRUPAMIENTO y TRAMO en la misma fila
    col_agrup, col_tramo = st.columns(2)

    # LIMPIEZA DE CAMPOS SEGÚN SITUACIÓN
    if "ultima_situacion" not in st.session_state:
        st.session_state["ultima_situacion"] = situacion
    if st.session_state["ultima_situacion"] != situacion:
        for campo in ["nivel", "grado", "agrupamiento", "tramo"]:
            if campo in st.session_state:
                del st.session_state[campo]
        st.session_state["ultima_situacion"] = situacion

    # CAMPOS VARIABLES
    if situacion == "PLANTA PERMANENTE":
        with col_nivel:
            nivel = st.selectbox("NIVEL *", niveles, index=niveles.index(datos_agente["nivel"]), key="nivel")
        with col_grado:
            grado = st.text_input("GRADO *", value=datos_agente["grado"], key="grado")
        with col_agrup:
            agrupamiento = st.selectbox("AGRUPAMIENTO *", agrupamientos, index=agrupamientos.index(datos_agente["agrupamiento"]), key="agrupamiento")
        with col_tramo:
            tramo = st.selectbox("TRAMO", tramos, index=tramos.index(datos_agente["tramo"]), key="tramo")
        tareas = st.text_area("TAREAS DESARROLLADAS *", max_chars=255, key="tareas")
    elif situacion == "PLANTA TRANSITORIA":
        with col_nivel:
            nivel = st.selectbox("NIVEL *", niveles, key="nivel")
        with col_grado:
            grado = st.text_input("GRADO *", key="grado")
        with col_agrup:
            agrupamiento = st.selectbox("AGRUPAMIENTO *", agrupamientos, key="agrupamiento")
        with col_tramo:
            tramo = ""
        tareas = st.text_area("TAREAS DESARROLLADAS *", max_chars=255, key="tareas")
    elif situacion == "CONTRATOS DEC. 1421/02":
        with col_nivel:
            nivel = st.selectbox("NIVEL *", niveles, key="nivel")
        with col_grado:
            grado = st.text_input("GRADO *", key="grado")
        with col_agrup:
            agrupamiento = st.selectbox("AGRUPAMIENTO *", agrupamientos, key="agrupamiento")
        with col_tramo:
            tramo = ""
        tareas = st.text_area("TAREAS DESARROLLADAS *", max_chars=255, key="tareas")
    elif situacion == "CONTRATOS DEC. 1109/17":
        nivel = grado = agrupamiento = tramo = ""
        tareas = st.text_area("TAREAS DESARROLLADAS *", max_chars=255, key="tareas")
    else:
        nivel = grado = agrupamiento = tramo = tareas = ""

    # Dependencia y correos
    dependencia = st.selectbox("DEPENDENCIA *", dependencias, index=0, key="dependencia")
    c3, c4 = st.columns(2)
    with c3:
        correo_indec = st.text_input("CORREO INDEC *", value="@indec.gob.ar", key="correo_indec")
    with c4:
        correo_alt = st.text_input("CORREO ALTERNATIVO (opcional)", key="correo_alt")

    # ---- Enviar ----
    if st.button("ENVIAR INSCRIPCIÓN"):
        datos = {
            "actividad": st.session_state.get("actividad_nombre", ""),
            "comision": st.session_state.get("comision_nombre", ""),
            "fecha_inicio": st.session_state.get("fecha_inicio", ""),
            "fecha_fin": st.session_state.get("fecha_fin", ""),
            "apellidos": apellidos,
            "nombres": nombres,
            "cuil": st.session_state.get("cuil", ""),
            "fecha_nac": fecha_nac,
            "nivel_educ": nivel_educ,
            "genero": genero,
            "titulo": titulo,
            "situacion": situacion,
            "tareas": tareas,
            "dependencia": dependencia,
            "correo_indec": correo_indec,
            "correo_alt": correo_alt,
        }
        if situacion == "PLANTA PERMANENTE":
            datos.update({
                "nivel": st.session_state.get("nivel", ""),
                "grado": st.session_state.get("grado", ""),
                "agrupamiento": st.session_state.get("agrupamiento", ""),
                "tramo": st.session_state.get("tramo", "")
            })
        elif situacion in ["PLANTA TRANSITORIA", "CONTRATOS DEC. 1421/02"]:
            datos.update({
                "nivel": st.session_state.get("nivel", ""),
                "grado": st.session_state.get("grado", ""),
                "agrupamiento": st.session_state.get("agrupamiento", "")
            })

        st.success("¡Formulario enviado correctamente!")
        st.write("**Datos enviados:**")
        st.json(datos)

else:
    st.info("Seleccioná una comisión y validá tu CUIL para continuar.")

st.markdown("</div>", unsafe_allow_html=True)
