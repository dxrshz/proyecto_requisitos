"""Cálculo de portafolio privado por cuenta; nunca reemplaza las filas de otro usuario."""

from db import conectar

FACTOR_SUBIDA = 2.0
FACTOR_BAJADA = 2.0


def variacion_portafolio(var_nasdaq):
    """Conserva la regla de negocio definida en el simulador original."""
    return var_nasdaq * (FACTOR_SUBIDA if var_nasdaq > 0 else FACTOR_BAJADA)


def calcular_portafolio(usuario_id, verbose=False):
    """Recalcula SOLO un portafolio, conservando otros y haciendo rollback si falla."""
    if not isinstance(usuario_id, int) or isinstance(usuario_id, bool) or usuario_id <= 0:
        raise ValueError("Es obligatorio un ID de usuario autenticado para recalcular.")

    conn = conectar()
    try:
        with conn:
            with conn.cursor() as cur:
                # Evita dos recálculos simultáneos para esta misma cuenta.
                cur.execute("SELECT id FROM ritech_usuarios WHERE id = %s FOR UPDATE", (usuario_id,))
                if cur.fetchone() is None:
                    raise ValueError("La cuenta de usuario ya no existe.")

                cur.execute("""
                    SELECT capital_inicial, fecha_inicio FROM configuracion
                    WHERE usuario_id = %s ORDER BY id LIMIT 1
                """, (usuario_id,))
                fila = cur.fetchone()
                if fila is None:
                    raise RuntimeError("Configura tu propio capital inicial antes de calcular el portafolio.")
                capital, fecha_inicio = float(fila[0]), fila[1]

                if fecha_inicio:
                    cur.execute("""
                        SELECT fecha, valor_cierre FROM historico_nasdaq
                        WHERE fecha >= %s ORDER BY fecha ASC
                    """, (fecha_inicio,))
                else:
                    cur.execute("SELECT fecha, valor_cierre FROM historico_nasdaq ORDER BY fecha ASC")
                datos = cur.fetchall()
                if len(datos) < 2:
                    raise RuntimeError("Se necesitan al menos 2 días bursátiles desde la fecha de inversión.")

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
                    filas.append((usuario_id, fecha, cierre, round(var_n, 4),
                                  round(valor, 2), round(var_p, 4), round(ganancia, 2)))
                    anterior = cierre

                # Nunca DELETE sin WHERE usuario_id. Las filas antiguas NULL también se conservan.
                cur.execute("DELETE FROM portafolio_diario WHERE usuario_id = %s", (usuario_id,))
                cur.executemany("""
                    INSERT INTO portafolio_diario
                        (usuario_id, fecha, valor_nasdaq, variacion_nasdaq,
                         valor_portafolio, variacion_portafolio, ganancia_perdida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, filas)
    finally:
        conn.close()

    if verbose:
        print(f"Portafolio de la cuenta #{usuario_id}: {len(filas)} días (capital ${capital:,.2f})")
    return {"dias_calculados": len(filas), "ultima_fecha": str(filas[-1][1]), "capital": capital}


if __name__ == "__main__":
    print("Para proteger los portafolios, inicia sesión en RiTech y guarda "
          "tu configuración o utiliza 'Actualizar datos'.")
    raise SystemExit(1)
