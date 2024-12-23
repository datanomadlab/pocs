-- 02-init-stage.sql

-- 1. Crear la BBDD stage
CREATE DATABASE stage;

-- 2. Conectarnos a la base de datos stage
\connect stage;

-- 3. (Opcional) Crear una tabla clean para prueba
--    Aunque dbt usualmente la creará o reemplazará, puedes dejar esto como ejemplo.
CREATE TABLE IF NOT EXISTS clean (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    apellido TEXT,
    fecha_registro DATE,
    monto NUMERIC(10, 2),
    categoria TEXT
);
