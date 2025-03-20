-- Habilitar la extensión vector
CREATE EXTENSION IF NOT EXISTS vector;

-- Configurar pg_hba.conf para permitir conexiones desde cualquier host
ALTER SYSTEM SET listen_addresses = '*';
ALTER SYSTEM SET password_encryption = 'md5';

-- Otorgar todos los privilegios al usuario existente
GRANT ALL PRIVILEGES ON DATABASE mydatabase TO myuser;

-- Crear tabla para almacenar datos y vectores
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    descripcion TEXT,
    metadata JSONB,  -- Para almacenar datos contextuales adicionales
    embedding VECTOR(1536)  -- Dimensión según el modelo utilizado (por ejemplo, 1536 para ciertos modelos de OpenAI)
);

-- Crear un índice para optimizar la búsqueda por similitud (usando operaciones de coseno)
CREATE INDEX idx_embedding ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
