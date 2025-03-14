-- Habilitar extensiones avanzadas
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Ejemplo 1: pgvector para búsqueda vectorial
CREATE TABLE IF NOT EXISTS items (
  id serial PRIMARY KEY,
  embedding vector(3),
  description text
);
INSERT INTO items (embedding, description) VALUES (ARRAY[0.1, 0.2, 0.3], 'Primer item');

-- Ejemplo 2: PostGIS para datos geoespaciales
CREATE TABLE IF NOT EXISTS locations (
  id serial PRIMARY KEY,
  name text,
  geom geometry(Point,4326)
);
INSERT INTO locations (name, geom)
  VALUES ('New York', ST_SetSRID(ST_MakePoint(-74.005941, 40.712784),4326));

-- Ejemplo 3: pg_trgm para búsqueda de texto
CREATE TABLE IF NOT EXISTS products (
  id serial PRIMARY KEY,
  name text
);
INSERT INTO products (name) VALUES ('Apple iPhone');

-- (Ejemplo 4: pg_stat_statements se usa para monitoreo, no requiere tabla)
