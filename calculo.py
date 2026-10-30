from db import conectar

FACTOR_SUBIDA = 2.0
FACTOR_BAJADA = 2.0


def variacion_portafolio(var_nasdaq):
    """Aplica la regla de negocio. Reutilizable desde recomendaciones.py."""
    return var_nasdaq * (FACTOR_SUBIDA if var_nasdaq > 0 else FACTOR_BAJADA)


def calcular_portafolio(verbose=False):
    """Borra y recalcula portafolio_diario en UNA transaccion: si algo falla
    no se pierden los datos anteriores. Devuelve un resumen (dict)."""
    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT capital_inicial FROM configuracion ORDER BY id LIMIT 1")
                fila = cur.fetchone()
                if fila is None:
                    raise RuntimeError(
                        "No hay configuracion guardada. Abre la app y guarda el "
                        "capital inicial en la barra lateral."
                    )
                capital = float(fila[0])

                cur.execute("SELECT fecha, valor_cierre FROM historico_nasdaq ORDER BY fecha ASC")
                datos = cur.fetchall()
                if len(datos) < 2:
                    raise RuntimeError("Se necesitan al menos 2 dias de datos del NASDAQ.")

                filas, valor, anterior = [], capital, None
                for fecha, cierre in datos:
                    cierre = float(cierre)
                    if anterior is None:
                        var_n = var_p = ganancia = 0.0
                    else:
                        var_n = (cierre - anterior) / anterior * 100
                        var_p = variacion_portafolio(var_n)
                        valor *= 1 + var_p / 100
                        ganancia = valor - capital
                    filas.append((fecha, cierre, round(var_n, 4), round(valor, 2),
                                  round(var_p, 4), round(ganancia, 2)))
                    anterior = cierre

                cur.execute("DELETE FROM portafolio_diario")
                cur.executemany("""
                    INSERT INTO portafolio_diario
                        (fecha, valor_nasdaq, variacion_nasdaq,
                         valor_portafolio, variacion_portafolio, ganancia_perdida)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, filas)
    finally:
        conn.close()

    if verbose:
        print(f"Portafolio calculado para {len(filas)} dias (capital ${capital:,.2f})")
    return {"dias_calculados": len(filas), "ultima_fecha": str(filas[-1][0]), "capital": capital}


if __name__ == "__main__":
    try:
        calcular_portafolio(verbose=True)
    except Exception as e:
        print(f"ERROR: {e}")
