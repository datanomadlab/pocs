import psycopg2
import numpy as np
import json
from tqdm import tqdm

# Conexión a la base de datos
conn = psycopg2.connect(
    host="localhost",
    database="mydatabase",
    user="myuser",
    password="mysecretpassword",
    port=5432
)

def create_schema(conn):
    with conn.cursor() as cur:
        # Crear la extensión pgvector
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        # Eliminar la tabla si existe
        cur.execute("DROP TABLE IF EXISTS items;")
        # Crear la tabla con campo vectorial
        cur.execute("""
            CREATE TABLE items (
                id SERIAL PRIMARY KEY,
                descripcion TEXT,
                metadata JSONB,
                embedding VECTOR(768)
            );
        """)
        # Crear índice para búsqueda vectorial
        cur.execute("""
            CREATE INDEX idx_items_embedding 
            ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)
    conn.commit()

def insert_data(conn, num_records=100000, batch_size=1000, dim=768):
    with conn.cursor() as cur:
        insert_query = "INSERT INTO items (descripcion, metadata, embedding) VALUES (%s, %s, %s::vector)"
        for i in tqdm(range(0, num_records, batch_size), desc="Insertando registros"):
            batch_data = []
            for j in range(batch_size):
                idx = i + j
                if idx >= num_records:
                    break
                descripcion = f"Registro {idx}: descripción de ejemplo."
                metadata = json.dumps({"categoria": "prueba", "indice": idx})
                embedding = np.random.rand(dim).tolist()  # Simulación de embedding
                batch_data.append((descripcion, metadata, embedding))
            cur.executemany(insert_query, batch_data)
            conn.commit()

def query_similarity(conn, dim=768):
    with conn.cursor() as cur:
        # Generar un vector de consulta aleatorio
        query_vector = np.random.rand(dim).tolist()
        sql_query = """
            SELECT id, descripcion, metadata, embedding <=> %s::vector AS distancia
            FROM items
            ORDER BY embedding <=> %s::vector
            LIMIT 10;
        """
        cur.execute(sql_query, (query_vector, query_vector))
        results = cur.fetchall()
    return results

def main():
    try:
        #create_schema(conn)
        #insert_data(conn)
        results = query_similarity(conn)
        print("Top 10 resultados de similitud:")
        for row in results:
            print(row)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
