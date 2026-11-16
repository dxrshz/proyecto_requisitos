import streamlit as st
import pandas as pd
from db import conectar
from alertas import obtener_alertas
from recomendaciones import obtener_recomendacion
from actualizar import ejecutar_pipeline
from datetime import date
from calculo import calcular_portafolio

### ═══════════════════════════════════════════════════════════
### CONFIGURACIÓN DE PÁGINA
### ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Asistente de Decisiones RiTech",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

### ═══════════════════════════════════════════════════════════
### SELECTOR DE TEMA Y ESTILOS PERSONALIZADOS
### ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Configuración")
    modo_oscuro = st.toggle("🌙 Modo Oscuro", value=True)
    st.caption("Ajusta los parámetros del portafolio")

if modo_oscuro:
    tema_css = """
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        [data-testid="stSidebar"] { background-color: #161B22; }
        [data-testid="stMetric"] {
            background-color: #1F242D;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #30363D;
        }
        [data-testid="stMetricValue"] { font-size: 1.8rem; color: #FAFAFA; }
        [data-testid="stMetricLabel"] { color: #8B949E; }
        hr { margin: 1.5rem 0; border-color: #30363D; }
        h1, h2, h3 { color: #FAFAFA; padding-bottom: 0.5rem; }
        [data-testid="stDataFrame"] { border-radius: 8px; }
    </style>
    """
else:
    tema_css = """
    <style>
        /* Fondo principal y barra superior */
        .stApp, [data-testid="stHeader"] {
            background-color: #FFFFFF;
            color: #1F2328;
        }
        /* Barra lateral */
        [data-testid="stSidebar"] {
            background-color: #F6F8FA;
        }
        /* Forzar texto oscuro en párrafos, captions, etiquetas y encabezados */
        .stApp p, .stApp span, .stApp label, .stApp li,
        [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stExpander"] summary span,
        h1, h2, h3, h4 {
            color: #1F2328 !important;
        }
        /* Tarjetas de métricas */
        [data-testid="stMetric"] {
            background-color: #F6F8FA;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #D0D7DE;
        }
        [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1F2328 !important; }
        [data-testid="stMetricLabel"] p { color: #57606A !important; }
        /* Pestañas (Tabs) */
        button[data-baseweb="tab"] p {
            color: #1F2328 !important;
        }
        /* Cajas de alerta (st.info, st.warning, etc.) */
        [data-testid="stAlert"] p {
            color: #1F2328 !important;
        }
        hr { margin: 1.5rem 0; border-color: #D0D7DE; }
        [data-testid="stDataFrame"] { border-radius: 8px; }
    </style>
    """
st.markdown(tema_css, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# CONEXIÓN A BD
# ═══════════════════════════════════════════════════════════
conn = conectar()
cursor = conn.cursor()

# ═══════════════════════════════════════════════════════════
# ENCABEZADO PRINCIPAL
# ═══════════════════════════════════════════════════════════
col_logo, col_title = st.columns([1, 8])

with col_logo:
    st.markdown("# 🏦")

with col_title:
    st.title("Asistente de Decisiones RiTech")
    st.caption("Panel de Control · Sprint 3 · Seguimiento del portafolio basado en el NASDAQ")

st.divider()
# ═══════════════════════════════════════════════════════════
# SIDEBAR: CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Configuración")
    st.caption("Ajusta los parámetros del portafolio")
    
    # --- AQUÍ VA EL BLOQUE NUEVO ---
    cursor.execute("SELECT MIN(fecha), MAX(fecha) FROM historico_nasdaq")
    rango_fechas = cursor.fetchone()
    min_fecha = rango_fechas[0] if rango_fechas and rango_fechas[0] else date.today()
    max_fecha = rango_fechas[1] if rango_fechas and rango_fechas[1] else date.today()

    cursor.execute("""
        SELECT id, capital_inicial, moneda, 
               umbral_alerta_perdida, umbral_alerta_ganancia, fecha_inicio
        FROM configuracion 
        ORDER BY id LIMIT 1
    """)
    config = cursor.fetchone()

    if config is None:
        st.info("👋 Primera vez: configura tu portafolio.")
        config_id = None
        capital_actual = 10000.0
        moneda_actual = 'USD'
        umbral_perdida_actual = -5.0
        umbral_ganancia_actual = 10.0
        fecha_inicio_actual = min_fecha
    else:
        config_id = config[0]
        capital_actual = float(config[1])
        moneda_actual = config[2]
        umbral_perdida_actual = float(config[3]) if config[3] is not None else -5.0
        umbral_ganancia_actual = float(config[4]) if config[4] is not None else 10.0
        fecha_inicio_actual = config[5] if config[5] is not None else min_fecha
    # --- FIN DEL BLOQUE NUEVO ---

    with st.form("form_config"):
        capital = st.number_input(
            "💰 Capital Inicial:",
            min_value=0.0,
            value=capital_actual,
            step=100.0,
            format="%.2f"
        )

        moneda = st.selectbox(
            "💵 Moneda:",
            options=['USD', 'COP', 'EUR'],
            index=['USD', 'COP', 'EUR'].index(moneda_actual)
        )
        fecha_inversion = st.date_input(
            "📅 Fecha de inversión:",
            value=max(min_fecha, min(fecha_inicio_actual, max_fecha)),
            min_value=min_fecha,
            max_value=max_fecha
        )
        st.markdown("**🚨 Umbrales de alerta**")
        umbral_perdida = st.number_input(
            "Pérdida (%):",
            min_value=-100.0, max_value=0.0,
            value=umbral_perdida_actual, step=0.5
        )
        umbral_ganancia = st.number_input(
            "Ganancia (%):",
            min_value=0.0, max_value=100.0,
            value=umbral_ganancia_actual, step=0.5
        )

        guardar = st.form_submit_button("💾 Guardar Configuración", use_container_width=True)

    if guardar:
        if config_id is None:
            cursor.execute("""
                INSERT INTO configuracion 
                    (capital_inicial, moneda, umbral_alerta_perdida, umbral_alerta_ganancia, fecha_inicio)
                VALUES (%s, %s, %s, %s, %s)
            """, (capital, moneda, umbral_perdida, umbral_ganancia, fecha_inversion))
        else:
            cursor.execute("""
                UPDATE configuracion 
                SET capital_inicial = %s, moneda = %s,
                    umbral_alerta_perdida = %s, umbral_alerta_ganancia = %s,
                    fecha_inicio = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (capital, moneda, umbral_perdida, umbral_ganancia, fecha_inversion, config_id))

        conn.commit()
        try:
            calcular_portafolio()
        except Exception as e:
            st.error(f"Error al recalcular: {e}")
        st.session_state.pop("ultima_alerta_toast", None)
        st.rerun()

# ═══════════════════════════════════════════════════════════
# BOTÓN: ACTUALIZAR DATOS CON UN CLIC
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.header("🔄 Datos")
    if st.button("Actualizar datos ahora", type="primary", use_container_width=True):
        with st.spinner("Descargando NASDAQ y recalculando portafolio..."):
            try:
                res = ejecutar_pipeline()
                st.session_state["msg_update"] = (
                    "ok",
                    f"Datos al día hasta {res['ultima_fecha']} "
                    f"({res['dias_calculados']} días calculados).",
                )
            except Exception as e:
                st.session_state["msg_update"] = ("error", str(e))
        st.session_state.pop("ultima_alerta_toast", None)
        st.rerun()

    if "msg_update" in st.session_state:
        tipo, texto = st.session_state.pop("msg_update")
        (st.success if tipo == "ok" else st.error)(texto)

    st.divider()
    st.caption(f"Sprint 3")


# ═══════════════════════════════════════════════════════════
# MÉTRICAS PRINCIPALES
# ═══════════════════════════════════════════════════════════
st.subheader("📊 Resumen del Portafolio")

cursor.execute("""
    SELECT fecha, valor_nasdaq, variacion_nasdaq, 
           valor_portafolio, variacion_portafolio, ganancia_perdida
    FROM portafolio_diario 
    ORDER BY fecha DESC 
    LIMIT 1
""")
ultimo_dia = cursor.fetchone()

cursor.execute("SELECT COUNT(*) FROM historico_nasdaq")
total_hist = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM portafolio_diario")
total_port = cursor.fetchone()[0]

if ultimo_dia:
    fecha, nasdaq, var_nasdaq, portafolio, var_portafolio, ganancia = ultimo_dia

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💼 Valor Portafolio",
            value=f"${float(portafolio):,.2f}",
            delta=f"{float(var_portafolio):.2f}%"
        )

    with col2:
        st.metric(
            label="📈 NASDAQ",
            value=f"{float(nasdaq):,.2f}",
            delta=f"{float(var_nasdaq):.2f}%"
        )

    with col3:
        delta_color = "normal" if float(ganancia) >= 0 else "inverse"
        st.metric(
            label="💵 Ganancia/Pérdida",
            value=f"${float(ganancia):,.2f}",
            delta=f"{'▲' if float(ganancia) >= 0 else '▼'} vs. capital"
        )

    with col4:
        st.metric(
            label="📅 Última actualización",
            value=pd.to_datetime(fecha).strftime('%d/%m/%Y')
        )
else:
    st.warning("⚠️ No hay datos. Ejecuta `python actualizar.py` y `python calculo.py`.")

st.divider()


# ═══════════════════════════════════════════════════════════
# GRÁFICOS DE EVOLUCIÓN
# ═══════════════════════════════════════════════════════════
st.subheader("📈 Evolución histórica")

cursor.execute("""
    SELECT fecha, valor_nasdaq, valor_portafolio
    FROM portafolio_diario
    ORDER BY fecha ASC
""")
datos_evol = cursor.fetchall()

if datos_evol:
    df_evol = pd.DataFrame(
        datos_evol,
        columns=['Fecha', 'NASDAQ', 'Portafolio']
    )
    df_evol['Fecha'] = pd.to_datetime(df_evol['Fecha'])
    df_evol['NASDAQ'] = pd.to_numeric(df_evol['NASDAQ'], errors='coerce')
    df_evol['Portafolio'] = pd.to_numeric(df_evol['Portafolio'], errors='coerce')
    df_evol = df_evol.dropna().set_index('Fecha')

    tab1, tab2, tab3 = st.tabs(["📈 NASDAQ", "💼 Portafolio", "⚖️ Comparativa (base 100)"])

    with tab1:
        st.line_chart(df_evol[['NASDAQ']], color="#1f77b4")

    with tab2:
        st.line_chart(df_evol[['Portafolio']], color="#2ca02c")

    with tab3:
        df_norm = df_evol.copy()
        df_norm['NASDAQ'] = df_norm['NASDAQ'] / df_norm['NASDAQ'].iloc[0] * 100
        df_norm['Portafolio'] = df_norm['Portafolio'] / df_norm['Portafolio'].iloc[0] * 100
        st.line_chart(df_norm)
        st.caption("Ambas series comienzan en 100 para comparar rendimiento relativo.")
else:
    st.warning("⚠️ No hay datos de evolución.")

st.divider()

# ═══════════════════════════════════════════════════════════
# NUEVO - ALERTAS DE UMBRALES DE PÉRDIDA Y GANANCIA
# ═══════════════════════════════════════════════════════════
st.header("🚨 Alertas de umbrales")
st.caption("Comprueba si el portafolio llegó a los umbrales de pérdida o ganancia configurados.")

if st.button("🔍 Revisar alertas", type="primary"):
    info = obtener_alertas(cursor)

    if info is None:
        st.warning(
            "⚠️ Aún no hay datos del portafolio. Guarda la configuración y ejecuta "
            "`python actualizar.py` y luego `python calculo.py`."
        )
    else:
        st.caption(f"Evaluado con el último día registrado: {info['fecha']}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Variación del último día", f"{info['variacion_dia']:+.2f}%")
        with col2:
            st.metric("Rentabilidad acumulada", f"{info['rentabilidad']:+.2f}%")

        st.caption(
            f"Umbrales configurados: pérdida {info['umbral_perdida']:.2f}% · "
            f"ganancia +{info['umbral_ganancia']:.2f}%"
        )

        if not info["alertas"]:
            st.info("✅ Sin alertas: el portafolio está dentro de los umbrales.")

        for alerta in info["alertas"]:
            if alerta["tipo"] == "perdida":
                st.error("🔴 ALERTA DE PÉRDIDA — " + alerta["mensaje"])
            else:
                st.success("🟢 ALERTA DE GANANCIA — " + alerta["mensaje"])
else:
    st.info("Pulsa «Revisar alertas» para comprobar si hay pérdidas o ganancias que superen los umbrales.")


st.divider()

### ═══════════════════════════════════════════════════════════
### Parte Juan Cordoba Mi Colega (Recomendaciones de inversión y simulador)
### ═══════════════════════════════════════════════════════════
st.header("🧭 Recomendaciones de inversión")
rec = obtener_recomendacion(cursor)

if rec is None:
    st.warning("⚠️ Se necesitan al menos 12 días de histórico.")
else:
    # Detectar si se tocaron los umbrales configurados según la lógica de recomendaciones.py
    toco_ganancia = rec["accion"] == "TOMAR UTILIDADES"
    toco_perdida = "umbral de pérdida" in rec["detalle"]

    # Banners fijos en pantalla
    if "AUMENTAR" in rec["accion"]:
        st.success(f"🟢  **{rec['accion']}**  — {rec['detalle']}")
    elif "REDUCIR" in rec["accion"] or toco_ganancia:
        st.error(f"🔴  **{rec['accion']}**  — {rec['detalle']}")
    else:
        st.info(f"🟡  **{rec['accion']}**  — {rec['detalle']}")

    # Notificación flotante en la esquina superior derecha (st.toast)
    # Se usa st.session_state para evitar que salte repetidamente al cambiar de tema o abrir expanders
    estado_alerta = f"{rec['accion']}_{rec['rentabilidad']:.2f}"
    if st.session_state.get("ultima_alerta_toast") != estado_alerta:
            if toco_ganancia or toco_perdida:
                color_borde = "#2ea043" if toco_ganancia else "#f85149"
                icono = "🟢 🚀" if toco_ganancia else "🔴 ⚠️"
                titulo = "¡Umbral de ganancia alcanzado!" if toco_ganancia else "¡Alerta de umbral de pérdida!"

                st.markdown(f"""
                <style>
                @keyframes fadeOutToast {{
                    0%   {{ opacity: 1; transform: translateY(0); }}
                    85%  {{ opacity: 1; transform: translateY(0); }}
                    100% {{ opacity: 0; transform: translateY(-20px); visibility: hidden; }}
                }}
                .custom-toast {{
                    position: fixed;
                    top: 60px;
                    right: 25px;
                    z-index: 999999;
                    background-color: #1F242D;
                    color: #FAFAFA !important;
                    border-left: 6px solid {color_borde};
                    padding: 16px 20px;
                    border-radius: 8px;
                    box-shadow: 0 6px 16px rgba(0,0,0,0.4);
                    max-width: 380px;
                    font-size: 0.95rem;
                    animation: fadeOutToast 10s forwards; /* <-- Cambia 10s por los segundos que quieras */
                }}
                </style>
                <div class="custom-toast">
                    <strong>{icono} {titulo}</strong><br>
                    <span style="color: #E6EDF3 !important; font-size: 0.88rem;">{rec['detalle']}</span>
                </div>
                """, unsafe_allow_html=True)
                st.session_state["ultima_alerta_toast"] = estado_alerta

    with st.expander("Ver el análisis detrás de la recomendación"):
        for nombre, punt, texto in rec["señales"]:
            icono = "🟢" if punt > 0 else "🔴" if punt < 0 else "⚪"
            st.write(f"{icono} **{nombre}**: {texto}")

    st.subheader("🎲 Simulador de escenarios")
    df_esc = pd.DataFrame(rec["escenarios"])
    st.dataframe(df_esc.style.format("{:+.2f}%"), hide_index=True)

    st.caption("⚠️ Herramienta de apoyo. No constituye asesoría financiera.")

# ═══════════════════════════════════════════════════════════
# TABLAS DETALLADAS
# ═══════════════════════════════════════════════════════════
st.subheader("📋 Detalle de datos")

tab_hist, tab_port = st.tabs(["📈 historico_nasdaq", "💼 portafolio_diario"])

with tab_hist:
    cursor.execute("""
        SELECT fecha, valor_apertura, valor_maximo, valor_minimo, valor_cierre, volumen
        FROM historico_nasdaq 
        ORDER BY fecha DESC 
        LIMIT 15
    """)
    datos_hist = cursor.fetchall()

    if datos_hist:
        df_hist = pd.DataFrame(
            datos_hist,
            columns=['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen']
        )
        df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha']).dt.strftime('%Y-%m-%d')
        for col in ['Apertura', 'Máximo', 'Mínimo', 'Cierre']:
            df_hist[col] = df_hist[col].apply(lambda x: f"{float(x):,.2f}")
        df_hist['Volumen'] = df_hist['Volumen'].apply(lambda x: f"{int(x):,}")
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No hay registros del NASDAQ.")

with tab_port:
    cursor.execute("""
        SELECT fecha, valor_nasdaq, variacion_nasdaq, 
               valor_portafolio, variacion_portafolio, ganancia_perdida
        FROM portafolio_diario 
        ORDER BY fecha DESC 
        LIMIT 15
    """)
    datos_port = cursor.fetchall()

    if datos_port:
        df_port = pd.DataFrame(
            datos_port,
            columns=['Fecha', 'NASDAQ', 'Var. NASDAQ (%)', 
                     'Valor Portafolio', 'Var. Portafolio (%)', 'Ganancia/Pérdida']
        )
        df_port['Fecha'] = pd.to_datetime(df_port['Fecha']).dt.strftime('%Y-%m-%d')
        df_port['NASDAQ'] = df_port['NASDAQ'].apply(lambda x: f"{float(x):,.2f}")
        df_port['Var. NASDAQ (%)'] = df_port['Var. NASDAQ (%)'].apply(lambda x: f"{float(x):+.2f}%")
        df_port['Valor Portafolio'] = df_port['Valor Portafolio'].apply(lambda x: f"${float(x):,.2f}")
        df_port['Var. Portafolio (%)'] = df_port['Var. Portafolio (%)'].apply(lambda x: f"{float(x):+.2f}%")
        df_port['Ganancia/Pérdida'] = df_port['Ganancia/Pérdida'].apply(lambda x: f"${float(x):+,.2f}")
        st.dataframe(df_port, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No hay registros del portafolio.")


# ═══════════════════════════════════════════════════════════
# CIERRE
# ═══════════════════════════════════════════════════════════
cursor.close()
conn.close()

st.divider()
st.caption("Sprint 3")