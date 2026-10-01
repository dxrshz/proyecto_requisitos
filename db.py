import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def conectar():
    """Retorna una conexión a la base de datos PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )


# Prueba rápida de conexión
if __name__ == "__main__":
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print("Conexión exitosa a PostgreSQL")
        print(f"   Versión: {version[0]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")