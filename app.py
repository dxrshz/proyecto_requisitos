import streamlit as st
import pandas as pd
from db import conectar


st.set_page_config(
    page_title="Asistente de Decisiones RiTech",
    page_icon="🏦",
    layout="wide"
)

st.title("🏦 Asistente de Decisiones RiTech")
st.markdown("**Panel de Control - Sprint 2**")
st.divider()


# ═══════════════════════════════════════════════════════════
# CONEXIÓN A BD
# ═══════════════════════════════════════════════════════════
conn = conectar()
cursor = conn.cursor()


# ═══════════════════════════════════════════════════════════
# SECCIÓN 1: CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════
st.header("⚙️ Configuración del Portafolio")

cursor.execute("""
    SELECT id, capital_inicial, moneda, 
           umbral_alerta_perdida, umbral_alerta_ganancia 
    FROM configuracion 
    ORDER BY id LIMIT 1
""")
config = cursor.fetchone()

if config is None:
    st.info("👋 Primera vez: configura tu portafolio y guarda los cambios.")
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
    col1, col2 = st.columns(2)
    
    with col1:
        capital = st.number_input(
            "Capital Inicial:",
            min_value=0.0,
            value=capital_actual,
            step=100.0,
            format="%.2f"
        )
        moneda = st.selectbox(
            "Moneda:",
            options=['USD', 'COP', 'EUR'],
            index=['USD', 'COP', 'EUR'].index(moneda_actual)
        )
    
    with col2:
        umbral_perdida = st.number_input(
            "Umbral alerta pérdida (%):",
            min_value=-100.0, max_value=0.0,
            value=umbral_perdida_actual, step=0.5
        )
        umbral_ganancia = st.number_input(
            "Umbral alerta ganancia (%):",
            min_value=0.0, max_value=100.0,
            value=umbral_ganancia_actual, step=0.5
        )
    
    guardar = st.form_submit_button("💾 Guardar Configuración")


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


# ═══════════════════════════════════════════════════════════
# SECCIÓN 2: ESTADO DEL SISTEMA
# ═══════════════════════════════════════════════════════════
st.header("📊 Estado del Sistema")

cursor.execute("SELECT COUNT(*) FROM historico_nasdaq")
total_hist = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM portafolio_diario")
total_port = cursor.fetchone()[0]

col1, col2 = st.columns(2)
with col1:
    st.metric("Registros NASDAQ", total_hist)
with col2:
    st.metric("Registros Portafolio", total_port)


st.divider()


# ═══════════════════════════════════════════════════════════
# SECCIÓN 3: HISTÓRICO NASDAQ
# ═══════════════════════════════════════════════════════════
st.header("📈 historico_nasdaq (últimos 10)")

cursor.execute("""
    SELECT fecha, valor_apertura, valor_maximo, valor_minimo, valor_cierre, volumen
    FROM historico_nasdaq 
    ORDER BY fecha DESC 
    LIMIT 10
""")
datos_hist = cursor.fetchall()

if datos_hist:
    df_hist = pd.DataFrame(
        datos_hist,
        columns=['Fecha', 'Apertura', 'Máximo', 'Mínimo', 'Cierre', 'Volumen']
    )
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ No hay registros. Ejecuta `python actualizar.py`")


# ═══════════════════════════════════════════════════════════
# SECCIÓN 4: PORTAFOLIO DIARIO
# ═══════════════════════════════════════════════════════════
st.header("💼 portafolio (últimos 10)")

cursor.execute("""
    SELECT fecha, valor_nasdaq, variacion_nasdaq, 
           valor_portafolio, variacion_portafolio, ganancia_perdida
    FROM portafolio_diario 
    ORDER BY fecha DESC 
    LIMIT 10
""")
datos_port = cursor.fetchall()

if datos_port:
    df_port = pd.DataFrame(
        datos_port,
        columns=['Fecha', 'NASDAQ', 'Var. NASDAQ (%)', 
                 'Valor Portafolio', 'Var. Portafolio (%)', 'Ganancia/Pérdida']
    )
    st.dataframe(df_port, use_container_width=True, hide_index=True)
    
    ultimo = datos_port[0]
    st.markdown("### 📌 Último día registrado")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valor Portafolio", f"${ultimo[3]:,.2f}", 
                  delta=f"{ultimo[4]:.2f}%")
    with col2:
        st.metric("Ganancia/Pérdida", f"${ultimo[5]:,.2f}")
    with col3:
        st.metric("NASDAQ", f"{ultimo[1]:,.2f}", 
                  delta=f"{ultimo[2]:.2f}%")
else:
    st.warning("⚠️ No hay registros. Ejecuta `python calculo.py`")


cursor.close()
conn.close()

st.divider()
st.caption("RiTech SAS © 2026")