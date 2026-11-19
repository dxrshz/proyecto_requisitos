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


def ejecutar_pipeline(usuario_id, dias=DIAS_HISTORICO, verbose=False):
    """Actualiza NASDAQ (común), y recalcula únicamente la cuenta autenticada."""
    if not isinstance(usuario_id, int) or isinstance(usuario_id, bool) or usuario_id <= 0:
        raise ValueError("Debes iniciar sesión para actualizar tu portafolio.")
    log = print if verbose else (lambda *args, **kwargs: None)

    # Comprobación de identidad antes de descargar o escribir datos.
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM ritech_usuarios WHERE id = %s", (usuario_id,))
            if cur.fetchone() is None:
                raise ValueError("La cuenta no existe.")
    finally:
        conn.close()

    log("[1/2] Descargando NASDAQ y guardando datos del mercado...")
    n_datos = guardar_datos_nasdaq(dias)
    log(f"      {n_datos} días guardados en historico_nasdaq")

    # La primera vez aún no hay capital configurado: no se crea uno global.
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM configuracion WHERE usuario_id = %s", (usuario_id,))
            configurado = cur.fetchone() is not None
            cur.execute("SELECT MAX(fecha) FROM historico_nasdaq")
            fecha_mercado = cur.fetchone()[0]
    finally:
        conn.close()
    if not configurado:
        log("[2/2] Configura tu capital personal para activar el cálculo.")
        return {"dias_descargados": n_datos, "dias_calculados": 0,
                "ultima_fecha": str(fecha_mercado) if fecha_mercado else "—",
                "sin_configuracion": True}

    log(f"[2/2] Recalculando exclusivamente la cuenta #{usuario_id}...")
    resultado = calcular_portafolio(usuario_id)
    return {"dias_descargados": n_datos, **resultado, "sin_configuracion": False}


if __name__ == "__main__":
    # Desde la consola se actualizan únicamente cotizaciones públicas.
    # Nunca se recalcúla el portafolio privado de otra cuenta sin su sesión.
    try:
        total = guardar_datos_nasdaq()
        print(f"Datos comunes del NASDAQ actualizados: {total} sesiones.")
        print("Los portafolios personales se recalculan dentro de RiTech tras iniciar sesión.")
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
