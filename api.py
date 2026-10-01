

import yfinance as yf
from datetime import datetime, timedelta

def obtener_datos_nasdaq(dias=30):
    ticker = yf.Ticker("^IXIC")
    fin = datetime.now()
    inicio = fin - timedelta(days=dias)
    datos = ticker.history(start=inicio, end=fin)
    return datos


# Prueba rápida
if __name__ == "__main__":
    try:
        datos = obtener_datos_nasdaq(7)
        
        if datos.empty:
            print("❌ No se obtuvieron datos")
        else:
            print(f"✅ {len(datos)} días recibidos:\n")
            for fecha, fila in datos.iterrows():
                print(f"   {fecha.strftime('%Y-%m-%d')}: cierre = {fila['Close']:.2f}")
    except Exception as e:
        print(f"❌ Error: {e}")