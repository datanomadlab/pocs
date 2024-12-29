-- Primero, eliminar la tabla si existe
DROP TABLE IF EXISTS records;

-- Crear tabla en PostgreSQL
CREATE TABLE IF NOT EXISTS records (
    id SERIAL PRIMARY KEY,          -- Identificador único
    name VARCHAR(100) NOT NULL,     -- Nombre del usuario
    email VARCHAR(100) NOT NULL,    -- Correo electrónico
    address TEXT,                   -- Dirección
    created_at TIMESTAMP NOT NULL,  -- Fecha de creación
    updated_at TIMESTAMP            -- Fecha de actualización
);
