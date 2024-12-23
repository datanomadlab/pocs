-- 01-init-raw.sql

-- 1. Crear la BBDD raw
CREATE DATABASE raw;

-- 2. Conectarnos a la base de datos raw
\connect raw;

-- 3. Crear la tabla not_clean con 10 campos
CREATE TABLE not_clean (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    apellido TEXT,
    correo TEXT,
    telefono TEXT,
    fecha_registro DATE,
    monto NUMERIC(10, 2),
    categoria TEXT,
    descripcion TEXT,
    flag BOOLEAN
);

-- 4. Insertar data dummy
INSERT INTO not_clean (nombre, apellido, correo, telefono, fecha_registro, monto, categoria, descripcion, flag)
VALUES
('Juan', 'Perez', 'juan.perez@example.com', '1234567890', '2023-01-15', 100.00, 'A', 'Cliente inicial', TRUE),
('Maria', 'Gomez', 'maria.gomez@example.com', '0987654321', '2024-02-20', 200.50, 'B', 'Cliente regular', FALSE),
('Pedro', 'Lopez', 'pedro.lopez@example.com', '5555555555', '2022-05-01', 350.75, 'A', 'Cliente VIP', TRUE),
('Ana', 'Martinez', 'ana.martinez@example.com', '1111111111', '2023-11-30', 20.00, 'C', 'Lead nuevo', FALSE),
('Carlos', 'Rodriguez', 'carlos.rodriguez@example.com', '3333333333', '2024-01-01', 500.00, 'B', 'Cliente eventual', TRUE);
