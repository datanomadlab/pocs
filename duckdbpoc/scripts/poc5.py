import duckdb

INPUT_FILE = "./data/inputpoc1.parquet"
OUTPUT_PARQUET = "./data/output_resultp5.parquet"
OUTPUT_ARROW = "./data/output_resultp5.arrow"
OUTPUT_CSV = "./data/output_resultp5.csv"

def save_to_multiple_formats(input_file, output_parquet, output_arrow, output_csv):
    conn = duckdb.connect()
    
    # Leer datos
    conn.execute(f"CREATE TABLE data AS SELECT * FROM read_parquet('{input_file}')")
    
    # Consulta base
    query = """
        SELECT category, SUM(value) AS total_value
        FROM data
        GROUP BY category
    """
    
    # Guardar en Parquet
    conn.execute(f"COPY ({query}) TO '{output_parquet}' (FORMAT PARQUET)")
    
    # Guardar en Arrow usando el método arrow()
    result = conn.execute(query).arrow()
    import pyarrow as pa
    with pa.OSFile(output_arrow, 'wb') as sink:
        with pa.RecordBatchFileWriter(sink, result.schema) as writer:
            writer.write_table(result)
    
    # Guardar en CSV
    conn.execute(f"COPY ({query}) TO '{output_csv}' (DELIMITER ',')")
    
    print(f"Datos guardados en: {output_parquet}, {output_arrow}, {output_csv}")

save_to_multiple_formats(INPUT_FILE, OUTPUT_PARQUET, OUTPUT_ARROW, OUTPUT_CSV)
