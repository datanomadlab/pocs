import duckdb
import sqlite3

INPUT_FILE = "./data/inputpoc1.parquet"
DB_FILE = "./data/results.db"

def save_to_database(input_file, db_file):
    # Conectar a DuckDB y procesar datos
    conn_duck = duckdb.connect()
    conn_duck.execute(f"""
        SELECT 
            category, 
            COUNT(*) AS total_rows, 
            AVG(value) AS avg_value, 
            SUM(value) AS total_value 
        FROM read_parquet('{input_file}')
        GROUP BY category
    """)
    results = conn_duck.fetchdf()

    # Conectar a SQLite
    conn_sqlite = sqlite3.connect(db_file)
    cursor = conn_sqlite.cursor()

    # Crear tabla en SQLite
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_results (
            category TEXT,
            total_rows INTEGER,
            avg_value REAL,
            total_value REAL
        )
    """)

    # Insertar datos
    for _, row in results.iterrows():
        cursor.execute("""
            INSERT INTO analytics_results (category, total_rows, avg_value, total_value)
            VALUES (?, ?, ?, ?)
        """, (row['category'], row['total_rows'], row['avg_value'], row['total_value']))

    conn_sqlite.commit()
    conn_sqlite.close()
    print(f"Resultados guardados en la base de datos: {db_file}")

save_to_database(INPUT_FILE, DB_FILE)
