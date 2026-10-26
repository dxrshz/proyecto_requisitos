"""
actualizar.py
-------------
Pipeline de actualizacion en UN solo paso:

    1. Descarga el historico del NASDAQ (api.py)  -> tabla historico_nasdaq
    2. Recalcula el portafolio (calculo.py)       -> tabla portafolio_diario

Uso:
    python actualizar.py                          # desde consola
    from actualizar import ejecutar_pipeline      # desde app.py (boton)
"""
import sys
import pandas as pd
from api import obtener_datos_nasdaq
from calculo import calcular_portafolio
from db import conectar

# recomendaciones.py usa SMA50 y maximo de 60 sesiones.
# 200 dias calendario ~ 140 sesiones bursatiles: de sobra para ambos.
DIAS_HISTORICO = 200

# DO UPDATE (y no DO NOTHING): si la vela del dia se bajo con el mercado
# abierto, la siguiente actualizacion la corrige en vez de dejarla incompleta.
SQL_UPSERT = """
    INSERT INTO historico_nasdaq
        (fecha, valor_apertura, valor_maximo, valor_minimo, valor_cierre, volumen)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (fecha) DO UPDATE SET
        valor_apertura = EXCLUDED.valor_apertura,
        valor_maximo   = EXCLUDED.valor_maximo,
        valor_minimo   = EXCLUDED.valor_minimo,
        valor_cierre   = EXCLUDED.valor_cierre,
        volumen        = EXCLUDED.volumen
"""


def guardar_datos_nasdaq(dias=DIAS_HISTORICO):
    """Descarga el NASDAQ y lo guarda (upsert) en una sola transaccion.
    Devuelve el numero de dias procesados. Lanza RuntimeError si no hay datos."""
    datos = obtener_datos_nasdaq(dias)
    if datos is None or datos.empty:
        raise RuntimeError(
            "Yahoo Finance no devolvio datos del NASDAQ (revisa la conexion a internet)."
        )

    datos = datos.dropna(subset=["Open", "High", "Low", "Close"])
    filas = [
        (
            fecha.strftime("%Y-%m-%d"),
            round(float(f["Open"]), 4),
            round(float(f["High"]), 4),
            round(float(f["Low"]), 4),
            round(float(f["Close"]), 4),
            0 if pd.isna(f["Volume"]) else int(f["Volume"]),
        )
        for fecha, f in datos.iterrows()
    ]

    conn = conectar()
    try:
        with conn:  # commit si todo sale bien, rollback si algo falla
            with conn.cursor() as cur:
                cur.executemany(SQL_UPSERT, filas)
    finally:
        conn.close()
    return len(filas)


def ejecutar_pipeline(dias=DIAS_HISTORICO, verbose=False):
    """Descarga datos -> guarda en BD -> recalcula portafolio.
    Lanza una excepcion con mensaje claro si algun paso falla."""
    log = print if verbose else (lambda *a, **k: None)

    log("[1/2] Descargando NASDAQ y guardando en la base de datos...")
    n_datos = guardar_datos_nasdaq(dias)
    log(f"      {n_datos} dias procesados en historico_nasdaq")

    log("[2/2] Recalculando portafolio...")
    resultado = calcular_portafolio()
    log(f"      {resultado['dias_calculados']} dias calculados en portafolio_diario")

    return {"dias_descargados": n_datos, **resultado}


if __name__ == "__main__":
    try:
        res = ejecutar_pipeline(verbose=True)
        print(f"Listo. Ultima fecha: {res['ultima_fecha']}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
