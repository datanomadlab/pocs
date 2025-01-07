import duckdb

INPUT_CSV = "./data/inputpoc1.csv"
INPUT_PARQUET = "./data/inputpoc1.parquet"
OUTPUT_PARQUET = "./data/output_joined.parquet"

def join_data_sources(input_csv, input_parquet, output_parquet):
    conn = duckdb.connect()
    
    # Leer y registrar tablas
    conn.execute(f"CREATE TABLE csv_data AS SELECT * FROM read_csv_auto('{input_csv}')")
    conn.execute(f"CREATE TABLE parquet_data AS SELECT * FROM read_parquet('{input_parquet}')")
    
    # Realizar join
    joined_data = conn.execute("""
        SELECT 
            c.timestamp,
            c.category,
            c.value as csv_value,
            p.value as parquet_value
        FROM csv_data c
        LEFT JOIN parquet_data p
        ON c.timestamp = p.timestamp
        AND c.category = p.category
    """).fetchdf()
    
    # Guardar en Parquet
    joined_data.to_parquet(output_parquet, index=False)
    print(f"Datos combinados guardados en {output_parquet}")

join_data_sources(INPUT_CSV, INPUT_PARQUET, OUTPUT_PARQUET)
