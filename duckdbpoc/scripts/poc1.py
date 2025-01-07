import duckdb

# Configuración de rutas de archivos
INPUT_FILE = "./data/input.parquet"
OUTPUT_FILE = "./data/outputpoc1.parquet"

def process_with_duckdb(input_file, output_file):
    """
    Procesa datos directamente usando DuckDB: leer, analizar y guardar resultados.
    """
    # Conexión a DuckDB
    conn = duckdb.connect()

    # Crear una tabla en memoria directamente desde el archivo Parquet
    conn.execute(f"""
        CREATE TABLE input_data AS 
        SELECT * FROM read_parquet('{input_file}')
    """)

    # Análisis de datos con SQL
    conn.execute("""
        SELECT 
            category,
            COUNT(*) AS count,
            AVG(value) AS avg_value,
            SUM(value) AS total_value
        FROM input_data
        GROUP BY category
    """)

    # Guardar resultados directamente en formato Parquet
    conn.execute(f"""
        COPY (
            SELECT *
            FROM input_data
        )
        TO '{output_file}'
        (FORMAT PARQUET);
    """)

    print(f"Resultados guardados en: {output_file}")

def main():
    print("Iniciando procesamiento con DuckDB...")
    process_with_duckdb(INPUT_FILE, OUTPUT_FILE)
    print("Procesamiento completado.")

if __name__ == "__main__":
    main()
