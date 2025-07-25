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
            "nombre": c["nombre_actividad"],
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
st.markdown("#### 1. Seleccioná una comisión en la tabla (usá el checkbox):")

gb = GridOptionsBuilder.from_dataframe(df_comisiones)
gb.configure_default_column(sortable=True, wrapText=True, autoHeight=True)
gb.configure_selection(selection_mode="single", use_checkbox=True)
gb.configure_column("Actividad", width=320, wrapText=True, autoHeight=True, tooltipField="Actividad")
gb.configure_column("Comisión", width=160)
gb.configure_column("Fecha inicio", width=110)
gb.configure_column("Fecha fin", width=110)
custom_css = {
    ".ag-header": {"background-color": "#136ac1 !important", "color": "white !important", "font-weight": "bold !important"},
    ".ag-row": {"font-size": "14px !important"},
    ".ag-row:nth-child(even)": {"background-color": "#f5f5f5 !important"},
    ".ag-cell": {
        "white-space": "normal !important",
        "line-height": "1.2 !important"
    },
}
grid_options = gb.build()
response = AgGrid(
    df_comisiones,
    gridOptions=grid_options,
    height=330,
    allow_unsafe_jscode=True,
    theme="balham",
    custom_css=custom_css,
    use_container_width=True
)

selected = response["selected_rows"]
if isinstance(selected, pd.DataFrame):
    selected = selected.to_dict("records")

if selected and selected[0].get("Comisión") != "Sin comisiones":
    fila = selected[0]
    actividad_nombre = fila.get("Actividad", "")
    comision_nombre = fila.get("Comisión", "")
    fecha_inicio = fila.get("Fecha inicio", "")
    fecha_fin = fila.get("Fecha fin", "")

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

    # --- Validar y buscar datos reales ---
    if st.button("VALIDAR Y CONTINUAR", type="primary"):
        if not validar_cuil(cuil):
            st.error("El CUIL/CUIT debe tener 11 dígitos válidos.")
            st.session_state["cuil_valido"] = False
            st.session_state["datos_agenteform"] = {}
        else:
            # Consultar agentesform
            resp = supabase.table("agentesform").select("*").eq("cuil_cuit", cuil).execute()
            if resp.data and len(resp.data) > 0:
                st.session_state["cuil_valido"] = True
                st.session_state["cuil"] = cuil
                st.session_state["datos_agenteform"] = resp.data[0]
                st.success("¡Datos encontrados! Revisá y completá tus datos si es necesario.")
            else:
                st.session_state["cuil_valido"] = False
                st.session_state["datos_agenteform"] = {}
                st.error("No existe esa persona en la base de datos. No podés continuar.")

# ========== BLOQUE 2: DATOS PERSONALES SOLO SI EL CUIL ES VÁLIDO Y EXISTE ==========
if st.session_state.get("validado", False) and st.session_state.get("cuil_valido", False):
    st.markdown("#### 3. Completá tus datos personales")

    datos_agente = st.session_state.get("datos_agenteform", {})

    # Opciones para los selectbox (adaptá si tenés otros valores posibles)
    niveles_educativos = ["", "PRIMARIO", "SECUNDARIO", "TERCIARIO", "UNIVERSITARIO", "POSGRADO"]
    situaciones_revista = [
        "", "PLANTA PERMANENTE", "PLANTA TRANSITORIA",
        "CONTRATOS DEC. 1109/17", "CONTRATOS DEC. 1421/02 (48)"
    ]
    agrupamientos = ["", "PROF", "GRAL"]
    niveles = ["", "A", "B", "C"]
    tramos = ["", "INICIAL", "INTERMEDIO", "AVANZADO"]
    sexos = ["", "F", "M", "X"]

    # Procesar fecha de nacimiento
    if datos_agente.get("fecha_nacimiento"):
        try:
            fecha_nac_valor = pd.to_datetime(datos_agente["fecha_nacimiento"]).date()
        except:
            fecha_nac_valor = date(1980, 1, 1)
    else:
        fecha_nac_valor = date(1980, 1, 1)

    apellido = st.text_input("Apellido *", value=datos_agente.get("apellido", ""))
    nombre = st.text_input("Nombre *", value=datos_agente.get("nombre", ""))
    fecha_nacimiento = st.date_input("Fecha de nacimiento *", value=fecha_nac_valor)
    nivel_educativo = st.selectbox(
        "Nivel educativo", niveles_educativos,
        index=niveles_educativos.index(datos_agente.get("nivel_educativo", "")) if datos_agente.get("nivel_educativo", "") in niveles_educativos else 0
    )
    titulo = st.text_input("Título", value=datos_agente.get("titulo", ""))
    situacion_revista = st.selectbox(
        "Situación de revista", situaciones_revista,
        index=situaciones_revista.index(datos_agente.get("situacion_revista", "")) if datos_agente.get("situacion_revista", "") in situaciones_revista else 0
    )
    agrupamiento = st.selectbox(
        "Agrupamiento", agrupamientos,
        index=agrupamientos.index(datos_agente.get("agrupamiento", "")) if datos_agente.get("agrupamiento", "") in agrupamientos else 0
    )
    nivel = st.selectbox(
        "Nivel", niveles,
        index=niveles.index(datos_agente.get("nivel", "")) if datos_agente.get("nivel", "") in niveles else 0
    )
    grado = st.text_input("Grado", value=datos_agente.get("grado", ""))
    tramo = st.selectbox(
        "Tramo", tramos,
        index=tramos.index(datos_agente.get("tramo", "")) if datos_agente.get("tramo", "") in tramos else 0
    )
    dependencia_simple = st.text_input("Dependencia simple", value=datos_agente.get("dependencia_simple", ""))
    correo = st.text_input("Correo", value=datos_agente.get("correo", ""))
    sexo = st.selectbox(
        "Sexo", sexos,
        index=sexos.index(datos_agente.get("sexo", "")) if datos_agente.get("sexo", "") in sexos else 0
    )

    # --- Enviar ---
    if st.button("ENVIAR INSCRIPCIÓN"):
        datos = {
            "actividad": st.session_state.get("actividad_nombre", ""),
            "comision": st.session_state.get("comision_nombre", ""),
            "fecha_inicio": st.session_state.get("fecha_inicio", ""),
            "fecha_fin": st.session_state.get("fecha_fin", ""),
            "cuil_cuit": st.session_state.get("cuil", ""),
            "apellido": apellido,
            "nombre": nombre,
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
            "sexo": sexo
        }
        # Guardar en Supabase (upsert por cuil_cuit)
        result = supabase.table("agentesform").upsert(datos).execute()
        if result.data:
            st.success("¡Formulario enviado correctamente!")
        else:
            st.error("Ocurrió un error al guardar los datos. Intentalo nuevamente.")

elif st.session_state.get("validado", False) and not st.session_state.get("cuil_valido", True):
    # Si validado pero el CUIL no existe en la base
    st.error("No existe esa persona en la base de datos. No podés continuar.")

else:
    st.info("Seleccioná una comisión y validá tu CUIL para continuar.")

st.markdown("</div>", unsafe_allow_html=True)
