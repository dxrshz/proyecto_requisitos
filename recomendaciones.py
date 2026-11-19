import pandas as pd

def impacto_portafolio(var_nasdaq):
    return var_nasdaq * 2 if var_nasdaq >= 0 else var_nasdaq * 2


def _rsi(cierres, periodo=14):
    delta = cierres.diff()
    ganancia = delta.clip(lower=0).rolling(periodo).mean()
    perdida = (-delta.clip(upper=0)).rolling(periodo).mean()
    rs = ganancia / perdida
    return 100 - 100 / (1 + rs)


def obtener_recomendacion(cursor):
    # Histórico de cierres
    cursor.execute("""
        SELECT fecha, valor_cierre FROM historico_nasdaq ORDER BY fecha ASC
    """)
    filas = cursor.fetchall()
    if len(filas) < 12:
        return None  # No hay datos suficientes

    df = pd.DataFrame(filas, columns=["fecha", "cierre"])
    df["cierre"] = pd.to_numeric(df["cierre"])
    c = df["cierre"]
    retornos = c.pct_change()

    # Rentabilidad del portafolio y umbrales
    cursor.execute("""
        SELECT valor_portafolio FROM portafolio_diario ORDER BY fecha ASC
    """)
    vp = [float(f[0]) for f in cursor.fetchall()]
    cursor.execute("""
        SELECT umbral_alerta_perdida, umbral_alerta_ganancia
        FROM configuracion ORDER BY id LIMIT 1
    """)
    u = cursor.fetchone()
    if u is None or not vp:
        return None
    umbral_p = float(u[0]) if u[0] is not None else -5.0
    umbral_g = float(u[1]) if u[1] is not None else 10.0
    rentab = (vp[-1] / vp[0] - 1) * 100 if len(vp) > 1 else 0.0

    señales = []   # (nombre, puntaje, explicación), formato original
    senales_ui = []  # Identificadores y valores para traducir en la interfaz

    def agregar_senal(nombre, puntaje, descripcion, nombre_id, descripcion_id, **variables):
        señales.append((nombre, puntaje, descripcion))
        senales_ui.append({
            "nombre_id": nombre_id,
            "puntaje": puntaje,
            "descripcion_id": descripcion_id,
            "variables": variables,
        })

    # 1. Tendencia
    sma20, sma50 = c.rolling(20).mean().iloc[-1], c.rolling(50).mean().iloc[-1]
    if pd.notna(sma20) and pd.notna(sma50) and sma20 > sma50:
        agregar_senal("Tendencia", +1, "SMA20 por encima de SMA50: tendencia alcista.", "signal_trend_name", "signal_trend_up")
    elif pd.notna(sma20) and pd.notna(sma50):
        agregar_senal("Tendencia", -1, "SMA20 por debajo de SMA50: tendencia bajista.", "signal_trend_name", "signal_trend_down")

    # 2. Momentum 5 días
    mom = (c.iloc[-1] / c.iloc[-6] - 1) * 100
    p = 1 if mom > 1 else -1 if mom < -1 else 0
    agregar_senal("Momentum 5d", p, f"El NASDAQ cambió {mom:+.2f}% en 5 días.", "signal_momentum_name", "signal_momentum", value=mom)

    # 3. RSI
    rsi = _rsi(c).iloc[-1]
    if rsi > 70:
        agregar_senal("RSI", -1, f"RSI {rsi:.0f}: sobrecompra, posible corrección.", "signal_rsi_name", "signal_rsi_high", value=rsi)
    elif rsi < 30:
        agregar_senal("RSI", +1, f"RSI {rsi:.0f}: sobreventa, posible rebote.", "signal_rsi_name", "signal_rsi_low", value=rsi)
    else:
        agregar_senal("RSI", 0, f"RSI {rsi:.0f}: zona neutral.", "signal_rsi_name", "signal_rsi_neutral", value=rsi)

    # 4. Volatilidad
    vol = retornos.tail(20).std() * 100
    if vol > 2:
        agregar_senal("Volatilidad", -1, f"Volatilidad diaria {vol:.2f}%: riesgo alto.", "signal_volatility_name", "signal_volatility_high", value=vol)
    else:
        agregar_senal("Volatilidad", 0, f"Volatilidad diaria {vol:.2f}%: controlada.", "signal_volatility_name", "signal_volatility_low", value=vol)

    # 5. Drawdown
    dd = (c.iloc[-1] / c.tail(60).max() - 1) * 100
    if dd < -8:
        agregar_senal("Drawdown", -1, f"{dd:.1f}% bajo el máximo de 60 días.", "signal_drawdown_name", "signal_drawdown_low", value=dd)
    else:
        agregar_senal("Drawdown", 0, f"{dd:.1f}% respecto al máximo de 60 días.", "signal_drawdown_name", "signal_drawdown_normal", value=dd)

    # Puntaje final
    total = sum(s[1] for s in señales)
    if rentab >= umbral_g:
        accion = "TOMAR UTILIDADES"
        detalle = f"La rentabilidad ({rentab:.2f}%) alcanzó el umbral de ganancia ({umbral_g}%)."
        accion_id, detalle_id = "action_take_profit", "recommendation_gain_threshold"
        detalle_vars = {"return_pct": rentab, "threshold": umbral_g}
    elif rentab <= umbral_p:
        accion = "REDUCIR EXPOSICIÓN"
        detalle = f"La rentabilidad ({rentab:.2f}%) llegó al umbral de pérdida ({umbral_p}%)."
        accion_id, detalle_id = "action_reduce", "recommendation_loss_threshold"
        detalle_vars = {"return_pct": rentab, "threshold": umbral_p}
    elif total >= 3:
        accion, detalle = "AUMENTAR EXPOSICIÓN", "Las señales son mayoritariamente favorables."
        accion_id, detalle_id, detalle_vars = "action_increase", "recommendation_positive", {}
    elif total <= -2:
        accion, detalle = "REDUCIR EXPOSICIÓN", "Las señales son mayoritariamente desfavorables."
        accion_id, detalle_id, detalle_vars = "action_reduce", "recommendation_negative", {}
    else:
        accion, detalle = "MANTENER", "Señales mixtas: no hay motivo claro para cambiar."
        accion_id, detalle_id, detalle_vars = "action_hold", "recommendation_mixed", {}

    # Escenarios
    escenarios = [{"NASDAQ (%)": v, "Portafolio (%)": impacto_portafolio(v)}
    for v in (-5, -2, -1, 1, 2, 5)]

    return {"accion": accion, "detalle": detalle, "puntaje": total,
            "señales": señales, "escenarios": escenarios, "rentabilidad": rentab,
            # Campos extra solo para visualización bilingüe (sin alterar el algoritmo).
            "accion_id": accion_id, "detalle_id": detalle_id,
            "detalle_vars": detalle_vars, "senales_ui": senales_ui}