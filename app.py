"""Panel de inversiones RiTech con selector de idioma español/inglés."""

from datetime import date
from html import escape

import pandas as pd
import streamlit as st

from actualizar import ejecutar_pipeline
from alertas import obtener_alertas
from calculo import calcular_portafolio
from db import conectar
from idiomas import traducir
from acceso import requerir_acceso, cerrar_sesion, guardar_preferencias
from recomendaciones import obtener_recomendacion


# ═══════════════════════════════════════════════════════════
# PÁGINA E IDIOMA — solo cambia lo que ve el usuario
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="RiTech | Asistente de Decisiones",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Control de acceso antes de crear el sidebar o ejecutar consultas financieras.
requerir_acceso()
# Todas las operaciones privadas exigen este identificador de la sesión validada.
usuario_id = st.session_state["ritech_usuario_id"]

# Conservamos el arranque original: actualización NASDAQ una sola vez por sesión,
# pero únicamente DESPUÉS de autenticar. Si falla, el panel sigue funcionando.
if not st.session_state.get("ritech_auto_actualizado"):
    with st.spinner(traducir("update_spinner", st.session_state.get("idioma", "es"))):
        try:
            resumen = ejecutar_pipeline(usuario_id)
            st.session_state["msg_update"] = ("ok", resumen)
        except Exception as exc:
            st.session_state["msg_update"] = ("error", str(exc))
    st.session_state["ritech_auto_actualizado"] = True

if "idioma" not in st.session_state:
    st.session_state["idioma"] = st.session_state.get("ritech_pref_idioma", "es")
if "tema_oscuro" not in st.session_state:
    st.session_state["tema_oscuro"] = st.session_state.get("ritech_pref_tema", True)

with st.sidebar:
    st.markdown("### 🌐 Idioma / Language")
    st.selectbox(
        "Idioma / Language",
        options=["es", "en"],
        format_func=lambda codigo: "🇪🇸 Español" if codigo == "es" else "🇺🇸 English",
        key="idioma",
        index=0 if st.session_state.get("ritech_pref_idioma", "es") == "es" else 1,
        on_change=guardar_preferencias,
        label_visibility="collapsed",
    )

idioma = st.session_state["idioma"]


def tr(clave, **variables):
    """Traduce etiquetas y mensajes con el idioma elegido en la barra lateral."""
    return traducir(clave, idioma, **variables)


with st.sidebar:
    st.caption(tr("language_hint"))
    st.divider()
    st.header(tr("settings"))
    modo_oscuro = st.toggle(
        tr("dark_mode"), value=st.session_state.get("ritech_pref_tema", True),
        key="tema_oscuro", on_change=guardar_preferencias
    )
    st.caption(tr("sidebar_caption"))
    st.divider()
    st.caption(tr("auth_signed_in_as", user=st.session_state.get("ritech_usuario", "")))
    if st.button(tr("auth_logout"), key="ritech_logout", use_container_width=True):
        cerrar_sesion()


# ═══════════════════════════════════════════════════════════
# ESTILOS — conservados para los temas oscuro y claro
# ═══════════════════════════════════════════════════════════
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
        .stApp, [data-testid="stHeader"] { background-color: #f0f4f7; color: #1F2328; }
        [data-testid="stSidebar"] { background-color: #dfe2e6; }
        .stApp p, .stApp span, .stApp label, .stApp li,
        [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stExpander"] summary span,
        h1, h2, h3, h4 { color: #1F2328 !important; }
        [data-testid="stMetric"] {
            background-color: #F6F8FA;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #D0D7DE;
        }
        [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1F2328 !important; }
        [data-testid="stMetricLabel"] p { color: #57606A !important; }
        button[data-baseweb="tab"] p { color: #1F2328 !important; }
        [data-testid="stAlert"] p { color: #1F2328 !important; }
        hr { margin: 1.5rem 0; border-color: #D0D7DE; }
        [data-testid="stDataFrame"] { border-radius: 8px; }
    </style>
    """
st.markdown(tema_css, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# CONEXIÓN A LA BASE DE DATOS
# ═══════════════════════════════════════════════════════════
try:
    conn = conectar()
    cursor = conn.cursor()
except (RuntimeError, Exception) as exc:
    st.error(tr("connection_failed"))
    st.info(tr("connection_steps"))
    # No mostrar detalles del servidor ni credenciales en la interfaz.
    st.stop()

try:
    cursor.execute("SELECT 1 FROM configuracion WHERE usuario_id = %s LIMIT 1", (usuario_id,))
    cursor.execute("SELECT 1 FROM historico_nasdaq LIMIT 1")
    cursor.execute("SELECT 1 FROM portafolio_diario WHERE usuario_id = %s LIMIT 1", (usuario_id,))
except Exception:
    st.error(tr("schema_missing"))
    cursor.close()
    conn.close()
    st.stop()

# ═══════════════════════════════════════════════════════════
# ENCABEZADO
# ═══════════════════════════════════════════════════════════
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("# 🏦")
with col_title:
    st.title(tr("title"))
    st.caption(tr("subtitle"))
st.divider()

# ═══════════════════════════════════════════════════════════
# SIDEBAR: CONFIGURACIÓN DEL PORTAFOLIO
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    cursor.execute("SELECT MIN(fecha), MAX(fecha) FROM historico_nasdaq")
    rango_fechas = cursor.fetchone()
    min_fecha = rango_fechas[0] if rango_fechas and rango_fechas[0] else date.today()
    max_fecha = rango_fechas[1] if rango_fechas and rango_fechas[1] else date.today()

    cursor.execute("""
        SELECT id, capital_inicial, moneda,
               umbral_alerta_perdida, umbral_alerta_ganancia, fecha_inicio
        FROM configuracion WHERE usuario_id = %s ORDER BY id LIMIT 1
    """, (usuario_id,))
    config = cursor.fetchone()

    if config is None:
        st.info(tr("personal_setup_needed"))
        config_id = None
        capital_actual = 10000.0
        moneda_actual = "USD"
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

    with st.form("form_config"):
        capital = st.number_input(
            tr("initial_capital"), min_value=0.0, value=capital_actual,
            step=100.0, format="%.2f", key="capital_inicial",
        )
        opciones_monedas = ["USD", "COP", "EUR"]
        moneda = st.selectbox(
            tr("currency"), options=opciones_monedas,
            index=opciones_monedas.index(moneda_actual), key="moneda",
        )
        fecha_inversion = st.date_input(
            tr("investment_date"),
            value=max(min_fecha, min(fecha_inicio_actual, max_fecha)),
            min_value=min_fecha, max_value=max_fecha, key="fecha_inversion",
        )
        st.markdown(tr("alert_thresholds"))
        umbral_perdida = st.number_input(
            tr("loss_pct"), min_value=-100.0, max_value=0.0,
            value=umbral_perdida_actual, step=0.5, key="umbral_perdida",
        )
        umbral_ganancia = st.number_input(
            tr("profit_pct"), min_value=0.0, max_value=100.0,
            value=umbral_ganancia_actual, step=0.5, key="umbral_ganancia",
        )
        guardar = st.form_submit_button(tr("save_settings"), use_container_width=True)

    if guardar:
        # Una sola configuración por dueño, incluso con dos pestañas abiertas.
        # Nunca se actualizan las configuraciones históricas sin dueño.
        cursor.execute("""
            INSERT INTO configuracion
                (usuario_id, capital_inicial, moneda,
                 umbral_alerta_perdida, umbral_alerta_ganancia, fecha_inicio)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (usuario_id) WHERE usuario_id IS NOT NULL
            DO UPDATE SET capital_inicial = EXCLUDED.capital_inicial,
                          moneda = EXCLUDED.moneda,
                          umbral_alerta_perdida = EXCLUDED.umbral_alerta_perdida,
                          umbral_alerta_ganancia = EXCLUDED.umbral_alerta_ganancia,
                          fecha_inicio = EXCLUDED.fecha_inicio,
                          updated_at = CURRENT_TIMESTAMP
        """, (usuario_id, capital, moneda, umbral_perdida, umbral_ganancia, fecha_inversion))

        conn.commit()
        try:
            calcular_portafolio(usuario_id)
        except Exception as e:
            st.error(tr("recalculate_error", error=str(e)))
        st.session_state.pop("ultima_alerta_toast", None)
        st.rerun()

# ═══════════════════════════════════════════════════════════
# BOTÓN: ACTUALIZAR DATOS
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.header(tr("data_title"))
    if st.button(tr("update_now"), type="primary", use_container_width=True, key="actualizar_datos"):
        with st.spinner(tr("update_spinner")):
            try:
                res = ejecutar_pipeline(usuario_id)
                # Se guardan los DATOS, no un mensaje ya traducido.
                st.session_state["msg_update"] = ("ok", res)
            except Exception as e:
                st.session_state["msg_update"] = ("error", str(e))
        st.session_state.pop("ultima_alerta_toast", None)
        st.rerun()

    if "msg_update" in st.session_state:
        tipo, resultado = st.session_state.pop("msg_update")
        if tipo == "ok":
            if resultado.get("sin_configuracion"):
                st.info(tr("personal_setup_needed"))
            else:
                st.success(tr("update_success", date=resultado["ultima_fecha"], days=resultado["dias_calculados"]))
        else:
            st.error(tr("update_error", error=resultado))

    st.divider()
    st.caption("Sprint 4")

# ═══════════════════════════════════════════════════════════
# MÉTRICAS PRINCIPALES
# ═══════════════════════════════════════════════════════════

st.subheader(tr("portfolio_summary"))
st.caption(tr("personal_space", user=st.session_state["ritech_usuario"]))

cursor.execute("""
    SELECT fecha, valor_nasdaq, variacion_nasdaq,
           valor_portafolio, variacion_portafolio, ganancia_perdida
    FROM portafolio_diario WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 1
""", (usuario_id,))
ultimo_dia = cursor.fetchone()

if ultimo_dia:
    fecha, nasdaq, var_nasdaq, portafolio, var_portafolio, ganancia = ultimo_dia
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(tr("portfolio_value"), f"${float(portafolio):,.2f}", f"{float(var_portafolio):.2f}%")
    with col2:
        st.metric("📈 NASDAQ", f"{float(nasdaq):,.2f}", f"{float(var_nasdaq):.2f}%")
    with col3:
        st.metric(
            tr("profit_loss"), f"${float(ganancia):,.2f}",
            f"{'▲' if float(ganancia) >= 0 else '▼'} {tr('vs_capital')}",
            delta_color="normal" if float(ganancia) >= 0 else "inverse",
        )
    with col4:
        st.metric(tr("last_update"), pd.to_datetime(fecha).strftime("%d/%m/%Y"))
else:
    st.warning(tr("no_data"))
st.divider()

# ═══════════════════════════════════════════════════════════
# GRÁFICOS DE EVOLUCIÓN
# ═══════════════════════════════════════════════════════════
st.subheader(tr("historical_evolution"))
cursor.execute("""
    SELECT fecha, valor_nasdaq, valor_portafolio
    FROM portafolio_diario WHERE usuario_id = %s ORDER BY fecha ASC
""", (usuario_id,))
datos_evol = cursor.fetchall()

if datos_evol:
    df_evol = pd.DataFrame(datos_evol, columns=["fecha", "nasdaq", "portafolio"])
    df_evol["fecha"] = pd.to_datetime(df_evol["fecha"])
    df_evol["nasdaq"] = pd.to_numeric(df_evol["nasdaq"], errors="coerce")
    df_evol["portafolio"] = pd.to_numeric(df_evol["portafolio"], errors="coerce")
    df_evol = df_evol.dropna().set_index("fecha")
    df_evol.index.name = tr("date")
    df_evol = df_evol.rename(columns={"nasdaq": "NASDAQ", "portafolio": tr("portfolio")})

    tab1, tab2, tab3 = st.tabs(["📈 NASDAQ", tr("portfolio_tab"), tr("compare_tab")])
    with tab1:
        st.line_chart(df_evol[["NASDAQ"]], color="#1f77b4")
    with tab2:
        st.line_chart(df_evol[[tr("portfolio")]], color="#2ca02c")
    with tab3:
        df_norm = df_evol.copy()
        df_norm["NASDAQ"] = df_norm["NASDAQ"] / df_norm["NASDAQ"].iloc[0] * 100
        df_norm[tr("portfolio")] = df_norm[tr("portfolio")] / df_norm[tr("portfolio")].iloc[0] * 100
        st.line_chart(df_norm)
        st.caption(tr("comparative_caption"))
else:
    st.warning(tr("no_evolution"))
st.divider()

# ═══════════════════════════════════════════════════════════
# ALERTAS DE UMBRALES
# ═══════════════════════════════════════════════════════════
st.header(tr("threshold_alerts"))
st.caption(tr("threshold_caption"))

# El resultado del botón sigue visible al alternar de idioma.
if st.button(tr("review_alerts"), type="primary", key="revisar_alertas"):
    st.session_state["mostrar_alertas"] = True

if st.session_state.get("mostrar_alertas", False):
    info = obtener_alertas(cursor, usuario_id)
    if info is None:
        st.warning(tr("no_portfolio_for_alerts"))
    else:
        st.caption(tr("evaluated_date", date=info["fecha"]))
        col1, col2 = st.columns(2)
        with col1:
            st.metric(tr("daily_change"), f"{info['variacion_dia']:+.2f}%")
        with col2:
            st.metric(tr("cumulative_return"), f"{info['rentabilidad']:+.2f}%")
        st.caption(tr("configured_thresholds", loss=info["umbral_perdida"], profit=info["umbral_ganancia"]))

        if not info["alertas"]:
            st.info(tr("no_alerts"))
        for alerta in info["alertas"]:
            perdida = alerta["tipo"] == "perdida"
            titulo = tr("loss_alert_name" if perdida else "profit_alert_name")
            detalle = tr(
                "alert_loss_detail" if perdida else "alert_profit_detail",
                measure=tr(alerta["medida_id"]),
                value=alerta["valor"], threshold=alerta["umbral"],
            )
            (st.error if perdida else st.success)(f"{titulo} — {detalle}")
else:
    st.info(tr("review_prompt"))
st.divider()

# ═══════════════════════════════════════════════════════════
# RECOMENDACIONES DE INVERSIÓN Y SIMULADOR
# ═══════════════════════════════════════════════════════════
st.header(tr("recommendations_title"))
rec = obtener_recomendacion(cursor, usuario_id)

if rec is None:
    st.warning(tr("insufficient_history"))
else:
    # La recomendación conserva exactamente su lógica original; solo se traduce su presentación.
    accion = tr(rec["accion_id"])
    detalle = tr(rec["detalle_id"], **rec["detalle_vars"])
    toco_ganancia = rec["accion_id"] == "action_take_profit"
    toco_perdida = rec["detalle_id"] == "recommendation_loss_threshold"

    if rec["accion_id"] == "action_increase":
        st.success(f"🟢  **{accion}**  — {detalle}")
    elif rec["accion_id"] == "action_reduce" or toco_ganancia:
        st.error(f"🔴  **{accion}**  — {detalle}")
    else:
        st.info(f"🟡  **{accion}**  — {detalle}")

    # Mensajes flotantes que respetan el idioma seleccionado.
    estado_alerta = f"{rec['accion_id']}_{rec['rentabilidad']:.2f}_{idioma}"
    if st.session_state.get("ultima_alerta_toast") != estado_alerta:
        if toco_ganancia or toco_perdida:
            color_borde = "#2ea043" if toco_ganancia else "#f85149"
            icono = "🟢 🚀" if toco_ganancia else "🔴 ⚠️"
            titulo = tr("gain_toast_title") if toco_ganancia else tr("loss_toast_title")
            st.markdown(f"""
            <style>
            @keyframes fadeOutToast {{
                0% {{ opacity: 1; transform: translateY(0); }}
                85% {{ opacity: 1; transform: translateY(0); }}
                100% {{ opacity: 0; transform: translateY(-20px); visibility: hidden; }}
            }}
            .custom-toast {{
                position: fixed; top: 60px; right: 25px; z-index: 999999;
                background-color: #1F242D; color: #FAFAFA !important;
                border-left: 6px solid {color_borde}; padding: 16px 20px;
                border-radius: 8px; box-shadow: 0 6px 16px rgba(0,0,0,0.4);
                max-width: 380px; font-size: 0.95rem;
                animation: fadeOutToast 10s forwards;
            }}
            </style>
            <div class="custom-toast">
                <strong>{icono} {escape(titulo)}</strong><br>
                <span style="color: #E6EDF3 !important; font-size: 0.88rem;">{escape(detalle)}</span>
            </div>
            """, unsafe_allow_html=True)
            st.session_state["ultima_alerta_toast"] = estado_alerta

    with st.expander(tr("analysis_expander")):
        for senal in rec["senales_ui"]:
            punt = senal["puntaje"]
            icono = "🟢" if punt > 0 else "🔴" if punt < 0 else "⚪"
            nombre = tr(senal["nombre_id"])
            descripcion = tr(senal["descripcion_id"], **senal["variables"])
            st.write(f"{icono} **{nombre}**: {descripcion}")

    st.subheader(tr("scenarios_title"))
    df_esc = pd.DataFrame(rec["escenarios"])
    df_esc = df_esc.rename(columns={"Portafolio (%)": tr("portfolio_pct")})
    st.dataframe(df_esc.style.format("{:+.2f}%"), hide_index=True)
    st.caption(tr("disclaimer"))

# ═══════════════════════════════════════════════════════════
# TABLAS DETALLADAS
# ═══════════════════════════════════════════════════════════
st.subheader(tr("details_title"))
tab_hist, tab_port = st.tabs([tr("nasdaq_history_tab"), tr("portfolio_daily_tab")])

with tab_hist:
    cursor.execute("""
        SELECT fecha, valor_apertura, valor_maximo, valor_minimo, valor_cierre, volumen
        FROM historico_nasdaq ORDER BY fecha DESC LIMIT 15
    """)
    datos_hist = cursor.fetchall()
    if datos_hist:
        df_hist = pd.DataFrame(datos_hist, columns=["Fecha", "Apertura", "Máximo", "Mínimo", "Cierre", "Volumen"])
        df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"]).dt.strftime("%Y-%m-%d")
        for columna in ["Apertura", "Máximo", "Mínimo", "Cierre"]:
            df_hist[columna] = df_hist[columna].apply(lambda x: f"{float(x):,.2f}")
        df_hist["Volumen"] = df_hist["Volumen"].apply(lambda x: f"{int(x):,}")
        df_hist = df_hist.rename(columns={
            "Fecha": tr("date"), "Apertura": tr("opening"), "Máximo": tr("high"),
            "Mínimo": tr("low"), "Cierre": tr("closing"), "Volumen": tr("volume"),
        })
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.warning(tr("no_nasdaq_records"))

with tab_port:
    cursor.execute("""
        SELECT fecha, valor_nasdaq, variacion_nasdaq,
               valor_portafolio, variacion_portafolio, ganancia_perdida
        FROM portafolio_diario WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 15
    """, (usuario_id,))
    datos_port = cursor.fetchall()
    if datos_port:
        df_port = pd.DataFrame(datos_port, columns=[
            "Fecha", "NASDAQ", "Var. NASDAQ (%)", "Valor Portafolio", "Var. Portafolio (%)", "Ganancia/Pérdida"
        ])
        df_port["Fecha"] = pd.to_datetime(df_port["Fecha"]).dt.strftime("%Y-%m-%d")
        df_port["NASDAQ"] = df_port["NASDAQ"].apply(lambda x: f"{float(x):,.2f}")
        df_port["Var. NASDAQ (%)"] = df_port["Var. NASDAQ (%)"].apply(lambda x: f"{float(x):+.2f}%")
        df_port["Valor Portafolio"] = df_port["Valor Portafolio"].apply(lambda x: f"${float(x):,.2f}")
        df_port["Var. Portafolio (%)"] = df_port["Var. Portafolio (%)"].apply(lambda x: f"{float(x):+.2f}%")
        df_port["Ganancia/Pérdida"] = df_port["Ganancia/Pérdida"].apply(lambda x: f"${float(x):+,.2f}")
        df_port = df_port.rename(columns={
            "Fecha": tr("date"), "Var. NASDAQ (%)": tr("nasdaq_change_pct"),
            "Valor Portafolio": tr("portfolio_value").replace("💼 ", ""),
            "Var. Portafolio (%)": tr("portfolio_change_pct"),
            "Ganancia/Pérdida": tr("profit_loss").replace("💵 ", ""),
        })
        st.dataframe(df_port, use_container_width=True, hide_index=True)
    else:
        st.warning(tr("no_portfolio_records"))

# ═══════════════════════════════════════════════════════════
# CIERRE
# ═══════════════════════════════════════════════════════════
cursor.close()
conn.close()
st.divider()
st.caption("Sprint 4")
