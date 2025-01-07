import duckdb

# Configuración
INPUT_CSV = "./data/inputpoc1.csv"
OUTPUT_PARQUET = "./data/output_transformed.parquet"

def process_csv_to_parquet(input_csv, output_parquet):
    conn = duckdb.connect()
    
    # Leer datos CSV
    conn.execute(f"""
        CREATE TABLE input_data AS 
        SELECT * FROM read_csv_auto('{input_csv}')
    """)
    
    # Transformación: agregar columna calculada y filtrar datos
    conn.execute("""
        SELECT *,
               value * 2 AS double_value
        FROM input_data
        WHERE category IN ('A', 'B')
    """)
    
    # Guardar resultados en Parquet
    conn.execute(f"""
        COPY (
            SELECT * 
            FROM input_data
        )
        TO '{output_parquet}' (FORMAT PARQUET);
    """)

    print(f"Datos procesados y guardados en {output_parquet}")

process_csv_to_parquet(INPUT_CSV, OUTPUT_PARQUET)
