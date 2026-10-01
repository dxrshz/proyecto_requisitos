from db import conectar
from api import obtener_datos_nasdaq
from datetime import datetime


def guardar_datos_nasdaq(dias=30):
    """
    1. Trae los datos del NASDAQ desde yfinance.
    2. Los guarda en la tabla historico_nasdaq.
    """
    print("🚀 Iniciando actualización...\n")
    
    datos = obtener_datos_nasdaq(dias)
    
    if datos.empty:
        print("❌ No se obtuvieron datos del NASDAQ")
        return
    
    print(f"📥 {len(datos)} días recibidos de la API")
    
    conn = conectar()
    cursor = conn.cursor()
    
    insertados = 0
    for fecha, fila in datos.iterrows():
        fecha_str = fecha.strftime('%Y-%m-%d')
        
        cursor.execute("""
            INSERT INTO historico_nasdaq 
                (fecha, valor_apertura, valor_maximo, valor_minimo, valor_cierre, volumen)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fecha) DO NOTHING
        """, (
            fecha_str,
            round(fila['Open'], 4),
            round(fila['High'], 4),
            round(fila['Low'], 4),
            round(fila['Close'], 4),
            int(fila['Volume'])
        ))
        insertados += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ {insertados} días procesados en historico_nasdaq")
    print("\n🎉 Actualización completada")


if __name__ == "__main__":
    guardar_datos_nasdaq(30)