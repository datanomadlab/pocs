import pandas as pd
from sentence_transformers import SentenceTransformer
import psycopg2
import numpy as np
import json
from tqdm import tqdm

def clean_price(price_str):
    if pd.isna(price_str):
        return None
    # Eliminar el símbolo de rupia y las comas
    price_str = str(price_str).replace('₹', '').replace(',', '')
    try:
        return float(price_str)
    except ValueError:
        return None

def clean_number(num_str):
    if pd.isna(num_str):
        return None
    # Eliminar las comas
    num_str = str(num_str).replace(',', '')
    try:
        return int(num_str)
    except ValueError:
        return None

def clean_rating(rating_str):
    if pd.isna(rating_str):
        return None
    try:
        # Si es un número, convertirlo a float
        return float(rating_str)
    except ValueError:
        # Si no es un número, retornar None
        return None

# Crear esquema: tabla y extensión pgvector
def create_schema(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("DROP TABLE IF EXISTS products;")
        cur.execute("""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name TEXT,
                main_category TEXT,
                sub_category TEXT,
                image TEXT,
                link TEXT,
                ratings FLOAT,
                no_of_ratings INTEGER,
                discount_price FLOAT,
                actual_price FLOAT,
                embedding VECTOR(384)
            );
        """)
        cur.execute("""
            CREATE INDEX idx_products_embedding
            ON products USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)
    conn.commit()

# Insertar datos del dataset en lotes y generar embeddings a partir de campos textuales
def insert_data(conn, df, model, batch_size=1000):
    with conn.cursor() as cur:
        insert_query = """
            INSERT INTO products 
            (name, main_category, sub_category, image, link, ratings, no_of_ratings, discount_price, actual_price, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
        """
        records = []
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Procesando registros"):
            name = row['name']
            main_category = row['main_category']
            sub_category = row['sub_category']
            image = row['image']
            link = row['link']
            ratings = clean_rating(row['ratings'])
            no_of_ratings = clean_number(row['no_of_ratings'])
            discount_price = clean_price(row['discount_price'])
            actual_price = clean_price(row['actual_price'])
            
            # Generar texto para embedding a partir de campos clave
            text_to_embed = f"{name} - {main_category} - {sub_category}"
            embedding = model.encode(text_to_embed).tolist()
            
            records.append((name, main_category, sub_category, image, link, ratings, no_of_ratings, discount_price, actual_price, embedding))
            
            if len(records) == batch_size:
                cur.executemany(insert_query, records)
                conn.commit()
                records = []
        if records:
            cur.executemany(insert_query, records)
            conn.commit()

# Consulta de similitud: búsqueda por vector a partir de una consulta textual
def query_similarity(conn, model, query_text, top_k=10):
    query_embedding = model.encode(query_text).tolist()
    with conn.cursor() as cur:
        sql_query = """
            SELECT id, name, main_category, sub_category, embedding <=> %s::vector AS distance
            FROM products
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        cur.execute(sql_query, (query_embedding, query_embedding, top_k))
        results = cur.fetchall()
    return results

def main():
    # Conexión a PostgreSQL (ajustar parámetros según corresponda)
    conn = psycopg2.connect(
        host="localhost",
        database="mydatabase",
        user="myuser",
        password="mysecretpassword",
        port=5432
    )

    try:
        # Crear esquema de la tabla y extensión pgvector
        create_schema(conn)
        
        # Cargar dataset desde archivo CSV (asegúrate de que el archivo 'dataset.csv' esté en el directorio de trabajo)
        df = pd.read_csv("dataset.csv")
        
        # Inicializar modelo de embeddings (modelo con salida de dimensión 384)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Insertar datos del dataset en la base de datos
        insert_data(conn, df, model)
        
        # Realizar una consulta de similitud con un texto de ejemplo
        query_text = "Busco productos de tecnología y gadgets innovadores"
        results = query_similarity(conn, model, query_text)
        
        print("Top resultados de similitud tecnología:")
        for row in results:
            print(row)
            
        query_text = "Quiero libros de ciencia ficción"
        results = query_similarity(conn, model, query_text)
        
        print("Top resultados de similitud libros:")
        for row in results:
            print(row)    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
