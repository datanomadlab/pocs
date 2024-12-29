-- Primero, eliminar la tabla si existe
DROP TABLE IF EXISTS records;

-- Tabla para MySQL
CREATE TABLE IF NOT EXISTS transformed_records (
    id INT PRIMARY KEY AUTO_INCREMENT, -- Identificador único
    name VARCHAR(100) NOT NULL,        -- Nombre del usuario
    email VARCHAR(100) NOT NULL,       -- Correo electrónico
    address TEXT,                      -- Dirección
    processed_date TIMESTAMP           -- Fecha procesada (rellenada en el ETL)
);

