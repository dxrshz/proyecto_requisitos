-- Crear base de datos (ejecutar por separado en pgAdmin)
-- CREATE DATABASE ritech_db;
-- Luego conectar a ritech_db y ejecutar el resto.

CREATE TABLE IF NOT EXISTS configuracion (
    id SERIAL PRIMARY KEY,
    capital_inicial NUMERIC(15,2) NOT NULL,
    moneda VARCHAR(3) DEFAULT 'USD',
    umbral_alerta_perdida NUMERIC(5,2) DEFAULT -5,
    umbral_alerta_ganancia NUMERIC(5,2) DEFAULT 10,
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historico_nasdaq (
    id SERIAL PRIMARY KEY,
    fecha DATE UNIQUE NOT NULL,
    valor_apertura NUMERIC(15,4),
    valor_maximo NUMERIC(15,4),
    valor_minimo NUMERIC(15,4),
    valor_cierre NUMERIC(15,4),
    volumen BIGINT
);

CREATE TABLE IF NOT EXISTS portafolio_diario (
    id SERIAL PRIMARY KEY,
    fecha DATE UNIQUE NOT NULL,
    valor_nasdaq NUMERIC(15,4),
    variacion_nasdaq NUMERIC(10,4),
    valor_portafolio NUMERIC(15,2),
    variacion_portafolio NUMERIC(10,4),
    ganancia_perdida NUMERIC(15,2)
);