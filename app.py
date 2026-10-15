import streamlit as st
import pandas as pd
from db import conectar


# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Asistente de Decisiones RiTech",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
# ESTILOS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════
st.markdown("""
    <style>
    /* Métricas más grandes */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    /* Separadores más sutiles */
    hr {
        margin: 1.5rem 0;
    }
    /* Títulos */
    h1 {
        padding-bottom: 0.5rem;
    }
    /* Tablas */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)


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

    cursor.execute("""
        SELECT id, capital_inicial, moneda, 
               umbral_alerta_perdida, umbral_alerta_ganancia 
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
    else:
        config_id = config[0]
        capital_actual = float(config[1])
        moneda_actual = config[2]
        umbral_perdida_actual = float(config[3]) if config[3] is not None else -5.0
        umbral_ganancia_actual = float(config[4]) if config[4] is not None else 10.0

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
                    (capital_inicial, moneda, umbral_alerta_perdida, umbral_alerta_ganancia)
                VALUES (%s, %s, %s, %s)
            """, (capital, moneda, umbral_perdida, umbral_ganancia))
            st.success("✅ Configuración inicial creada")
        else:
            cursor.execute("""
                UPDATE configuracion 
                SET capital_inicial = %s, moneda = %s,
                    umbral_alerta_perdida = %s, umbral_alerta_ganancia = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (capital, moneda, umbral_perdida, umbral_ganancia, config_id))
            st.success("✅ Configuración actualizada")

        conn.commit()
        st.rerun()

    st.divider()
    st.caption(f"© 2026 RiTech SAS")


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