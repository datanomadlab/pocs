-- Conectarse a la base stage
\connect stage;

-- 1. Crear un server que apunte a la base 'raw'
CREATE SERVER raw_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host 'localhost', dbname 'raw', port '5432');

-- 2. Crear un user mapping para el usuario con el que se conecta dbt (e.g. 'admin')
CREATE USER MAPPING FOR admin
  SERVER raw_server
  OPTIONS (user 'admin', password 'admin');

-- 3. (Opcional) Crear un schema en stage para alojar la foreign table
CREATE SCHEMA IF NOT EXISTS foreign_raw;

-- 4. Crear la foreign table dentro de stage que apunta a raw.public.not_clean
CREATE FOREIGN TABLE foreign_raw.not_clean (
    id INT,
    nombre TEXT,
    apellido TEXT,
    correo TEXT,
    telefono TEXT,
    fecha_registro DATE,
    monto NUMERIC(10, 2),
    categoria TEXT,
    descripcion TEXT,
    flag BOOLEAN
)
SERVER raw_server
OPTIONS (schema_name 'public', table_name 'not_clean');
