from db import conectar


def calcular_portafolio():
    print("🚀 Calculando portafolio...\n")
    
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Capital inicial desde configuracion (lo pone la app)
    cursor.execute("SELECT capital_inicial FROM configuracion ORDER BY id LIMIT 1")
    resultado = cursor.fetchone()
    
    if resultado is None:
        print("⚠️ No hay configuración guardada.")
        print("   Abre la app (streamlit run app.py) y configura el capital primero.")
        conn.close()
        return
    
    capital = float(resultado[0])
    print(f"💰 Capital inicial: ${capital:,.2f}\n")
    
    # 2. Datos del NASDAQ
    cursor.execute("""
        SELECT fecha, valor_cierre 
        FROM historico_nasdaq 
        ORDER BY fecha ASC
    """)
    datos = cursor.fetchall()
    
    if len(datos) < 2:
        print("⚠️ Se necesitan al menos 2 días de datos")
        conn.close()
        return
    
    # 3. Limpiar cálculos anteriores
    cursor.execute("DELETE FROM portafolio_diario")
    
    # 4. Calcular día a día
    valor_portafolio = capital
    cierre_anterior = None
    
    for fecha, cierre in datos:
        cierre = float(cierre)
        
        if cierre_anterior is None:
            variacion_nasdaq = 0
            variacion_portafolio = 0
            ganancia = 0
        else:
            variacion_nasdaq = ((cierre - cierre_anterior) / cierre_anterior) * 100
            
            # REGLA DE NEGOCIO
            if variacion_nasdaq > 0:
                variacion_portafolio = variacion_nasdaq * 2
            else:
                variacion_portafolio = variacion_nasdaq * 1.25
            
            valor_portafolio = valor_portafolio * (1 + variacion_portafolio / 100)
            ganancia = valor_portafolio - capital
        
        cursor.execute("""
            INSERT INTO portafolio_diario 
                (fecha, valor_nasdaq, variacion_nasdaq, 
                 valor_portafolio, variacion_portafolio, ganancia_perdida)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            fecha,
            cierre,
            round(variacion_nasdaq, 4),
            round(valor_portafolio, 2),
            round(variacion_portafolio, 4),
            round(ganancia, 2)
        ))
        
        cierre_anterior = cierre
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✅ Portafolio calculado para {len(datos)} días")
    print("\n🎉 Cálculo completado")


if __name__ == "__main__":
    calcular_portafolio()