"""Verifica conexión/esquema sin modificar información ni mostrar credenciales."""
from db import conectar

TABLAS = ("configuracion", "historico_nasdaq", "portafolio_diario", "ritech_usuarios")


def main():
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            print("Base conectada:", cur.fetchone()[0])
            for tabla in TABLAS:
                cur.execute("SELECT to_regclass(%s)", (f"public.{tabla}",))
                print(("OK: " if cur.fetchone()[0] else "FALTA: ") + tabla)
            for tabla in ("configuracion", "portafolio_diario"):
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = %s
                          AND column_name = 'usuario_id'
                    )
                """, (tabla,))
                print(f"usuario_id en {tabla}:", "OK" if cur.fetchone()[0] else "FALTA")
            cur.execute("""
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'configuracion'
                  AND column_name = 'fecha_inicio'
                )
            """)
            print("fecha_inicio en configuracion:", "OK" if cur.fetchone()[0] else "FALTA")
            for indice in ("uq_ritech_config_usuario", "uq_ritech_portafolio_usuario_fecha"):
                cur.execute("SELECT to_regclass(%s)", ("public." + indice,))
                print(f"Índice {indice}:", "OK" if cur.fetchone()[0] else "FALTA")
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint con
                    JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = con.conkey[1]
                    WHERE con.conrelid = 'portafolio_diario'::regclass
                    AND con.contype = 'u' AND array_length(con.conkey, 1) = 1
                    AND a.attname = 'fecha'
                )
            """)
            print("Restricción anterior UNIQUE(fecha) en portafolio:",
                  "PENDIENTE DE MIGRACIÓN" if cur.fetchone()[0] else "ELIMINADA")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("No se pudo comprobar la base de datos:", exc)
        raise SystemExit(1)
