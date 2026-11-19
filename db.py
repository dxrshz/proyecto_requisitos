import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), encoding="utf-8")

def conectar():
    """Abre una conexión a la base de datos configurada en .env."""
    claves = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    faltantes = [clave for clave in claves if not os.getenv(clave)]
    if faltantes:
        raise RuntimeError(
            "Faltan datos en el archivo .env: " + ", ".join(faltantes)
            + ". Copia .env.example a .env y completa los valores."
        )
    try:
        return psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            connect_timeout=5,
        )
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "PostgreSQL devolvió un mensaje con codificación incompatible. "
            "Verifica en pgAdmin que el servidor esté activo y que usuario, "
            "contraseña y base de datos coincidan con .env. Si sigue ocurriendo, "
            "revisa la codificación/región del servidor PostgreSQL."
        ) from exc
    except psycopg2.OperationalError as exc:
        raise RuntimeError(
            "No fue posible conectar con PostgreSQL. Comprueba el servidor, "
            "el puerto 5432, la base de datos, el usuario y la contraseña del .env. "
            "Puedes ejecutar: python comprobar_proyecto.py"
        ) from exc

if __name__ == "__main__":
    try:
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database()")
                print("Conexión correcta:", cur.fetchone()[0])
    except RuntimeError as exc:
        print("ERROR:", exc)
        raise SystemExit(1)