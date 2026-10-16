"""
alertas.py
----------
Alertas de umbrales de perdida y ganancia del portafolio (NASDAQ).

Se usa desde app.py:
    from alertas import obtener_alertas
"""

# Valores por defecto (los mismos de init.sql y de app.py)
UMBRAL_PERDIDA_DEFECTO = -5.0
UMBRAL_GANANCIA_DEFECTO = 10.0


def evaluar_alertas(variacion_dia, rentabilidad, umbral_perdida, umbral_ganancia):
    """
    Compara dos medidas del portafolio contra los umbrales y retorna
    la lista de alertas que se activaron (lista vacia si no hay ninguna).

    - variacion_dia: variacion (%) del ultimo dia registrado.
    - rentabilidad:  ganancia o perdida acumulada (%) respecto al capital inicial.
    - umbral_perdida:  numero negativo, por ejemplo -5  (alerta si baja a -5% o menos).
    - umbral_ganancia: numero positivo, por ejemplo 10  (alerta si sube a +10% o mas).
    """
    medidas = [
        ("Variación del último día", variacion_dia),
        ("Rentabilidad acumulada", rentabilidad),
    ]

    alertas = []
    for nombre, valor in medidas:
        if valor < 0 and valor <= umbral_perdida:
            alertas.append({
                "tipo": "perdida",
                "mensaje": f"{nombre}: {valor:+.2f}% (llegó al umbral de pérdida de {umbral_perdida:.2f}%)",
            })
        elif valor > 0 and valor >= umbral_ganancia:
            alertas.append({
                "tipo": "ganancia",
                "mensaje": f"{nombre}: {valor:+.2f}% (llegó al umbral de ganancia de {umbral_ganancia:.2f}%)",
            })
    return alertas


def obtener_alertas(cursor):
    """
    Lee de la base de datos los umbrales y el ultimo dia del portafolio,
    y retorna un diccionario con las medidas y las alertas activas.
    Retorna None si todavia no hay configuracion o no hay datos calculados.
    """
    cursor.execute("""
        SELECT umbral_alerta_perdida, umbral_alerta_ganancia
        FROM configuracion
        ORDER BY id LIMIT 1
    """)
    umbrales = cursor.fetchone()

    cursor.execute("""
        SELECT fecha, variacion_portafolio, valor_portafolio, ganancia_perdida
        FROM portafolio_diario
        ORDER BY fecha DESC LIMIT 1
    """)
    ultimo = cursor.fetchone()

    if umbrales is None or ultimo is None:
        return None

    umbral_perdida = float(umbrales[0]) if umbrales[0] is not None else UMBRAL_PERDIDA_DEFECTO
    umbral_ganancia = float(umbrales[1]) if umbrales[1] is not None else UMBRAL_GANANCIA_DEFECTO

    fecha, variacion_dia, valor_portafolio, ganancia = ultimo
    variacion_dia = float(variacion_dia)

    # Capital con el que se calculo el portafolio = valor actual - ganancia
    capital_base = float(valor_portafolio) - float(ganancia)
    rentabilidad = (float(ganancia) / capital_base * 100) if capital_base else 0.0

    return {
        "fecha": fecha,
        "variacion_dia": variacion_dia,
        "rentabilidad": rentabilidad,
        "umbral_perdida": umbral_perdida,
        "umbral_ganancia": umbral_ganancia,
        "alertas": evaluar_alertas(variacion_dia, rentabilidad, umbral_perdida, umbral_ganancia),
    }
