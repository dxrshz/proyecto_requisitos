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
    umbral_p, umbral_g = float(u[0]), float(u[1])
    rentab = (vp[-1] / vp[0] - 1) * 100 if len(vp) > 1 else 0.0

    señales = []   # (nombre, puntaje, explicación)

    # 1. Tendencia
    sma20, sma50 = c.rolling(20).mean().iloc[-1], c.rolling(50).mean().iloc[-1]
    if sma20 > sma50:
        señales.append(("Tendencia", +1, "SMA20 por encima de SMA50: tendencia alcista."))
    else:
        señales.append(("Tendencia", -1, "SMA20 por debajo de SMA50: tendencia bajista."))

    # 2. Momentum 5 días
    mom = (c.iloc[-1] / c.iloc[-6] - 1) * 100
    p = 1 if mom > 1 else -1 if mom < -1 else 0
    señales.append(("Momentum 5d", p, f"El NASDAQ cambió {mom:+.2f}% en 5 días."))

    # 3. RSI
    rsi = _rsi(c).iloc[-1]
    if rsi > 70:
        señales.append(("RSI", -1, f"RSI {rsi:.0f}: sobrecompra, posible corrección."))
    elif rsi < 30:
        señales.append(("RSI", +1, f"RSI {rsi:.0f}: sobreventa, posible rebote."))
    else:
        señales.append(("RSI", 0, f"RSI {rsi:.0f}: zona neutral."))

    # 4. Volatilidad
    vol = retornos.tail(20).std() * 100
    if vol > 2:
        señales.append(("Volatilidad", -1, f"Volatilidad diaria {vol:.2f}%: riesgo alto."))
    else:
        señales.append(("Volatilidad", 0, f"Volatilidad diaria {vol:.2f}%: controlada."))

    # 5. Drawdown
    dd = (c.iloc[-1] / c.tail(60).max() - 1) * 100
    if dd < -8:
        señales.append(("Drawdown", -1, f"{dd:.1f}% bajo el máximo de 60 días."))
    else:
        señales.append(("Drawdown", 0, f"{dd:.1f}% respecto al máximo de 60 días."))

    # Puntaje final
    total = sum(s[1] for s in señales)
    if rentab >= umbral_g:
        accion = "TOMAR UTILIDADES"
        detalle = f"La rentabilidad ({rentab:.2f}%) alcanzó el umbral de ganancia ({umbral_g}%)."
    elif rentab <= umbral_p:
        accion = "REDUCIR EXPOSICIÓN"
        detalle = f"La rentabilidad ({rentab:.2f}%) llegó al umbral de pérdida ({umbral_p}%)."
    elif total >= 3:
        accion, detalle = "AUMENTAR EXPOSICIÓN", "Las señales son mayoritariamente favorables."
    elif total <= -2:
        accion, detalle = "REDUCIR EXPOSICIÓN", "Las señales son mayoritariamente desfavorables."
    else:
        accion, detalle = "MANTENER", "Señales mixtas: no hay motivo claro para cambiar."

    # Escenarios
    escenarios = [{"NASDAQ (%)": v, "Portafolio (%)": impacto_portafolio(v)}
    for v in (-5, -2, -1, 1, 2, 5)]

    return {"accion": accion, "detalle": detalle, "puntaje": total,
            "señales": señales, "escenarios": escenarios, "rentabilidad": rentab}